"""LLM module for report generation

Provides LLM client and report generation services.
"""

from src.llm.llm_client import LLMClient
from src.llm.report_generator import ReportGenerator

__all__ = ["LLMClient", "ReportGenerator"]
