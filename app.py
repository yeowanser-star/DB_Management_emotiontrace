import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
from ai_agent import agent
from bilibili_spider import fetch_bilibili_comments, fetch_video_detail
from db_handler import db_handler
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from bilibili_spider import validate_bvid

# ==========================================
# 1. 基础配置
# ==========================================
st.set_page_config(page_title="B站评论 AI 智能分析", layout="wide", initial_sidebar_state="expanded")
st.markdown('<meta name="referrer" content="no-referrer">', unsafe_allow_html=True)

# ==========================================
# 2. 侧边栏：控制面板
# ==========================================
with st.sidebar:
    st.header("📊 控制")
    target_aid_input = st.text_input("B站视频 BV号", placeholder="例如: BV1yK2QBAEHv")
    user_cookie = st.text_area("B站 Cookie", height=80, help="F12了解你的Cookie")
    crawl_pages = st.slider("爬取深度 (页数)", min_value=1, max_value=20, value=3)

    st.divider()
    st.subheader("📈 库内数据统计")
    stats_sql = """
        SELECT 
            (SELECT COUNT(*) FROM videos) as v_count,
            (SELECT COUNT(*) FROM comments) as c_count,
            (SELECT COUNT(*) FROM tags_dict) as t_count
    """
    overall_stats = db_handler.execute_query(stats_sql)
    if overall_stats:
        s = overall_stats[0]
        c1, c2 = st.columns(2)
        c1.metric("视频数", s['v_count'])
        c2.metric("评论总数", s['c_count'])
        st.metric("挖掘特征标签", s['t_count'])

    # --- 数据库管理 ---
    with st.expander("🛠️ 高级管理"):
        if st.button("🔥 清空数据库"):
            try:
                conn, cursor = db_handler._get_conn_and_cursor()

                sql_commands = [
                    "SET FOREIGN_KEY_CHECKS = 0;",
                    "TRUNCATE TABLE comment_tag_map;",
                    "TRUNCATE TABLE comments;",
                    "TRUNCATE TABLE tags_dict;",
                    "TRUNCATE TABLE videos;",
                    "SET FOREIGN_KEY_CHECKS = 1;"
                ]

                for cmd in sql_commands:
                    cursor.execute(cmd)

                conn.commit()
                cursor.close()
                conn.close()

                st.cache_data.clear()
                st.cache_resource.clear()

                keys_to_clear = ['last_viewed_aid', 'batch_data']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]

                st.success("✅ 物理删除成功，页面即将重置...")

                import time

                time.sleep(0.5)
                st.rerun()

            except Exception as e:
                st.error(f"❌ 强制清空失败: {e}")

    if st.button("🚀 开始", use_container_width=True):
        current_time = time.time()
        last_run = st.session_state.get('last_run_time', 0)

        if current_time - last_run < 10:
            st.warning(f"⏳ 系统繁忙！请在 {int(10 - (current_time - last_run))} 秒后再次尝试，防止过载分析。")

        elif not target_aid_input or not validate_bvid(target_aid_input):
            st.error("🚫 非法的BV号格式！请输入以BV开头的12位字符。")

        elif not user_cookie or len(user_cookie) < 50:  # 简单校验Cookie长度，防止误传
            st.error("⚠️ B站 Cookie 格式不正确或为空，请重新获取。")

        else:
            st.session_state['last_run_time'] = current_time

            with st.status("🚀...", expanded=True) as status:
                video_ctx = fetch_video_detail(target_aid_input, user_cookie)
                if video_ctx:
                    st.session_state['last_viewed_aid'] = video_ctx['aid']
                    st.session_state['current_video_data'] = {
                        "title": video_ctx['title'],
                        "desc": video_ctx['desc'],
                        "pic": video_ctx['pic'],
                        "owner": video_ctx['owner_name'],
                        "view": video_ctx['view'],
                        "like": video_ctx['like']
                    }

                    db_handler.save_video_context(video_ctx['aid'], video_ctx['title'], video_ctx['desc'])

                    replies, _ = fetch_bilibili_comments(target_aid_input, user_cookie, pages=crawl_pages)

                    if replies:
                        bar = st.progress(0)
                        status_text = st.empty()
                        batch_data = []

                        with ThreadPoolExecutor(max_workers=15) as executor:
                            future_to_comment = {
                                executor.submit(
                                    agent.analyze_sentiment_and_tags,
                                    r['content'],
                                    v_title=video_ctx['title'],
                                    v_desc=video_ctx['desc'],
                                    is_sub_comment=(r.get('parent_id') is not None)
                                ): r for r in replies
                            }

                            for i, future in enumerate(as_completed(future_to_comment)):
                                r = future_to_comment[future]
                                try:
                                    analysis = future.result()
                                    batch_data.append({
                                        'rpid': r['rpid'],
                                        'uname': r['uname'],
                                        'content': r['content'],
                                        'parent_id': r.get('parent_id'),
                                        'analysis': analysis
                                    })
                                except Exception as e:
                                    print(f"AI分析失败: {e}")

                                bar.progress((i + 1) / len(replies))
                                status_text.text(f"🧠 分析中: {i + 1}/{len(replies)}")

                        status_text.text("💾 正在按层级同步至数据库连接池...")
                        db_handler.save_comments_batch(video_ctx['aid'], batch_data)

                        st.session_state['last_viewed_aid'] = video_ctx['aid']
                        st.success("✅ 同步完成！已应用相关性加权算法。")
                        st.rerun()

