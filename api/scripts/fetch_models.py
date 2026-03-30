# codes/api/scripts/fetch_models.py
"""
Download & place model files into the backend's models/ tree.

Usage (PowerShell):
  cd textor/codes/api
  python -m venv .venv
  . .\.venv\Scripts\Activate.ps1
  pip install --upgrade pip
  pip install requests tqdm transformers torch easyocr paddleocr

  # basic (no kraken URLs; still warms TrOCR/EasyOCR/Tesseract)
  python scripts/fetch_models.py

  # with Kraken recognizer URLs (optional)
  python scripts/fetch_models.py ^
    --kraken-en-url "https://<direct-url-to-latin>.mlmodel" ^
    --kraken-hi-url "https://<direct-url-to-devanagari>.mlmodel"

Notes:
- If you don't have direct .mlmodel URLs yet, run without those flags; you can drop the files later into:
    models/kraken/latin/ and models/kraken/devanagari/
- Tesseract binaries are separate; this only downloads traineddata files locally. Ensure your app sets TESSDATA_PREFIX.
"""

import argparse
import os
import sys
import shutil
from pathlib import Path

import requests
from tqdm import tqdm

# ------------------------
# target layout
# ------------------------
ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
DIRS = {
    "kraken_latin": MODELS / "kraken" / "latin",
    "kraken_deva": MODELS / "kraken" / "devanagari",
    "hf_cache":    MODELS / "hf" / "cache",
    "easyocr":     MODELS / "easyocr" / "model",
    "paddle_det":  MODELS / "paddleocr" / "det" / "en",
    "paddle_rec":  MODELS / "paddleocr" / "rec" / "en",
    "paddle_cls":  MODELS / "paddleocr" / "cls",
    "tessdata":    MODELS / "tesseract" / "tessdata",
    "custom_tel":  MODELS / "custom" / "telugu",
    "custom_tam":  MODELS / "custom" / "tamil",
    "custom_ban":  MODELS / "custom" / "bangla",
    "custom_guj":  MODELS / "custom" / "gujarati",
    "custom_kan":  MODELS / "custom" / "kannada",
    "custom_mal":  MODELS / "custom" / "malayalam",
    "custom_odi":  MODELS / "custom" / "odia",
}

def ensure_dirs():
    for p in DIRS.values():
        p.mkdir(parents=True, exist_ok=True)

def download(url: str, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        tmp = out.with_suffix(out.suffix + ".part")
        with open(tmp, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=out.name
        ) as bar:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        tmp.replace(out)

def put_env_line(dotenv: Path, key: str, value: str):
    lines = []
    if dotenv.exists():
        lines = dotenv.read_text(encoding="utf-8").splitlines()
        # replace if exists
        replaced = False
        for i, ln in enumerate(lines):
            if ln.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{key}={value}")
    else:
        lines = [f"{key}={value}"]
    dotenv.write_text("\n".join(lines) + "\n", encoding="utf-8")

def warm_hf_trocr(cache_dir: Path):
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_dir))
    os.environ.setdefault("HF_HOME", str(cache_dir))
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        print("⏬ Downloading HuggingFace TrOCR (base) into cache…")
        TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
        VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    except Exception as e:
        print(f"⚠️  HF warm failed: {e}")

def warm_easyocr(model_dir: Path):
    # This triggers downloads on Reader init if missing.
    try:
        import easyocr
        print("⏬ Downloading EasyOCR (en)…")
        easyocr.Reader(['en'], model_storage_directory=str(model_dir), download_enabled=True, gpu=False)
        print("⏬ Downloading EasyOCR (hi)…")
        easyocr.Reader(['hi'], model_storage_directory=str(model_dir), download_enabled=True, gpu=False)
    except Exception as e:
        print(f"⚠️  EasyOCR warm failed: {e}")

def warm_paddleocr():
    # Optional: just trigger download to PaddleOCR cache (usually ~/.paddleocr).
    try:
        from paddleocr import PaddleOCR
        print("⏬ Warming PaddleOCR (en)…")
        PaddleOCR(use_angle_cls=True, lang='en')  # will download to its cache on first run
    except Exception as e:
        print(f"⚠️  PaddleOCR warm failed: {e}")

def write_dotenv_defaults():
    dotenv = ROOT / ".env"
    put_env_line(dotenv, "KRAKEN_MODEL_PATH_EN", "./models/kraken/latin/latin.mlmodel")
    put_env_line(dotenv, "KRAKEN_MODEL_PATH_HI", "./models/kraken/devanagari/devanagari.mlmodel")
    put_env_line(dotenv, "TRANSFORMERS_CACHE", "./models/hf/cache")
    put_env_line(dotenv, "HF_HOME", "./models/hf/cache")
    put_env_line(dotenv, "TESSDATA_PREFIX", "./models/tesseract")
    print(f"✅ Wrote/updated {dotenv}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kraken-en-url", default="", help="Direct URL to a Latin .mlmodel (optional)")
    ap.add_argument("--kraken-hi-url", default="", help="Direct URL to a Devanagari .mlmodel (optional)")
    ap.add_argument("--skip-paddle", action="store_true", help="Skip warming PaddleOCR")
    args = ap.parse_args()

    ensure_dirs()
    write_dotenv_defaults()

    # 1) Kraken recognizers (optional, via direct URLs if you have them)
    if args.kraken_en_url:
        out = DIRS["kraken_latin"] / "latin.mlmodel"
        print(f"⏬ Downloading Kraken Latin model → {out}")
        download(args.kraken_en_url, out)
    else:
        print("ℹ️  Kraken Latin URL not provided. You can place .mlmodel later into models/kraken/latin/")

    if args.kraken_hi_url:
        out = DIRS["kraken_deva"] / "devanagari.mlmodel"
        print(f"⏬ Downloading Kraken Devanagari model → {out}")
        download(args.kraken_hi_url, out)
    else:
        print("ℹ️  Kraken Devanagari URL not provided. You can place .mlmodel later into models/kraken/devanagari/")

    # 2) HuggingFace (TrOCR)
    warm_hf_trocr(DIRS["hf_cache"])

    # 3) EasyOCR (en + hi)
    warm_easyocr(DIRS["easyocr"])

    # 4) Tesseract traineddata (eng + hin) from tessdata_best
    tessbest = "https://github.com/tesseract-ocr/tessdata_best/raw/main"
    for lang in ("eng", "hin"):
        url = f"{tessbest}/{lang}.traineddata"
        out = DIRS["tessdata"] / f"{lang}.traineddata"
        if not out.exists():
            print(f"⏬ Downloading Tesseract {lang}.traineddata → {out}")
            try:
                download(url, out)
            except Exception as e:
                print(f"⚠️  Could not fetch {lang}.traineddata: {e}")
        else:
            print(f"✔️  {out} already exists")

    # 5) (Optional) PaddleOCR warm
    if not args.skip_paddle:
        warm_paddleocr()

    print("\n✅ Done.")
    print(f"   Models root: {MODELS}")
    print("   You can now set/confirm these in .env:")
    print("     KRAKEN_MODEL_PATH_EN=./models/kraken/latin/latin.mlmodel")
    print("     KRAKEN_MODEL_PATH_HI=./models/kraken/devanagari/devanagari.mlmodel")
    print("     TRANSFORMERS_CACHE=./models/hf/cache")
    print("     HF_HOME=./models/hf/cache")
    print("     TESSDATA_PREFIX=./models/tesseract")
    print("\n   If you later obtain Kraken .mlmodel URLs/DOIs, re-run with --kraken-*-url or drop the files into the folders above.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
