"""Streamlit app with LLM integration and scheduling

Enhanced dashboard with real-time report generation and task scheduling.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from src.config import config
from src.analysis.scoring import MultiFactorScorer
from src.data.pipeline import DataPipeline
from src.llm.report_generator import ReportGenerator
from src.llm.llm_client import LLMClient
from src.scheduler.task_scheduler import TaskScheduler
from src.logger import get_logger

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="A-Share 量化分析系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "scheduler" not in st.session_state:
    st.session_state.scheduler = TaskScheduler()

if "report_generator" not in st.session_state:
    st.session_state.report_generator = ReportGenerator()

if "llm_client" not in st.session_state:
    st.session_state.llm_client = LLMClient()

if "last_scores" not in st.session_state:
    st.session_state.last_scores = []

# Custom CSS
st.markdown(
    """
    <style>
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; }
    .score-high { color: #00dd00; font-weight: bold; }
    .score-medium { color: #ff9800; font-weight: bold; }
    .score-low { color: #ff0000; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)


def main():
    """Main app"""
    st.title("🎯 A-Share 量化分析系统 - 完整版")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ 控制面板")

        # Tab selection
        tab = st.radio(
            "选择功能",
            ["📊 仪表板", "📝 报告生成", "⏰ 任务调度", "🔧 系统设置"],
        )

        st.markdown("---")

        # Common parameters
        st.subheader("评分参数")
        top_k = st.slider(
            "显示前N只股票", min_value=10, max_value=100, value=50, step=10
        )
        min_score = st.slider(
            "最低评分阈值", min_value=0.0, max_value=100.0, value=50.0, step=5.0
        )

        st.markdown("---")

        # Environment info
        st.subheader("环境信息")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("运行环境", config.ENV.upper())
        with col2:
            st.metric("调试模式", "✓" if config.DEBUG else "✗")

        # LLM Status
        st.subheader("LLM 状态")
        if st.button("🔍 检查连接"):
            if st.session_state.llm_client.health_check():
                st.success("✓ LLM 服务正常")
            else:
                st.error("✗ LLM 服务不可用")

    # Main content based on selected tab
    if tab == "📊 仪表板":
        show_dashboard(top_k, min_score)
    elif tab == "📝 报告生成":
        show_report_generation(st.session_state.last_scores)
    elif tab == "⏰ 任务调度":
        show_task_scheduling()
    elif tab == "🔧 系统设置":
        show_system_settings()


def show_dashboard(top_k: int, min_score: float):
    """Show main dashboard"""
    st.subheader("📊 高分股票池")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔄 同步数据", use_container_width=True):
            with st.spinner("正在同步数据..."):
                try:
                    with DataPipeline() as pipeline:
                        results = pipeline.full_sync()
                    st.success("✓ 数据同步完成")
                    st.json(results)
                except Exception as e:
                    st.error(f"✗ 同步失败: {e}")

    with col2:
        if st.button("⚡ 评分股票", use_container_width=True):
            with st.spinner("正在计算评分..."):
                try:
                    scorer = MultiFactorScorer()
                    scores = scorer.score_top_stocks(
                        limit=top_k, min_score=min_score
                    )
                    st.session_state.last_scores = scores
                    st.success(f"✓ 评分完成: {len(scores)} 只股票")
                except Exception as e:
                    st.error(f"✗ 评分失败: {e}")

    with col3:
        if st.button("📝 生成报告", use_container_width=True):
            if st.session_state.last_scores:
                with st.spinner("正在生成报告..."):
                    try:
                        report = st.session_state.report_generator.generate_portfolio_report(
                            st.session_state.last_scores, limit=10
                        )
                        st.session_state.portfolio_report = report
                        st.success("✓ 报告生成完成")
                    except Exception as e:
                        st.error(f"✗ 报告生成失败: {e}")
            else:
                st.warning("⚠️ 请先评分股票")

    with col4:
        if st.button("🌬️ 清空缓存", use_container_width=True):
            st.cache_data.clear()
            st.session_state.last_scores = []
            st.success("✓ 缓存已清空")

    st.markdown("---")

    # Display scores
    if st.session_state.last_scores:
        scores_data = [score.to_dict() for score in st.session_state.last_scores]
        df = pd.DataFrame(scores_data)

        # Stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("股票数量", len(df))
        with col2:
            st.metric("平均分数", f"{df['total_score'].mean():.2f}")
        with col3:
            st.metric("最高分数", f"{df['total_score'].max():.2f}")
        with col4:
            st.metric("最低分数", f"{df['total_score'].min():.2f}")

        st.markdown("")

        # Table
        display_df = df[
            [
                "symbol",
                "name",
                "price",
                "factor_a_score",
                "factor_b_score",
                "factor_c_score",
                "total_score",
            ]
        ].copy()
        display_df.columns = [
            "代码",
            "名称",
            "价格",
            "因子A(趋势)",
            "因子B(资金)",
            "因子C(板块)",
            "综合评分",
        ]

        st.dataframe(
            display_df.style.format(
                {
                    "价格": ":.2f",
                    "因子A(趋势)": ":.2f",
                    "因子B(资金)": ":.2f",
                    "因子C(板块)": ":.2f",
                    "综合评分": ":.2f",
                }
            ).background_gradient(
                subset=["综合评分"], cmap="RdYlGn", vmin=0, vmax=100
            ),
            use_container_width=True,
            height=400,
        )

        # Export
        st.markdown("---")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 下载CSV",
            data=csv,
            file_name=f"stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("👉 请先点击'评分股票'按钮")


def show_report_generation(scores: list):
    """Show report generation interface"""
    st.subheader("📝 报告生成")

    if not scores:
        st.warning("⚠️ 请先在仪表板中评分股票")
        return

    col1, col2 = st.columns([3, 1])

    with col1:
        st.write(f"已加载 {len(scores)} 只股票")

    with col2:
        report_type = st.radio(
            "报告类型",
            ["投资组合", "市场总结", "单股分析"],
            horizontal=True,
        )

    st.markdown("---")

    if report_type == "投资组合":
        st.subheader("投资组合分析报告")
        if st.button("生成报告", use_container_width=True):
            with st.spinner("正在生成报告..."):
                try:
                    report = st.session_state.report_generator.generate_portfolio_report(
                        scores, limit=10
                    )
                    st.markdown(report)
                    st.download_button(
                        "📥 下载报告",
                        data=report,
                        file_name=f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"✗ 报告生成失败: {e}")

    elif report_type == "市场总结":
        st.subheader("市场总结报告")
        if st.button("生成报告", use_container_width=True):
            with st.spinner("正在生成报告..."):
                try:
                    report_data = st.session_state.report_generator.generate_daily_summary(
                        scores
                    )
                    st.json(report_data)
                    st.markdown(report_data["summary_report"])
                except Exception as e:
                    st.error(f"✗ 报告生成失败: {e}")

    elif report_type == "单股分析":
        st.subheader("单股分析报告")
        selected_stock = st.selectbox(
            "选择股票",
            options=[f"{s.name} ({s.ts_code})" for s in scores],
        )
        if selected_stock and st.button("生成分析", use_container_width=True):
            stock = next(
                s
                for s in scores
                if f"{s.name} ({s.ts_code})" == selected_stock
            )
            with st.spinner("正在生成分析..."):
                try:
                    analysis = st.session_state.report_generator.generate_stock_analysis(
                        stock
                    )
                    st.markdown(analysis)
                except Exception as e:
                    st.error(f"✗ 分析生成失败: {e}")


def show_task_scheduling():
    """Show task scheduling interface"""
    st.subheader("⏰ 任务调度")

    scheduler = st.session_state.scheduler

    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("📋 已计划任务")

    with col2:
        if st.button("刷新状态", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # Task status
    st.subheader("任务状态")
    for task_name in ["data_sync", "scoring", "report_generation"]:
        status = scheduler.get_task_status(task_name)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**{status['name']}**")
        with col2:
            status_color = (
                "🟢"
                if status["last_status"] == "success"
                else "🔴"
                if status["last_status"] == "error"
                else "🟡"
            )
            st.write(f"状态: {status_color} {status['last_status']}")
        with col3:
            st.write(f"最后运行: {status['last_run'] or 'N/A'}")

    st.markdown("---")

    # Schedule configuration
    st.subheader("⏱️ 计划配置")

    col1, col2, col3 = st.columns(3)
    with col1:
        sync_time = st.time_input("数据同步时间", value=datetime.strptime("09:30", "%H:%M").time())
    with col2:
        score_time = st.time_input("评分时间", value=datetime.strptime("09:35", "%H:%M").time())
    with col3:
        report_time = st.time_input("报告生成时间", value=datetime.strptime("09:40", "%H:%M").time())

    if st.button("🚀 启动定时任务", use_container_width=True):
        try:
            scheduler.schedule_daily_routine(
                sync_time=sync_time.strftime("%H:%M"),
                score_time=score_time.strftime("%H:%M"),
                report_time=report_time.strftime("%H:%M"),
            )
            scheduler.start()
            st.success("✓ 定时任务已启动")
        except Exception as e:
            st.error(f"✗ 启动失败: {e}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⏸️ 暂停任务", use_container_width=True):
            try:
                scheduler.pause()
                st.success("✓ 任务已暂停")
            except Exception as e:
                st.error(f"✗ 暂停失败: {e}")

    with col2:
        if st.button("▶️ 恢复任务", use_container_width=True):
            try:
                scheduler.resume()
                st.success("✓ 任务已恢复")
            except Exception as e:
                st.error(f"✗ 恢复失败: {e}")

    # Job list
    st.markdown("---")
    st.subheader("📅 已计划的任务")
    jobs = scheduler.list_jobs()
    if jobs:
        jobs_df = pd.DataFrame(jobs)
        st.dataframe(jobs_df, use_container_width=True)
    else:
        st.info("暂无计划任务")


def show_system_settings():
    """Show system settings"""
    st.subheader("🔧 系统设置")

    st.write("**基础配置**")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("运行环境", config.ENV.upper())
    with col2:
        st.metric("调试模式", "启用" if config.DEBUG else "禁用")

    st.markdown("---")

    st.write("**数据库配置**")
    st.text(f"数据库路径: {config.DB_PATH}")
    st.text(f"数据目录: {config.DATA_DIR}")
    st.text(f"日志目录: {config.LOGS_DIR}")

    st.markdown("---")

    st.write("**LLM 配置**")
    st.text(f"API 地址: {config.LLM_BASE_URL}")
    st.text(f"模型: {config.LLM_MODEL}")
    st.text(f"最大 Token: {config.LLM_MAX_TOKENS}")

    st.markdown("---")

    st.write("**API 配置**")
    st.text(f"最大重试次数: {config.MAX_RETRIES}")
    st.text(f"退避因子: {config.RETRY_BACKOFF_FACTOR}")
    st.text(f"请求超时: {config.REQUEST_TIMEOUT}s")
    st.text(f"速率限制延迟: {config.RATE_LIMIT_DELAY}s")

    st.markdown("---")

    st.write("**数据同步配置**")
    st.text(f"批处理大小: {config.SYNC_BATCH_SIZE}")
    st.text(f"日线数据同步天数: {config.SYNC_QUOTE_DAYS}")
    st.text(f"资金流向同步天数: {config.SYNC_FUND_FLOW_DAYS}")


if __name__ == "__main__":
    main()