# ==========================================
# 3. 主界面可视化布局
# ==========================================
st.title("🎬 bilibili视频情感分析")
display_aid = st.session_state.get('last_viewed_aid')

if display_aid:
    v_data = st.session_state.get('current_video_data')

    if v_data:
        with st.container(border=True):
            v_col1, v_col2 = st.columns([1, 2.5])
            with v_col1:
                    # 封面展示
                st.image(v_data['pic'], use_container_width=True)
            with v_col2:
                    # 标题
                st.subheader(f"{v_data['title']}")
                    # 统计数据条
                st.markdown(f"""
                **UP主**: `{v_data['owner']}` | 
                **播放量**: `{v_data['view']:,}` | 
                **点赞**: `{v_data['like']:,}`
                """)
                # 简介摘要
                with st.expander("查看视频简介"):
                    st.write(v_data['desc'])
        st.divider()


    raw_data = db_handler.get_analysis_report(display_aid)
    data_all = pd.DataFrame(raw_data)

    raw_data = db_handler.get_analysis_report(display_aid)
    data_all = pd.DataFrame(raw_data)

    if not data_all.empty:
        video_stats = db_handler.get_video_stats(display_aid)
        db_score = video_stats['avg_sentiment']

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("样本量", len(data_all))
        m2.metric("情感均值", f"{data_all['sentiment_score'].mean():.2f}")
        m3.metric("平均相关度", f"{data_all['relevance_score'].mean():.2f}")
        m4.metric("库级评定分", f"{db_score:.2f}", help="MySQL触发器基于相关性加权+Sigmoid拉伸计算")


        # 情绪分类
        def get_label(s):
            if s >= 0.75: return '积极'
            if s <= 0.25: return '消极'
            return '中性'


        data_all['label'] = data_all['sentiment_score'].apply(get_label)

        # 布局展示
        c1, c2 = st.columns(2)
        with c1:
            fig_pie = px.pie(data_all, names='label', hole=0.4, title="情感倾向比例",
                             color='label',
                             color_discrete_map={'积极': '#26a69a', '中性': '#ffa726', '消极': '#ef5350'})
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            fig_bar = px.histogram(data_all, x="label", color="type", barmode="group", title="主/子评论情绪对比")
            st.plotly_chart(fig_bar, use_container_width=True)

        # 标签云
        st.subheader("🏷️ AI 提取特征标签")
        all_tags = []
        for t in data_all['tags_display'].dropna():
            if t: all_tags.extend(t.split(','))

        if all_tags:
            tag_counts = Counter(all_tags).most_common(20)
            tag_df = pd.DataFrame(tag_counts, columns=['特征', '频次'])
            fig_tag = px.bar(tag_df, x='频次', y='特征', orientation='h', color='频次', color_continuous_scale='GnBu')
            st.plotly_chart(fig_tag, use_container_width=True)

        # 明细
        st.subheader("💬 评论明细")
        data_all['display_content'] = data_all.apply(
            lambda r: f"└─ {r['content']}" if r['type'] == '回复' else r['content'], axis=1)
        st.dataframe(
            data_all[['display_content', 'sentiment_score', 'relevance_score', 'tags_display']],
            column_config={
                "display_content": st.column_config.TextColumn("内容", width="large"),
                "sentiment_score": st.column_config.ProgressColumn("评分", min_value=0, max_value=1),
                "relevance_score": st.column_config.ProgressColumn("相关性", min_value=0, max_value=1),
            },
            hide_index=True, use_container_width=True
        )
else:
    st.info("👋 欢迎！请输入左侧BV号并点击开始分析。")