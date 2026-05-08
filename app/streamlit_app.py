"""Streamlit Dashboard for A-Share Quantitative Analysis System

Real-time visualization of stock scores, fund flows, and technical analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path

from src.config import config
from src.analysis.scoring import MultiFactorScorer
from src.data.pipeline import DataPipeline
from src.logger import get_logger

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="A-Share 量化分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .score-high {
        color: #00dd00;
        font-weight: bold;
    }
    .score-medium {
        color: #ff9800;
        font-weight: bold;
    }
    .score-low {
        color: #ff0000;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_score_color(score: float) -> str:
    """Get color based on score"""
    if score >= 70:
        return "#00dd00"  # Green
    elif score >= 50:
        return "#ff9800"  # Orange
    else:
        return "#ff0000"  # Red


def format_number(num: float, decimals: int = 2) -> str:
    """Format number with thousand separator"""
    if num is None:
        return "N/A"
    return f"{num:,.{decimals}f}"


@st.cache_data(ttl=3600)
def load_top_stocks(limit: int = 50, min_score: float = 50.0) -> list:
    """Load top scored stocks (cached for 1 hour)"""
    try:
        scorer = MultiFactorScorer()
        scores = scorer.score_top_stocks(limit=limit, min_score=min_score)
        return scores
    except Exception as e:
        st.error(f"Error loading scores: {e}")
        logger.error(f"Error in load_top_stocks: {e}")
        return []


@st.cache_data(ttl=1800)
def sync_data() -> dict:
    """Sync data from Tushare (cached for 30 minutes)"""
    try:
        with DataPipeline() as pipeline:
            results = pipeline.full_sync()
        return results
    except Exception as e:
        st.error(f"Error syncing data: {e}")
        logger.error(f"Error in sync_data: {e}")
        return {"status": "error", "error": str(e)}


def main():
    """Main dashboard"""

    # Header
    st.title("📈 A-Share 量化分析系统")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ 控制面板")

        # Sync button
        if st.button("🔄 同步数据", use_container_width=True):
            st.cache_data.clear()
            with st.spinner("正在同步数据..."):
                result = sync_data()
            st.success("数据同步完成！")
            st.write(result)

        st.markdown("---")

        # Scoring parameters
        st.subheader("评分参数")
        top_k = st.slider("显示前N只股票", min_value=10, max_value=100, value=50, step=10)
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

        st.caption(
            f"数据库: {config.DB_PATH}\n最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    # Main content
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("最低分数", f"{min_score:.0f}", "%")
    with col2:
        st.metric("查看数量", f"{top_k}", "只")
    with col3:
        st.metric("环境", config.ENV.upper())

    st.markdown("---")

    # Load and display scores
    st.subheader("📊 高分股票池")

    with st.spinner("正在计算评分..."):
        scores = load_top_stocks(limit=top_k, min_score=min_score)

    if not scores:
        st.warning("未找到符合条件的股票。请检查数据或调整参数。")
    else:
        # Convert to DataFrame
        scores_data = [score.to_dict() for score in scores]
        df = pd.DataFrame(scores_data)

        # Display stats
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

        # Display table
        st.subheader("详细数据")

        # Format DataFrame for display
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

        # Charts
        st.markdown("---")
        st.subheader("📈 可视化分析")

        col1, col2 = st.columns(2)

        # Factor score distribution
        with col1:
            fig = go.Figure()
            fig.add_trace(
                go.Box(
                    y=df["factor_a_score"],
                    name="因子A (趋势)",
                    marker_color="lightblue",
                )
            )
            fig.add_trace(
                go.Box(
                    y=df["factor_b_score"],
                    name="因子B (资金)",
                    marker_color="lightgreen",
                )
            )
            fig.add_trace(
                go.Box(
                    y=df["factor_c_score"],
                    name="因子C (板块)",
                    marker_color="lightyellow",
                )
            )
            fig.update_layout(
                title="因子评分分布",
                yaxis_title="评分",
                height=400,
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Score distribution histogram
        with col2:
            fig = go.Figure()
            fig.add_trace(
                go.Histogram(
                    x=df["total_score"],
                    nbinsx=20,
                    marker_color="steelblue",
                    name="综合评分",
                )
            )
            fig.update_layout(
                title="综合评分分布",
                xaxis_title="评分",
                yaxis_title="股票数量",
                height=400,
                hovermode="x",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Top 10 stocks
        col1, col2 = st.columns(2)

        with col1:
            top10 = df.nlargest(10, "total_score")[["symbol", "name", "total_score"]]
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=top10["total_score"],
                        y=top10["name"],
                        orientation="h",
                        marker=dict(
                            color=top10["total_score"],
                            colorscale="Viridis",
                            showscale=False,
                        ),
                        text=top10["total_score"].apply(lambda x: f"{x:.2f}"),
                        textposition="outside",
                    )
                ]
            )
            fig.update_layout(
                title="Top 10 高分股票",
                xaxis_title="综合评分",
                height=400,
                margin=dict(l=150),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Factor correlation
        with col2:
            fig = go.Figure(
                data=[
                    go.Scatter(
                        x=df["factor_b_score"],
                        y=df["factor_a_score"],
                        mode="markers",
                        marker=dict(
                            size=df["total_score"] / 5,
                            color=df["total_score"],
                            colorscale="Viridis",
                            showscale=True,
                            colorbar=dict(title="综合评分"),
                        ),
                        text=df["name"],
                        hovertemplate="<b>%{text}</b><br>资金评分: %{x:.2f}<br>趋势评分: %{y:.2f}",
                    )
                ]
            )
            fig.update_layout(
                title="因子关联性分析",
                xaxis_title="因子B (资金评分)",
                yaxis_title="因子A (趋势评分)",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

        # Export option
        st.markdown("---")
        st.subheader("📥 数据导出")

        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 下载 CSV",
            data=csv,
            file_name=f"stocks_scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")
    st.caption(
        "本系统基于历史数据和技术指标进行量化分析，不构成投资建议��\n"
        "投资有风险，入市需谨慎。"
    )


if __name__ == "__main__":
    main()
