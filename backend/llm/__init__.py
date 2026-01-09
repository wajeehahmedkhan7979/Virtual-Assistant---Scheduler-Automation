"""
Initialize LLM package.
"""
from .classifier import EmailClassifier

try:
    from .analyzer import DataAnalyzer, S3DataHandler
except ImportError:
    DataAnalyzer = None
    S3DataHandler = None

__all__ = [
    "EmailClassifier",
    "DataAnalyzer",
    "S3DataHandler",
]
