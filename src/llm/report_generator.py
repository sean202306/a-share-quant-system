"""Report Generation Module

Generates investment reports using LLM based on stock scores.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.config import config
from src.logger import get_logger
from src.analysis.scoring import StockScore
from src.llm.llm_client import LLMClient

logger = get_logger(__name__)


class ReportGenerator:
    """Generate investment reports using LLM"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize report generator

        Args:
            llm_client: LLMClient instance (creates default if None)
        """
        self.llm_client = llm_client or LLMClient()
        logger.info("ReportGenerator initialized")

    def _format_stock_data(self, score: StockScore) -> str:
        """Format stock score data for LLM prompt

        Args:
            score: StockScore object

        Returns:
            Formatted stock information string
        """
        return f"""
股票信息:
- 代码: {score.ts_code}
- 名称: {score.name}
- 当前价格: ¥{score.price:.2f}

评分指标:
- 综合评分: {score.total_score:.2f}/100
- 因子A (趋势与动量): {score.factor_a_score:.2f}/100
- 因子B (资金面): {score.factor_b_score:.2f}/100
- 因子C (板块共振): {score.factor_c_score:.2f}/100

技术面数据:
- EMA20: {score.ema20:.2f if score.ema20 else 'N/A'}
- EMA60: {score.ema60:.2f if score.ema60 else 'N/A'}
- MACD: {score.macd:.4f if score.macd else 'N/A'}
- 资金净流入 (10天): {score.net_inflow:.2f if score.net_inflow else 'N/A'} 万元
"""

    def generate_stock_analysis(
        self, score: StockScore, language: str = "zh"
    ) -> str:
        """Generate analysis for a single stock

        Args:
            score: StockScore object
            language: Language code ('zh' for Chinese, 'en' for English)

        Returns:
            Generated analysis text
        """
        stock_data = self._format_stock_data(score)

        if language == "zh":
            prompt = f"""
请基于以下股票量化分析数据，生成一份简明的投资分析说明。

{stock_data}

请从以下几个方面分析:
1. 趋势判断: 基于因子A评分，分析股票的技术面强弱
2. 资金面分析: 基于因子B评分，分析主力资金动向
3. 板块共振: 基于因子C评分，分析板块的整体表现
4. 综合评价: 总体判断该股是否值得关注
5. 风险提示: 可能的风险因素

要求:
- 分析简明扼要，不超过500字
- 逻辑清晰，避免过度解读
- 不构成投资建议
"""
        else:
            prompt = f"""
Based on the following quantitative analysis data, provide a brief investment analysis.

{stock_data}

Analyze from these perspectives:
1. Trend Analysis: Technical strength based on Factor A
2. Capital Flow Analysis: Main fund movement based on Factor B
3. Sector Resonance: Overall sector performance based on Factor C
4. Overall Assessment: Whether this stock is worth monitoring
5. Risk Warning: Potential risk factors

Requirements:
- Concise analysis, not exceeding 300 words
- Clear logic, avoid over-interpretation
- Not investment advice
"""

        try:
            analysis = self.llm_client.generate(
                prompt, max_tokens=1000, temperature=0.5
            )
            logger.info(f"Generated analysis for {score.name}")
            return analysis
        except Exception as e:
            logger.error(f"Failed to generate analysis: {e}")
            return f"分析生成失败: {str(e)}"

    def generate_portfolio_report(
        self, scores: List[StockScore], limit: int = 10
    ) -> str:
        """Generate portfolio report for top stocks

        Args:
            scores: List of StockScore objects
            limit: Number of top stocks to include

        Returns:
            Generated report text
        """
        # Select top stocks
        top_scores = sorted(
            scores, key=lambda x: x.total_score, reverse=True
        )[:limit]

        # Format stock list
        stock_list = "\n".join(
            [
                f"{i+1}. {s.name} ({s.ts_code}): {s.total_score:.2f}分 \\n"
                f"   因子A:{s.factor_a_score:.2f} | "
                f"因子B:{s.factor_b_score:.2f} | "
                f"因子C:{s.factor_c_score:.2f}"
                for i, s in enumerate(top_scores)
            ]
        )

        prompt = f"""
请根据以下精选股票池的量化评分数据，生成一份投资组合分析报告。

{stock_list}

