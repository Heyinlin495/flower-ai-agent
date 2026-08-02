"""
知识搜索页面

直接搜索花卉知识库，快速查找花卉信息
"""

import streamlit as st
import requests

from config import API_BASE_URL


def search_knowledge(query: str, flower_name: str = "", top_k: int = 3) -> dict:
    """搜索知识库"""
    try:
        params = {"query": query, "top_k": top_k}
        if flower_name:
            params["flower_name"] = flower_name
        resp = requests.get(f"{API_BASE_URL}/api/flower/knowledge/search", params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        return {"success": False, "error": f"API 错误: {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "无法连接到后端服务"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─ 页面渲染 ─────────────────────────────────────────────────────────────────

# 顶部标题
with st.container(horizontal_alignment="center"):
    st.title("🔍 知识搜索", text_alignment="center")
    st.caption("从花卉知识库中检索养护、花语、特征等信息", text_alignment="center")

st.space("medium")

# 搜索表单
with st.form("knowledge_search_form"):
    query = st.text_input(
        "搜索内容",
        placeholder="例如：玫瑰怎么养护？向日葵的花语？",
        label_visibility="collapsed",
    )

    col1, col2, col3 = st.columns([2, 1, 1], vertical_alignment="bottom")
    with col1:
        flower_name = st.text_input(
            "指定花卉（可选）",
            placeholder="如：玫瑰",
            label_visibility="collapsed",
        )
    with col2:
        top_k = st.selectbox(
            "返回条数",
            options=[3, 5, 10],
            index=0,
            label_visibility="collapsed",
            key="search_top_k",
        )
    with col3:
        submitted = st.form_submit_button(
            "搜索",
            icon=":material/search:",
            type="primary",
            width="stretch",
        )

# 热门搜索（点击即搜）
if not query and not submitted and "_knowledge_query" not in st.session_state:
    st.space("medium")
    hot_queries = [
        "🌹 玫瑰的养护方法",
        "🌺 百合的花语",
        "🪴 多肉植物怎么浇水",
        "🌸 兰花需要什么样的光照",
        "🌼 菊花的品种有哪些",
    ]
    picked = st.pills(
        "热门搜索",
        hot_queries,
        label_visibility="collapsed",
        key="hot_pills",
    )
    if picked:
        st.session_state._knowledge_query = picked
        st.rerun()

# 执行搜索
if submitted and query:
    st.session_state._knowledge_query = query

if "_knowledge_query" in st.session_state and st.session_state._knowledge_query:
    search_q = st.session_state._knowledge_query
    with st.spinner("正在搜索知识库…"):
        result = search_knowledge(search_q, flower_name, top_k)

    if result.get("success"):
        results = result.get("results", [])
        with st.container(horizontal=True, horizontal_alignment="right", gap="small"):
            st.caption(f"找到 {len(results)} 条相关结果 · 「{search_q}」")
            if st.button(
                "清除结果",
                icon=":material/close:",
                help="回到热门搜索",
            ):
                del st.session_state["_knowledge_query"]
                st.rerun()

        if not results:
            st.info("未找到相关内容，试试换个关键词吧")
        else:
            # 按花卉名折叠去重（同名多 chunk 只显示最相关的一条）
            seen_flowers = set()
            shown = 0
            for i, r in enumerate(results, 1):
                metadata = r.get("metadata", {})
                flower = metadata.get("flower_name") or "未知花卉"
                if flower in seen_flowers:
                    continue
                seen_flowers.add(flower)

                source = metadata.get("source", "")
                source_name = source.replace("\\", "/").split("/")[-1] if source else ""
                score = r.get("score", 0)
                content = r.get("content", "")
                shown += 1

                with st.container(border=True):
                    with st.container(horizontal=True, gap="small"):
                        st.markdown(f"**{flower}**")
                        if score >= 0.7:
                            st.badge(f"相关度 {score:.0%}", color="green")
                        elif score >= 0.4:
                            st.badge(f"相关度 {score:.0%}", color="orange")
                        else:
                            st.badge(f"相关度 {score:.0%} · 较低", color="red")
                        st.caption(f"第 {shown} 条 · {source_name}")
                    st.markdown(content)

                    if st.button(
                        "继续提问",
                        key=f"ask_{i}",
                        icon=":material/chat:",
                    ):
                        st.session_state.messages = st.session_state.get("messages", [])
                        st.session_state.messages.append({
                            "role": "user",
                            "content": f"关于{flower}，{search_q}",
                        })
                        st.switch_page("app_pages/chat.py")

            if shown < len(results):
                st.caption(f"已合并 {len(results) - shown} 条同名重复结果")
    else:
        st.error(f"搜索失败：{result.get('error', '未知错误')}")
