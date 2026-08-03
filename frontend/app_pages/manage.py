"""
知识管理页面

添加和管理花卉知识库数据
"""

import json

import streamlit as st

from api import api_get, api_post, api_delete
from config import API_BASE_URL


# ─ 页面渲染 ────────────────────────────────────────────────────────────────

# 顶部标题
with st.container(horizontal_alignment="center"):
    st.title("📚 知识管理", text_alignment="center")
    st.caption("向花卉知识库添加新的花卉数据", text_alignment="center")

st.space("medium")

tab_add, tab_json = st.tabs([
    "添加花卉",
    "JSON 导入",
])

with tab_add:
    with st.form("add_flower_form"):
        # 基本信息卡片
        with st.container(border=True):
            st.markdown("**:material/flower: 基本信息**")

            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("花卉名称 *", placeholder="例如：玫瑰")
                family = st.text_input("科名", placeholder="例如：蔷薇科")
                genus = st.text_input("属名", placeholder="例如：蔷薇属")
                origin = st.text_input("原产地", placeholder="例如：中国")

            with col2:
                flowering_period = st.text_input("花期", placeholder="例如：5-11月")
                language = st.text_input("花语", placeholder="例如：爱情、美丽")
                habitat = st.text_input("生长环境", placeholder="例如：温暖湿润")

            characteristics = st.text_area(
                "形态特征",
                placeholder="描述花卉的外观特征…",
                height=90,
            )

        # 养护知识卡片
        with st.container(border=True):
            st.markdown("**:material/eco: 养护知识**")
            care_content = st.text_area(
                "养护方法",
                placeholder="浇水、施肥、光照、修剪等养护建议…",
                height=120,
            )

        with st.container(horizontal=True, horizontal_alignment="center"):
            submitted = st.form_submit_button(
                "添加到知识库",
                icon=":material/save:",
                type="primary",
            )

        if submitted:
            if not name:
                st.error("请填写花卉名称")
            else:
                flower_data = {
                    "name": name,
                    "family": family or "未知",
                    "genus": genus or "未知",
                    "origin": origin or "未知",
                    "flowering_period": flowering_period or "未知",
                    "language": language or "未知",
                    "habitat": habitat or "未知",
                    "characteristics": characteristics or "暂无",
                    "care_content": care_content or "暂无",
                }

                with st.spinner("正在添加…"):
                    result = api_post("/api/flower/knowledge/add", json=flower_data)

                if result.get("success"):
                    st.success(f"**{name}** 已成功添加到知识库！")
                else:
                    st.error(f"添加失败：{result.get('error', '未知错误')}")


with tab_json:
    with st.container(border=True):
        with st.expander("查看 JSON 格式说明", icon=":material/code:"):
            st.markdown(
                """
```json
{
    "name": "花卉名称",
    "family": "科名",
    "genus": "属名",
    "origin": "原产地",
    "flowering_period": "花期",
    "language": "花语",
    "habitat": "生长环境",
    "characteristics": "形态特征",
    "care_content": "养护方法"
}
```
                """
            )

        json_input = st.text_area(
            "粘贴 JSON 数据",
            placeholder='{\n    "name": "玫瑰",\n    "family": "蔷薇科",\n    ...\n}',
            height=220,
            label_visibility="collapsed",
        )

        with st.container(horizontal=True, horizontal_alignment="center", gap="small"):
            if st.button("验证 JSON", icon=":material/check_circle:"):
                if not json_input:
                    st.warning("请输入 JSON 数据")
                else:
                    try:
                        data = json.loads(json_input)
                        if "name" not in data:
                            st.error("JSON 缺少必需字段：name")
                        else:
                            st.success(f"JSON 格式正确，花卉名称：{data['name']}")
                    except json.JSONDecodeError as e:
                        st.error(f"JSON 格式错误：{e}")

            if st.button(
                "导入",
                icon=":material/upload:",
                type="primary",
            ):
                if not json_input:
                    st.warning("请输入 JSON 数据")
                else:
                    try:
                        data = json.loads(json_input)
                        if "name" not in data:
                            st.error("JSON 缺少必需字段：name")
                        else:
                            with st.spinner("正在导入…"):
                                result = api_post("/api/flower/knowledge/add", json=data)
                            if result.get("success"):
                                st.success(f"**{data['name']}** 导入成功！")
                            else:
                                st.error(f"导入失败：{result.get('error', '未知错误')}")
                    except json.JSONDecodeError as e:
                        st.error(f"JSON 格式错误：{e}")

# ── 知识库概览 ─────────────────────────────────────────────────────────────

st.space("medium")

with st.container(border=True):
    st.markdown("**:material/library_books: 知识库概览**")
    st.caption("当前知识库中已有的花卉（点击 ✕ 删除）")

    with st.spinner("正在读取知识库…"):
        list_result = api_get("/api/flower/knowledge/list")

    if list_result.get("success"):
        flowers = list_result.get("flowers", [])
        if not flowers:
            st.info("知识库还是空的，添加第一朵花吧！")
        else:
            st.caption(f"共 {list_result.get('total', len(flowers))} 种花卉")
            for fname in flowers:
                with st.container(horizontal=True, gap="small"):
                    st.markdown(f":material/local_florist: **{fname}**")
                    if st.button(
                        ":material/delete:",
                        key=f"del_flower_{fname}",
                        help=f"删除「{fname}」",
                    ):
                        with st.spinner(f"正在删除「{fname}」…"):
                            del_result = api_delete(f"/api/flower/knowledge/delete/{fname}")
                        if del_result.get("success"):
                            st.success(del_result.get("message", "删除成功"))
                            st.rerun()
                        else:
                            st.error(f"删除失败：{del_result.get('error', '未知错误')}")
    else:
        st.error(f"读取知识库失败：{list_result.get('error', '未知错误')}")