报告应包含:
1. 整体市场观点: 当前市场特征与机会
2. 组合特点: 选中股票的共性与差异
3. 主要亮点: 最值得关注的几只股票及原因
4. 风险提示: 可能的系统性风险
5. 建议: 后续关注重点

要求:
- 报告长度300-500字
- 基于数据进行分析，避免主观臆断
- 客观中立的表述风格
- 明确说明不构成投资建议
"""

        try:
            report = self.llm_client.generate(
                prompt, max_tokens=1500, temperature=0.6
            )
            logger.info(f"Generated portfolio report for {len(top_scores)} stocks")
            return report
        except Exception as e:
            logger.error(f"Failed to generate portfolio report: {e}")
            return f"报告生成失败: {str(e)}"

    def generate_daily_summary(
        self, scores: List[StockScore]
    ) -> Dict[str, Any]:
        """Generate daily summary report

        Args:
            scores: List of StockScore objects

        Returns:
            Dictionary with summary data and report
        """
        timestamp = datetime.now().isoformat()

        # Calculate statistics
        if not scores:
            logger.warning("No stocks provided for daily summary")
            return {
                "timestamp": timestamp,
                "total_stocks": 0,
                "average_score": 0,
                "summary": "无数据",
            }

        total_scores = [s.total_score for s in scores]
        avg_score = sum(total_scores) / len(total_scores)
        max_score = max(total_scores)
        min_score = min(total_scores)

        # Count factor leaders
        factor_a_leader = max(scores, key=lambda x: x.factor_a_score)
        factor_b_leader = max(scores, key=lambda x: x.factor_b_score)
        factor_c_leader = max(scores, key=lambda x: x.factor_c_score)

        summary_data = f"""
今日选股总结 ({datetime.now().strftime('%Y-%m-%d')})

数据概览:
- 评分股票总数: {len(scores)}
- 平均评分: {avg_score:.2f}/100
- 最高评分: {max_score:.2f}
- 最低评分: {min_score:.2f}

各因子领先股:
- 趋势之星 (因子A): {factor_a_leader.name} - {factor_a_leader.factor_a_score:.2f}
- 资金热点 (因子B): {factor_b_leader.name} - {factor_b_leader.factor_b_score:.2f}
- 板块先锋 (因子C): {factor_c_leader.name} - {factor_c_leader.factor_c_score:.2f}
"""

        prompt = f"""
请根据以下选股数据，生成一份简明的市场观察总结。

{summary_data}

请从以下角度分析:
1. 市场特征: 当前市场选股的主要特点
2. 热点板块: 主要受关注的板块和方向
3. 关键观察: 最需要重点关注的现象
4. 后续展望: 可能的市场走向

要求:
- 长度150-250字
- 简洁有力，直击要点
- 客观数据支撑
"""

        try:
            report = self.llm_client.generate(
                prompt, max_tokens=800, temperature=0.6
            )
        except Exception as e:
            logger.error(f"Failed to generate daily summary: {e}")
            report = "报告生成失败"

        return {
            "timestamp": timestamp,
            "total_stocks": len(scores),
            "average_score": round(avg_score, 2),
            "max_score": max_score,
            "min_score": min_score,
            "factor_a_leader": factor_a_leader.to_dict(),
            "factor_b_leader": factor_b_leader.to_dict(),
            "factor_c_leader": factor_c_leader.to_dict(),
            "summary_report": report,
        }

    def generate_with_streaming(
        self, score: StockScore, callback=None
    ) -> str:
        """Generate analysis with streaming output

        Args:
            score: StockScore object
            callback: Callback function to receive text chunks

        Returns:
            Complete generated text
        """
        stock_data = self._format_stock_data(score)

        prompt = f"""
请基于以下股票量化分析数据，生成一份简明的投资分析说明。

{stock_data}

请从以下几个方面分析:
1. 趋势判断: 基于因子A评分，分析股票的技术面强弱
2. 资金面分析: 基于因子B评分，分析主力资金动向
3. 板块共振: 基于因子C评分，分析板块的整体表现
4. 综合评价: 总体判断该股是否值得关注

要求: 简明扼要，不超过500字
"""

        complete_text = ""
        try:
            for chunk in self.llm_client.generate_stream(
                prompt, max_tokens=1000
            ):
                complete_text += chunk
                if callback:
                    callback(chunk)
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")

        return complete_text
