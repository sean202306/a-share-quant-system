"""Data module for A-Share Quantitative Analysis System

Handles data acquisition, storage, and pipeline orchestration.
"""

from src.data.pipeline import DataPipeline
from src.data.tushare_client import TushareClient

__all__ = ["DataPipeline", "TushareClient"]
