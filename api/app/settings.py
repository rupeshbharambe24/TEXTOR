# app/settings.py
from pathlib import Path
import os

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = BASE_DIR / "models"

# Kraken recognizers
KRAKEN_MODEL_PATH_EN = os.getenv(
    "KRAKEN_MODEL_PATH_EN",
    str(MODELS_DIR / "kraken" / "latin" / "latin.mlmodel")
)
KRAKEN_MODEL_PATH_HI = os.getenv(
    "KRAKEN_MODEL_PATH_HI",
    str(MODELS_DIR / "kraken" / "devanagari" / "devanagari.mlmodel")
)

# HuggingFace cache (TrOCR)
HF_HOME = os.getenv("HF_HOME", str(MODELS_DIR / "hf" / "cache"))
TRANSFORMERS_CACHE = os.getenv("TRANSFORMERS_CACHE", str(MODELS_DIR / "hf" / "cache"))

# Tesseract data prefix (must be parent of tessdata/)
TESSDATA_PREFIX = os.getenv("TESSDATA_PREFIX", str(MODELS_DIR / "tesseract"))

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
