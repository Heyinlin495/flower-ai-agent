"""
花卉识别 AI Agent - 智能代理

基于 LangChain Agent 实现花卉识别和问答功能
"""

import asyncio
import json
import logging
import queue
from typing import List, Optional, Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI

from ..config import settings
from ..tools.flower_recognition import flower_recognition_tool
from ..tools.knowledge_search import knowledge_search_tool
from ..tools.oss_image_manager import oss_image_manager_tool
from ..rag.knowledge_base import knowledge_base
from .session_store import session_store

logger = logging.getLogger(__name__)


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

        # 工具列表
        self.tools = [
            flower_recognition_tool,
            knowledge_search_tool,
            oss_image_manager_tool,
        ]

        # 系统提示词（精简版，减少 LLM 处理时间）
        self.system_prompt = """你是花卉养护顾问 AI。用中文回答，简洁专业。适当用 emoji。"""

        # 创建 Agent（仅用于图片识别场景）
        self._create_agent()

        # 会话历史存储
        self._sessions: Dict[str, List] = {}

    def _create_agent(self):
        """创建 LangChain Agent（仅用于图片识别 + 多工具场景）"""
        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是花卉识别 AI。当用户上传图片时：
1. 用 flower_recognition 识别花卉
2. 用 knowledge_search 查询详细信息
3. 给出完整专业的回答。用中文。"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=agent_prompt,
        )

        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=settings.DEBUG,
            handle_parsing_errors=True,
            max_iterations=3,
            return_intermediate_steps=True,
        )

        logger.info("花卉Agent初始化完成")

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> dict:
        """
        与用户对话

        Args:
            message: 用户消息
            session_id: 会话ID
            image_url: 图片URL（如果有）

        Returns:
            dict: 包含回复消息和元数据的字典
        """
        try:
            # 获取或创建会话历史
            if session_id is None:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            chat_history = self._get_chat_history(session_id)

            # 构建输入
            input_message = message
            if image_url:
                input_message = f"{message}\n\n[图片URL: {image_url}]"

            # 执行 Agent
            result = self.agent_executor.invoke({
                "input": input_message,
                "chat_history": chat_history,
            })

            # 获取回复
            response = result.get("output", "")

            # 获取使用的工具信息
            tools_used = []
            for step in result.get("intermediate_steps", []):
                if len(step) >= 2:
                    tool_name = step[0].tool if hasattr(step[0], 'tool') else "unknown"
                    tools_used.append(tool_name)

            # 更新会话历史
            self._update_chat_history(
                session_id,
                HumanMessage(content=input_message),
                AIMessage(content=response)
            )

            # 构建响应
            return {
                "success": True,
                "message": response,
                "session_id": session_id,
                "image_url": image_url,
                "tools_used": tools_used,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Agent 处理异常: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

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

            chat_history = self._get_chat_history(session_id)

            # 构建输入
            input_message = message
            if image_url:
                input_message = f"{message}\n\n[图片URL: {image_url}]"

            # 执行 Agent
            result = await self.agent_executor.ainvoke({
                "input": input_message,
                "chat_history": chat_history,
            })

            # 获取回复
            response = result.get("output", "")

            # 获取使用的工具信息
            tools_used = []
            for step in result.get("intermediate_steps", []):
                if len(step) >= 2:
                    tool_name = step[0].tool if hasattr(step[0], 'tool') else "unknown"
                    tools_used.append(tool_name)

            # 更新会话历史
            self._update_chat_history(
                session_id,
                HumanMessage(content=input_message),
                AIMessage(content=response)
            )

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
        return self._sessions[session_id]

    def _update_chat_history(
        self,
        session_id: str,
        human_message: HumanMessage,
        ai_message: AIMessage
    ):
        """更新会话历史（内存 + SQLite 双写）"""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].extend([human_message, ai_message])

        # 限制历史长度，保留最近的20条消息
        if len(self._sessions[session_id]) > 20:
            self._sessions[session_id] = self._sessions[session_id][-20:]

        # 落盘持久化（消息内容为字符串时直接存储）
        try:
            session_store.add_message(
                session_id, "user", str(human_message.content)
            )
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
            return [
                {"role": m["role"], "content": m["content"]}
                for m in stored
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

        try:
            chat_history = self._get_chat_history(session_id)

            input_message = message
            if image_url:
                input_message = f"{message}\n\n[图片URL: {image_url}]"

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
        # 预加载知识库内容
        kb_context = ""
        try:
            results = knowledge_base.search(query=message, top_k=2)
            if results:
                kb_parts = []
                for r in results:
                    kb_parts.append(r["content"][:600])
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
            self._update_chat_history(
                session_id,
                HumanMessage(content=message),
                AIMessage(content=response_text),
            )

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
            "input": message,
            "chat_history": chat_history,
        }

        q = queue.Queue()
        callback = _StreamingCallback(q)

        def run_agent():
            try:
                list(self.agent_executor.stream(
                    inputs,
                    config={"callbacks": [callback]},
                ))
            except Exception as agent_err:
                q.put(("error", str(agent_err)))
            finally:
                q.put(None)

        task = asyncio.ensure_future(asyncio.to_thread(run_agent))

        response_parts = []
        while not task.done() or not q.empty():
            try:
                item = await asyncio.to_thread(q.get, block=True, timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            kind, payload = item
            if kind == "token":
                response_parts.append(payload)
                yield {"type": "token", "content": payload}
            elif kind == "tool":
                yield {"type": "status", "content": f"正在{payload}…"}
            elif kind == "error":
                yield {"type": "error", "content": payload}
                break

        await task

        response_text = "".join(response_parts)
        if response_text:
            self._update_chat_history(
                session_id,
                HumanMessage(content=message),
                AIMessage(content=response_text),
            )

        yield {
            "type": "done",
            "message": response_text,
            "session_id": session_id,
        }


class _StreamingCallback(BaseCallbackHandler):
    """
    流式回调处理器（仅用于 Agent 路径）。

    工具调用阶段的 token 丢弃，工具执行后才开始产出最终回复 token。
    """

    def __init__(self, q: queue.Queue):
        self._q = q
        self._tool_finished = False  # 是否至少完成过一次工具

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        if not token:
            return
        # 工具结束后的 token 才是最终回复 → 直接产出
        if self._tool_finished:
            self._q.put(("token", token))

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        tool_name = (
            serialized.get("name", "工具")
            if isinstance(serialized, dict)
            else "工具"
        )
        self._q.put(("tool", _tool_display_name(tool_name)))

    def on_tool_end(self, output, **kwargs) -> None:
        self._tool_finished = True

    def on_chain_end(self, outputs, **kwargs) -> None:
        pass  # sentinel 由 run_agent 负责


def _tool_display_name(tool_name: str) -> str:
    name_map = {
        "flower_recognition": "识别花卉图片",
        "knowledge_search": "搜索花卉知识库",
        "oss_image_manager": "处理图片",
    }
    return name_map.get(tool_name, f"调用 {tool_name}")


# 全局 Agent 实例
flower_agent = FlowerAgent()
