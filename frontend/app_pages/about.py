"""
关于页面

项目介绍和使用帮助
"""

import streamlit as st

from config import APP_VERSION


# 顶部标题
with st.container(horizontal_alignment="center"):
    st.title("🌐 关于本项目", text_alignment="center")
    st.caption(f"花卉识别 AI Agent {APP_VERSION} · 作者 何胤霖", text_alignment="center")

st.space("medium")

# 能力概览（三张统计卡）
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("图片识别", "通义千问 VL", help="上传花卉图片，AI 自动识别花名、科属、特征、花语")
with m2:
    st.metric("智能问答", "RAG + Agent", help="结合知识库向量检索，回答养护、种植、病虫害问题")
with m3:
    st.metric("知识库", "ChromaDB", help="向量化存储花卉知识，支持相似度检索与持续扩展")

st.space("medium")

# 功能矩阵 + 技术栈
col_left, col_right = st.columns(2)

with col_left:
    with st.container(border=True):
        st.markdown("**:material/grid_view: 功能介绍**")

        features = [
            (":material/image_search:", "智能聊天", "图片识别 · 文字问答 · 多轮对话"),
            (":material/search:", "知识搜索", "知识库检索 · 花卉名过滤 · 相关度评分"),
            (":material/library_books:", "知识管理", "手动添加 · JSON 批量导入"),
            (":material/auto_awesome:", "AI 能力", "通义千问视觉模型 · RAG 向量检索 · LangChain Agent"),
        ]
        for icon, title, desc in features:
            with st.container(horizontal=True, gap="small"):
                st.markdown(icon)
                st.markdown(f"**{title}**")
            st.caption(desc)

    with st.container(border=True):
        st.markdown("**:material/lightbulb: 使用提示**")
        st.markdown(
            """
1. **识别花卉** — 在"智能聊天"页面上传图片，返回花名、科属、花期等信息
2. **养护咨询** — 直接提问，如"玫瑰怎么养护？"，AI 结合知识库回答
3. **知识搜索** — 检索知识库，结果附带相关度评分，可一键转到聊天
4. **扩展知识** — 在"知识管理"页面添加花卉数据，丰富知识库
            """
        )

with col_right:
    with st.container(border=True):
        st.markdown("**:material/dashboard: 技术栈**")

        tech_data = {
            "组件": ["后端框架", "AI Agent", "大语言模型", "视觉模型", "向量数据库", "前端", "知识库"],
            "技术": ["FastAPI", "LangChain", "通义千问 (qwen-plus)", "通义千问 VL (qwen-vl-max)", "ChromaDB", "Streamlit", "RAG + JSON"],
        }
        st.dataframe(tech_data, hide_index=True, width="stretch")

    with st.container(border=True):
        st.markdown("**:material/person: 作者**")
        st.markdown("**何胤霖 (Yinlin He)**")
        st.caption(
            "本项目为个人独立开发项目\n"
            "从需求分析、后端架构（FastAPI + LangChain + RAG + Agent）\n"
            "到前端 UI（Streamlit）全栈实现"
        )

    with st.container(border=True):
        st.markdown("**:material/info: 项目简介**")
        st.markdown(
            "基于 **FastAPI + LangChain + RAG** 的智能花卉识别和养护咨询系统。\n\n"
            "支持图片识别、文字问答、知识库搜索等功能。"
        )

# 底部
st.space("medium")
with st.container(horizontal_alignment="center"):
    st.caption(f"花卉识别 AI Agent {APP_VERSION} · 2026 · 作者 何胤霖")
