"""Project paths and default RAG settings."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
EVAL_DATA_DIR = DATA_DIR / "eval"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
RESULTS_DIR = PROJECT_ROOT / "results"

DEFAULT_COLLECTION_NAME = "investment_rag"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_RETRIEVAL_K = 5

