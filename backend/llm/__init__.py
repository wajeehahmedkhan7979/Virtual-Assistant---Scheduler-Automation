"""
Initialize LLM package.
"""
try:
    from .classifier import EmailClassifier
except Exception:
    EmailClassifier = None

try:
    from .analyzer import DataAnalyzer, S3DataHandler
except Exception:
    DataAnalyzer = None
    S3DataHandler = None

__all__ = [
    "EmailClassifier",
    "DataAnalyzer",
    "S3DataHandler",
]
