"""
花卉识别 AI Agent - 智能代理

基于 LangChain Agent 实现花卉识别和问答功能
"""

import asyncio
import logging
from collections import OrderedDict
from typing import List, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from ..config import settings
from ..tools.flower_recognition import flower_recognition_tool
from ..tools.knowledge_search import knowledge_search_tool
from ..rag.knowledge_base import knowledge_base
from .session_store import session_store

logger = logging.getLogger(__name__)

# 内存中最多保留的会话数（LRU 淘汰，超限的会话从内存移除，SQLite 仍可恢复）
MAX_SESSIONS_IN_MEMORY = 100
# 直连 LLM 路径的知识库检索结果缓存上限（热点问题不重复调 embedding）
KB_SEARCH_CACHE_MAX = 50


class FlowerAgent:
    """
    花卉识别智能代理

    功能：
    - 接收用户消息和图片
    - 自动选择合适的工具处理请求
    - 整合多个工具的结果生成回答
    - 维护对话历史
    """

    def __init__(self):
        """初始化花卉Agent"""
        # 初始化 LLM - 使用 OpenAI 兼容接口
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            streaming=True
        )

        # 工具列表（oss_image_manager 已移除：前端识别走 /api/flower/recognize，
        # LLM 不会主动保存图片，保留只会诱导模型向 Agent 上下文塞 base64 大字符串）
        self.tools = [
            flower_recognition_tool,
            knowledge_search_tool,
        ]

        # 系统提示词（精简版，减少 LLM 处理时间）
        self.system_prompt = """你是花卉养护顾问 AI。用中文回答，简洁专业。适当用 emoji。"""

        # 创建 Agent（仅用于图片识别场景）
        self._create_agent()

        # 会话历史存储（OrderedDict 做 LRU，超过上限自动淘汰最久未访问的会话）
        self._sessions: "OrderedDict[str, List]" = OrderedDict()
        # 每会话一个 asyncio.Lock：同会话并发请求串行化，防止历史双写串台
        self._session_locks: dict = {}
        # 知识库检索结果 LRU 缓存（直连 LLM 路径用，避免热点问题反复调 embedding）
        self._kb_search_cache: "OrderedDict[str, list]" = OrderedDict()

    def _create_agent(self):
        """创建 LangChain Agent（仅用于图片识别 + 多工具场景）"""
        system_prompt = (
            "你是花卉识别 AI。当用户上传图片时：\n"
            "1. 用 flower_recognition 识别花卉\n"
            "2. 用 knowledge_search 查询详细信息\n"
            "3. 给出完整专业的回答。用中文。"
        )

        # langchain 1.x：create_agent 基于 langgraph，
        # 输入为消息列表，输出为 {"messages": [...]} 状态字典
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
            debug=settings.DEBUG,
        )

        logger.info("花卉Agent初始化完成")

    async def achat(
        self,
        message: str,
        session_id: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> dict:
        """
        异步对话

        Args:
            message: 用户消息
            session_id: 会话ID
            image_url: 图片URL

        Returns:
            dict: 响应字典
        """
        try:
            # 获取或创建会话历史
            if session_id is None:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 同会话并发请求串行化（防历史双写串台）
            async with self._get_session_lock(session_id):
                chat_history = self._get_chat_history(session_id)

                # 构建输入
                input_message = message
                if image_url:
                    input_message = f"{message}\n\n[图片URL: {image_url}]"

                # 执行 Agent（langgraph：传入 messages 状态字典）
                result = await self.agent.ainvoke({
                    "messages": [
                        *chat_history,
                        HumanMessage(content=input_message),
                    ],
                })

                # 获取回复（最后一条消息为最终回答）
                messages = result.get("messages", [])
                response = messages[-1].content if messages else ""

                # 获取使用的工具信息（从消息的 tool_calls 提取）
                tools_used = _extract_tools_used(messages)

                # 更新会话历史（用户消息先记录，AI 回复后记录）
                self._record_user_message(session_id, input_message)
                self._update_chat_history(session_id, AIMessage(content=response))

                return {
                    "success": True,
                    "message": response,
                    "session_id": session_id,
                    "image_url": image_url,
                    "tools_used": tools_used,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            error_msg = f"Agent 异步处理异常: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

    def _trim_sessions(self):
        """LRU 淘汰：内存会话超过上限时移除最久未访问的"""
        while len(self._sessions) > MAX_SESSIONS_IN_MEMORY:
            oldest_sid, _ = next(iter(self._sessions.items()))
            del self._sessions[oldest_sid]

    def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        """获取会话级锁（惰性创建；超限时清理不属于内存会话的旧锁）"""
        lock = self._session_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._session_locks[session_id] = lock
            # 锁表膨胀时清掉已不在内存会话集合里的锁（防 session_id 注入式增长）
            if len(self._session_locks) > MAX_SESSIONS_IN_MEMORY * 2:
                for sid in [s for s in self._session_locks if s not in self._sessions]:
                    self._session_locks.pop(sid, None)
        return lock

    def _get_chat_history(self, session_id: str) -> List:
        """获取会话历史（内存缓存优先，SQLite 落盘兜底恢复）"""
        if session_id not in self._sessions:
            # 后端重启后从 SQLite 恢复
            stored = session_store.get_messages(session_id)
            restored = []
            for m in stored:
                if m["role"] == "user":
                    restored.append(HumanMessage(content=m["content"]))
                elif m["role"] == "assistant":
                    restored.append(AIMessage(content=m["content"]))
            # 保留最近 20 条
            self._sessions[session_id] = restored[-20:]
        # LRU：标记为最近访问
        self._sessions.move_to_end(session_id)
        self._trim_sessions()
        return self._sessions[session_id]

    def _record_user_message(self, session_id: str, message: str):
        """记录用户消息（内存 + SQLite），AI 回复失败时也不丢失"""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        human = HumanMessage(content=message)
        self._sessions[session_id].append(human)

        # 限制历史长度，保留最近的20条消息
        if len(self._sessions[session_id]) > 20:
            self._sessions[session_id] = self._sessions[session_id][-20:]

        # LRU：标记为最近访问
        self._sessions.move_to_end(session_id)
        self._trim_sessions()

        # 落盘持久化
        try:
            session_store.add_message(session_id, "user", message)
        except Exception as e:
            logger.warning(f"会话落盘失败: {e}")

    def _update_chat_history(self, session_id: str, ai_message: AIMessage):
        """记录 AI 回复（内存 + SQLite 双写），限制最近 20 条"""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append(ai_message)

        # 限制历史长度，保留最近的20条消息
        if len(self._sessions[session_id]) > 20:
            self._sessions[session_id] = self._sessions[session_id][-20:]

        # LRU：标记为最近访问
        self._sessions.move_to_end(session_id)
        self._trim_sessions()

        # 落盘持久化（消息内容为字符串时直接存储）
        try:
            session_store.add_message(
                session_id, "assistant", str(ai_message.content)
            )
        except Exception as e:
            logger.warning(f"会话落盘失败: {e}")

    def clear_session(self, session_id: str) -> bool:
        """
        清除会话历史（内存 + SQLite 双删）

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功
        """
        existed = session_id in self._sessions
        self._sessions.pop(session_id, None)
        try:
            deleted = session_store.delete_session(session_id)
        except Exception as e:
            logger.warning(f"会话删除失败: {e}")
            deleted = False
        return existed or deleted

    def get_session_history(self, session_id: str) -> List[dict]:
        """
        获取会话历史（格式化，优先读 SQLite 持久化数据）

        Args:
            session_id: 会话ID

        Returns:
            List[dict]: 格式化的历史消息列表
        """
        try:
            stored = session_store.get_messages(session_id)
        except Exception as e:
            logger.warning(f"读取会话历史失败: {e}")
            stored = []

        if stored:
            # 只回最近 50 条（长会话避免全量拉取）；image_url 一并返回，
            # 前端恢复历史时图片消息才能正常展示
            return [
                {"role": m["role"], "content": m["content"], "image_url": m.get("image_url")}
                for m in stored[-50:]
            ]

        # 落盘无数据时回退内存
        history = self._get_chat_history(session_id)
        formatted = []
        for msg in history:
            if isinstance(msg, HumanMessage):
                formatted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted.append({"role": "assistant", "content": msg.content})
        return formatted

    def list_sessions(self) -> List[dict]:
        """
        列出所有会话（含标题、消息数、更新时间）

        Returns:
            List[dict]: 会话列表
        """
        try:
            return session_store.list_sessions()
        except Exception as e:
            logger.warning(f"列出会话失败: {e}")
            return []

    async def stream_chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        image_url: Optional[str] = None,
    ):
        """
        流式对话。纯文字走快速 LLM 直连路径，有图片才走 Agent。

        Yields:
            {"type": "token",  "content": "..."}
            {"type": "status", "content": "..."}
            {"type": "done",   "message": "..."}
            {"type": "error",  "content": "..."}
        """
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 同会话并发请求串行化（流式期间也持锁，历史不串写；
        # 前端已用 submit_mode="stop" 限制单条，这里兜底双端并发）
        lock = self._get_session_lock(session_id)
        await lock.acquire()
        try:
            chat_history = self._get_chat_history(session_id)

            input_message = message
            if image_url:
                input_message = f"{message}\n\n[图片URL: {image_url}]"

            # 先记录用户消息（即使 AI 回复失败/断流，历史也不丢）
            self._record_user_message(session_id, input_message)

            # ── 快速路径：纯文字 → 直接 LLM（跳过 Agent 循环） ──────────────
            if not image_url:
                async for item in self._stream_direct_llm(
                    message=input_message,
                    session_id=session_id,
                    chat_history=chat_history,
                ):
                    yield item
                return

            # ── Agent 路径：有图片 → 完整 Agent（识别 + 搜索 + 回复） ──────
            async for item in self._stream_agent(
                message=input_message,
                session_id=session_id,
                chat_history=chat_history,
            ):
                yield item

        except Exception as e:
            logger.error(f"流式异常: {e}")
            yield {"type": "error", "content": f"处理失败：{e}"}
        finally:
            lock.release()

    async def _stream_direct_llm(
        self,
        message: str,
        session_id: str,
        chat_history: List,
    ):
        """
        直连 LLM，预加载知识库上下文。

        跳过 Agent 循环，节省一次 LLM 调用（~1-2 秒）。
        先快速搜索知识库，把相关内容注入 prompt。
        """
        # 预加载知识库内容（同步 embedding 调用放到线程池，避免阻塞 event loop）
        # 热点问题走 LRU 缓存，不重复调 embedding（省时省钱）
        kb_context = ""
        try:
            cached = self._kb_search_cache.get(message)
            if cached is not None:
                self._kb_search_cache.move_to_end(message)
                results = cached
            else:
                results = await asyncio.to_thread(knowledge_base.search, message, 2)
                if results:
                    self._kb_search_cache[message] = results
                    self._kb_search_cache.move_to_end(message)
                    while len(self._kb_search_cache) > KB_SEARCH_CACHE_MAX:
                        self._kb_search_cache.popitem(last=False)
            if results:
                kb_parts = [r["content"][:600] for r in results]
                kb_context = "\n\n".join(kb_parts)
        except Exception:
            pass  # 知识库不可用时不影响对话

        # 构建 prompt
        if kb_context:
            system_msg = SystemMessage(
                content=(
                    "你是花卉养护顾问 AI。用中文回答，简洁专业。适当用 emoji。\n\n"
                    f"## 知识库参考\n{kb_context}\n\n"
                    "优先使用知识库信息回答，知识库没有的可以凭自身知识补充。"
                )
            )
        else:
            system_msg = SystemMessage(
                content="你是花卉养护顾问 AI。用中文回答，简洁专业。适当用 emoji。"
            )

        messages = [system_msg, *chat_history, HumanMessage(content=message)]

        # 直接流式调用 LLM
        response_parts = []
        try:
            async for chunk in self.llm.astream(messages):
                content = chunk.content
                if content:
                    response_parts.append(content)
                    yield {"type": "token", "content": content}
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            yield {"type": "error", "content": f"LLM 调用失败：{e}"}
            return

        response_text = "".join(response_parts)
        if response_text:
            self._update_chat_history(session_id, AIMessage(content=response_text))

        yield {
            "type": "done",
            "message": response_text,
            "session_id": session_id,
        }

    async def _stream_agent(
        self,
        message: str,
        session_id: str,
        chat_history: List,
    ):
        """Agent 路径：有图片时用 Agent 协调多个工具。"""
        inputs = {
            "messages": [
                *chat_history,
                HumanMessage(content=message),
            ],
        }

        # langgraph 事件流：模型节点输出带 tool_calls 的是"中间决策"（要丢弃），
        # 无 tool_calls 的输出才是最终回复。
        # 先缓冲节点内的 token，节点结束（on_chat_model_end）时无 tool_calls 才流出 ——
        # 这样既正确丢弃中间轮的"我将使用工具…"措辞，也不误伤多轮工具循环。
        pending_tokens: List[str] = []
        response_parts = []
        try:
            async for event in self.agent.astream_events(
                inputs,
                version="v2",
                # 替代旧 AgentExecutor 的 max_iterations=3（每个迭代约 4-5 个节点）
                config={"recursion_limit": 20},
            ):
                kind = event["event"]
                if kind == "on_tool_start":
                    tool_name = event.get("name", "工具")
                    yield {
                        "type": "status",
                        "content": f"正在{_tool_display_name(tool_name)}…",
                    }
                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    content = getattr(chunk, "content", "") if chunk else ""
                    if content:
                        pending_tokens.append(content)
                elif kind == "on_chat_model_end":
                    output = event["data"].get("output")
                    has_tool_calls = bool(getattr(output, "tool_calls", None))
                    if has_tool_calls:
                        pending_tokens.clear()  # 中间决策节点：丢弃缓冲
                        continue
                    # 最终回复节点：缓冲全部流出
                    for t in pending_tokens:
                        response_parts.append(t)
                        yield {"type": "token", "content": t}
                    pending_tokens.clear()
        except Exception as e:
            logger.error(f"Agent 流式异常: {e}")
            yield {"type": "error", "content": f"处理失败：{e}"}
            return

        response_text = "".join(response_parts)
        if response_text:
            self._update_chat_history(session_id, AIMessage(content=response_text))

        yield {
            "type": "done",
            "message": response_text,
            "session_id": session_id,
        }


def _extract_tools_used(messages: List) -> List[str]:
    """从 langgraph 输出消息中提取实际调用的工具名（去重保序）"""
    tools_used = []
    for m in messages:
        for tc in getattr(m, "tool_calls", []) or []:
            name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
            if name not in tools_used:
                tools_used.append(name)
    return tools_used


def _tool_display_name(tool_name: str) -> str:
    name_map = {
        "flower_recognition": "识别花卉图片",
        "knowledge_search": "搜索花卉知识库",
    }
    return name_map.get(tool_name, f"调用 {tool_name}")


# 全局 Agent 实例
flower_agent = FlowerAgent()
