"""
花卉识别 AI Agent - 智能代理

基于 LangChain Agent 实现花卉识别和问答功能
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent
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

            # 执行 Agent（langgraph：传入 messages 状态字典）
            result = self.agent.invoke({
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
            "messages": [
                *chat_history,
                HumanMessage(content=message),
            ],
        }

        # langgraph 事件流：工具调用完成前丢弃 LLM token，
        # 工具执行完毕后的模型输出才是最终回复
        tool_finished = False
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
                elif kind == "on_tool_end":
                    tool_finished = True
                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    content = getattr(chunk, "content", "") if chunk else ""
                    if content and tool_finished:
                        response_parts.append(content)
                        yield {"type": "token", "content": content}
        except Exception as e:
            logger.error(f"Agent 流式异常: {e}")
            yield {"type": "error", "content": f"处理失败：{e}"}
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
        "oss_image_manager": "处理图片",
    }
    return name_map.get(tool_name, f"调用 {tool_name}")


# 全局 Agent 实例
flower_agent = FlowerAgent()
