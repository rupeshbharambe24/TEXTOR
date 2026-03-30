import os, json, logging, tempfile, subprocess
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from PIL import Image
import numpy as np

# Settings/paths
from app.settings import (
    KRAKEN_MODEL_PATH_EN,
    KRAKEN_MODEL_PATH_HI,
    HF_HOME,
    TRANSFORMERS_CACHE,
    TESSDATA_PREFIX,
    ALLOWED_ORIGINS,
)
from dotenv import load_dotenv
load_dotenv() 
import os
os.environ.setdefault("HF_HOME", HF_HOME)
os.environ.setdefault("TRANSFORMERS_CACHE", TRANSFORMERS_CACHE)
os.environ.setdefault("TESSDATA_PREFIX", TESSDATA_PREFIX)

# Optional imports guarded, so server still runs if lib missing
try:
    from paddleocr import PaddleOCR
    _paddle_ok = True
except Exception:
    _paddle_ok = False

import easyocr
import pytesseract

from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch
import cv2

from docling.document_converter import DocumentConverter

# NLP
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from keybert import KeyBERT
import yake

# --- FastAPI app ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log = logging.getLogger("api")
logging.basicConfig(level=logging.INFO)

# --- Singletons / lazy loaders ---
_ocr_en = None                 # PaddleOCR EN
_reader_en = None              # EasyOCR en
_reader_hi = None              # EasyOCR hi
_trocr_proc = None
_trocr_model = None
_kw = None
_yake = None

# ---------- helpers ----------
def summarize_text(text: str, sentences: int = 3) -> str:
    if not text: return ""
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    s = TextRankSummarizer()
    return " ".join(str(x) for x in s(parser.document, sentences))

def extract_keywords(text: str, top_n: int = 10):
    global _kw, _yake
    if _kw is None: _kw = KeyBERT()
    if _yake is None: _yake = yake.KeywordExtractor(lan="en", top=top_n)
    k1 = [k for k,_ in _yake.extract_keywords(text)]
    k2 = [k for k,_ in _kw.extract_keywords(text, top_n=top_n)]
    seen=set(); out=[]
    for k in k1+k2:
        if k not in seen:
            out.append(k); seen.add(k)
    return out[:top_n]

def _run_kraken_segment(ipath: str, jpath: str):
    """UTF-8 safe Kraken segmentation with quiet logging; avoids Windows cp1252 issues."""
    env = {**os.environ, "PYTHONUTF8":"1", "PYTHONIOENCODING":"utf-8"}
    cmd = ["kraken","-q","-i", ipath, jpath, "segment", "-bl"]
    subprocess.run(
        cmd, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    with open(jpath, "r", encoding="utf-8") as f:
        return json.load(f)

def _opencv_line_boxes(pil_img, pad: int = 32):
    gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    k = max(3, gray.shape[1] // 30)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, 3))
    dil = cv2.dilate(thr, kernel, iterations=1)
    cnts, _ = cv2.findContours(dil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in cnts]
    boxes = sorted(boxes, key=lambda b: b[1])  # top-to-bottom
    out = []
    H,W = gray.shape
    for (x,y,w,h) in boxes:
        x2 = max(x - pad, 0); y2 = max(y - pad, 0)
        w2 = min(w + 2*pad, W - x2); h2 = min(h + 2*pad, H - y2)
        out.append({"x":int(x2),"y":int(y2),"w":int(w2),"h":int(h2)})
    return out

def _enhance_for_trocr(img_rgb):
    g = cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2GRAY)
    g = cv2.fastNlMeansDenoising(g, h=15)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    g = clahe.apply(g)
    g = cv2.resize(g, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    return Image.fromarray(cv2.cvtColor(g, cv2.COLOR_GRAY2RGB))

def _paddle_or_easyocr_en(image_bytes: bytes):
    """Printed EN: try PaddleOCR if installed, else EasyOCR."""
    global _ocr_en, _reader_en
    boxes, texts = [], []
    if _paddle_ok:
        if _ocr_en is None:
            # Prefer explicit dirs if present; else let Paddle use cache
            kwargs = dict(use_angle_cls=True, lang='en')
            if Path(PADDLE_DET_DIR).exists() and Path(PADDLE_REC_DIR).exists():
                kwargs.update(det_model_dir=PADDLE_DET_DIR, rec_model_dir=PADDLE_REC_DIR)
                if Path(PADDLE_CLS_DIR).exists(): kwargs.update(cls_model_dir=PADDLE_CLS_DIR)
            _ocr_en = PaddleOCR(**kwargs)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes); tmp.flush()
            out = _ocr_en.ocr(tmp.name, cls=True)
        for line in out:
            for det in line:
                poly, (txt, _) = det
                xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
                x = min(xs); y = min(ys); w = max(xs)-x; h = max(ys)-y
                boxes.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"text":txt})
                texts.append(txt)
        return "\n".join(texts), boxes

    # EasyOCR fallback
    if _reader_en is None:
        _reader_en = easyocr.Reader(['en'], model_storage_directory=EASYOCR_MODEL_DIR, download_enabled=False)
    res = _reader_en.readtext(image_bytes)
    for (x1,y1,x2,y2,x3,y3,x4,y4), txt, conf in res:
        x = min(x1,x2,x3,x4); y = min(y1,y2,y3,y4); w = max(x1,x2,x3,x4)-x; h = max(y1,y2,y3,y4)-y
        boxes.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"text":txt})
        texts.append(txt)
    return "\n".join(texts), boxes

def _easyocr_hi(image_bytes: bytes):
    global _reader_hi
    if _reader_hi is None:
        _reader_hi = easyocr.Reader(['hi'], model_storage_directory=EASYOCR_MODEL_DIR, download_enabled=False)
    boxes, texts = [], []
    res = _reader_hi.readtext(image_bytes)
    for (x1,y1,x2,y2,x3,y3,x4,y4), txt, conf in res:
        x = min(x1,x2,x3,x4); y = min(y1,y2,y3,y4); w = max(x1,x2,x3,x4)-x; h = max(y1,y2,y3,y4)-y
        boxes.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"text":txt})
        texts.append(txt)
    return "\n".join(texts), boxes

def _tesseract_text(pil_img, lang_code):
    try:
        return pytesseract.image_to_string(pil_img, lang=lang_code)
    except Exception as e:
        log.error("tesseract error: %s", e)
        return ""

def _available_registry():
    reg = {
        "printed": {
            "en": {"paddleocr": _paddle_ok, "easyocr": True, "tesseract": True},
            "hi": {"easyocr": True, "tesseract": True}
        },
        "handwriting": {
            "en": {"trocr": True, "kraken": bool(Path(KRAKEN_MODEL_PATH_EN).exists())},
            "hi": {"kraken": bool(Path(KRAKEN_MODEL_PATH_HI).exists()), "easyocr": True}
        },
        "layout": {"any": {"docling": True}}
    }
    return reg

# ---------- endpoints ----------
@app.get("/v1/models")
def list_models():
    return _available_registry()

@app.post("/v1/ocr")
async def ocr_endpoint(
    file: UploadFile = File(...),
    task: str = Form(...),     # 'printed' | 'handwriting' | 'layout'
    lang: str = Form('en'),    # 'en' | 'hi'
    model: str = Form(None)    # optional override
):
    data = await file.read()
    result = {"text": "", "boxes": [], "layout": None, "summary": "", "keywords": [], "debug": {}}
    pipeline = {"task": task, "lang": lang, "segmenter": None, "recognizer": None}
    fname = getattr(file, "filename", "upload")
    log.info("/v1/ocr: task=%s lang=%s model=%s filename=%s size=%d", task, lang, model, fname, len(data))

    # ---- PRINTED ----
    if task == "printed":
        if lang == "en":
            # prefer Paddle, fallback EasyOCR
            txt, boxes = _paddle_or_easyocr_en(data)
            result["text"], result["boxes"] = txt, boxes
            pipeline.update(segmenter="detector", recognizer="paddleocr" if _paddle_ok else "easyocr")
        elif lang == "hi":
            # prefer EasyOCR; fallback Tesseract
            txt, boxes = _easyocr_hi(data)
            if not txt.strip():
                pil = Image.open(BytesIO(data)).convert("RGB")
                txt = _tesseract_text(pil, "hin")
            result["text"], result["boxes"] = txt, boxes
            pipeline.update(segmenter="detector", recognizer="easyocr/tesseract")

    # ---- HANDWRITING ----
    elif task == "handwriting":
        # segment lines with Kraken (safe), fallback to OpenCV
        with tempfile.TemporaryDirectory() as tdir:
            ipath = os.path.join(tdir, "in.png")
            base_img = Image.open(BytesIO(data)).convert("RGB")
            base_img.save(ipath)
            jpath = os.path.join(tdir, "lines.json")

            boxes = []
            try:
                seg = _run_kraken_segment(ipath, jpath)
                pipeline["segmenter"] = "kraken"
                # build crops list
                crops = []
                for ln in seg.get("lines", []):
                    if "baseline" in ln and ln["baseline"]:
                        xs = [p[0] for p in ln["baseline"]]; ys = [p[1] for p in ln["baseline"]]
                        pad = 32
                        x = max(min(xs)-pad, 0); y = max(min(ys)-pad, 0)
                        w = (max(xs)-min(xs)) + 2*pad; h = (max(ys)-min(ys)) + 2*pad
                    elif "box" in ln and len(ln["box"]) == 4:
                        x,y,w,h = ln["box"]
                    else:
                        continue
                    crop = base_img.crop((x,y,x+w,y+h)).convert("RGB")
                    crops.append((x,y,w,h,crop))
            except Exception as e:
                log.error("kraken segmentation failed: %s", e)
                pipeline["segmenter"] = "opencv"
                bxs = _opencv_line_boxes(base_img)
                crops = [(b["x"],b["y"],b["w"],b["h"], base_img.crop((b["x"],b["y"],b["x"]+b["w"],b["y"]+b["h"])) .convert("RGB")) for b in bxs]

            texts = []
            rec = (model or "").lower()

            # choose recognizer by language + availability
            if lang == "en":
                # default to TrOCR
                global _trocr_proc, _trocr_model
                if _trocr_proc is None:
                    _trocr_proc = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
                if _trocr_model is None:
                    _trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
                pipeline["recognizer"] = "trocr"
                for i, (x,y,w,h,crop) in enumerate(crops):
                    crop2 = _enhance_for_trocr(crop)
                    pixel_values = _trocr_proc(images=crop2, return_tensors="pt").pixel_values
                    with torch.no_grad():
                        ids = _trocr_model.generate(pixel_values, max_length=160, num_beams=5, early_stopping=True, length_penalty=0.1)
                    line_text = _trocr_proc.batch_decode(ids, skip_special_tokens=True)[0]
                    texts.append(line_text)
                    boxes.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"text":line_text,"lineId":str(i)})

            elif lang == "hi":
                # prefer Kraken Devanagari recognizer if file exists; else EasyOCR('hi')
                if Path(KRAKEN_MODEL_PATH_HI).exists():
                    pipeline["recognizer"] = "kraken-devanagari"
                    env = {**os.environ, "PYTHONUTF8":"1", "PYTHONIOENCODING":"utf-8"}
                    for i,(x,y,w,h,crop) in enumerate(crops):
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as limg, \
                             tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as ltxt:
                            crop.save(limg.name)
                            subprocess.run(
                                ["kraken","-q","-i", limg.name, ltxt.name, "ocr", "-m", KRAKEN_MODEL_PATH_HI],
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                            )
                            line_text = Path(ltxt.name).read_text(encoding="utf-8").strip()
                        texts.append(line_text)
                        boxes.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"text":line_text,"lineId":str(i)})
                else:
                    pipeline["recognizer"] = "easyocr-hi"
                    txt_all, _ = _easyocr_hi(data)  # quick path if you prefer per-line: run on crops
                    if not txt_all.strip():
                        # try per line with EasyOCR for better recall
                        global _reader_hi
                        if _reader_hi is None:
                            _reader_hi = easyocr.Reader(['hi'], model_storage_directory=EASYOCR_MODEL_DIR, download_enabled=False)
                        for i,(x,y,w,h,crop) in enumerate(crops):
                            res = _reader_hi.readtext(np.array(crop))
                            line_text = " ".join([t for *_ , t, __ in res]) if res else ""
                            texts.append(line_text)
                            boxes.append({"x":int(x),"y":int(y),"w":int(w),"h":int(h),"text":line_text,"lineId":str(i)})
                    else:
                        # global run result (no boxes). Fall back to per-line if you want boxes always.
                        texts = [txt_all]

            result["text"] = "\n".join(texts)
            result["boxes"] = boxes

    # ---- LAYOUT / PDF ----
    elif task == "layout":
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data); tmp.flush()
            converter = DocumentConverter()
            doc = converter.convert(tmp.name).document
            md = doc.export_to_markdown(); js = doc.export_to_dict()
            result["text"] = md
            result["layout"] = js
            pipeline.update(segmenter="docling", recognizer="docling")

    # summary + keywords
    if result["text"]:
        result["summary"] = summarize_text(result["text"])
        result["keywords"] = extract_keywords(result["text"])

    result["debug"] = pipeline
    return JSONResponse(result)
import io
from io import BytesIO
import json
import logging
import os
import tempfile
import time
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from PIL import Image

import numpy as np  # type: ignore
import cv2  # type: ignore
import torch  # type: ignore

# Heavy deps are imported lazily inside getters to avoid startup overhead

# Globals for lazy singletons
_paddle_ocr = None
_easyocr_readers: Dict[str, Any] = {}
_trocr_processor = None
_trocr_model = None
_kw_model = None
_yake_extractor = None
_docling_converter = None


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
log = logging.getLogger("ocr")
logger = log

# Optional Gemini import (safe if not installed)
try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None  # type: ignore

# Environment defaults for HF cache (TrOCR) and tessdata
os.environ.setdefault("TRANSFORMERS_CACHE", "./models/hf/cache")
os.environ.setdefault("HF_HOME", "./models/hf/cache")
os.environ.setdefault("TESSDATA_PREFIX", os.getenv("TESSDATA_PREFIX", "./models/tesseract"))

# Path constants for EasyOCR local models (prefer '/model' first)
EASYOCR_DIRS = ["./models/easyocr/model", "./models/easyocr"]

# Safe EasyOCR loader that prefers local cache but can download as last resort
def get_easy_reader(lang_codes):
    import easyocr  # type: ignore
    for p in EASYOCR_DIRS:
        try:
            return easyocr.Reader(
                lang_codes,
                model_storage_directory=p,
                download_enabled=False,
                gpu=False,
            )
        except FileNotFoundError:
            continue
        except Exception:
            # If path exists but partial, try next or fall back to allow download
            continue
    # Last chance: allow download into preferred directory
    return easyocr.Reader(
        lang_codes,
        model_storage_directory=EASYOCR_DIRS[0],
        download_enabled=True,
        gpu=False,
    )

# Single source of truth for languages
SUPPORTED_LANGS: Dict[str, Dict[str, str]] = {
    "en": {"easyocr": "en", "tesseract": "eng", "printed_default": "paddleocr"},
    "hi": {"easyocr": "hi", "tesseract": "hin", "printed_default": "easyocr"},
    "ta": {"easyocr": "ta", "printed_default": "easyocr"},
    "te": {"easyocr": "te", "printed_default": "easyocr"},
    "bn": {"easyocr": "bn", "printed_default": "easyocr"},
    "gu": {"easyocr": "gu", "printed_default": "easyocr"},
    "kn": {"easyocr": "kn", "printed_default": "easyocr"},
    "ml": {"easyocr": "ml", "printed_default": "easyocr"},
}

HANDWRITING_BEST: Dict[str, str] = {
    "en": "trocr",
    "hi": "kraken",
}

# Kraken / Tesseract paths from env
KRAKEN_MODEL_PATH_EN = os.getenv("KRAKEN_MODEL_PATH_EN", "").strip()
KRAKEN_MODEL_PATH_HI = os.getenv("KRAKEN_MODEL_PATH_HI", "").strip()
TESSDATA_PREFIX = os.getenv("TESSDATA_PREFIX", os.environ.get("TESSDATA_PREFIX", "")).strip()

# Gemini cleanup settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
OCR_CLEANING = os.getenv("OCR_CLEANING", "always").strip().lower()

# Additional globals for hardened handwriting branch
_trocr_proc = None
_reader_hi = None


def get_paddle_ocr(lang: str = "en"):
    global _paddle_ocr
    if _paddle_ocr is None:
        logger.info("Initializing PaddleOCR (lang=%s)...", lang)
        from paddleocr import PaddleOCR  # type: ignore

        _paddle_ocr = PaddleOCR(lang="en", use_angle_cls=True, show_log=False)
    return _paddle_ocr


def get_easyocr_reader(lang: str = "en"):
    global _easyocr_readers
    key = lang
    if key not in _easyocr_readers:
        logger.info("Initializing EasyOCR reader (lang=%s)...", lang)
        _easyocr_readers[key] = get_easy_reader([lang])
    return _easyocr_readers[key]


def get_trocr():
    global _trocr_processor, _trocr_model
    if _trocr_processor is None or _trocr_model is None:
        logger.info("Initializing TrOCR (microsoft/trocr-base-handwritten)...")
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore

        _trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
        _trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
        _trocr_model.eval()
    return _trocr_processor, _trocr_model


def get_keyword_models(lang: str = "en"):
    global _kw_model, _yake_extractor
    if _kw_model is None:
        logger.info("Initializing KeyBERT model...")
        from keybert import KeyBERT  # type: ignore

        _kw_model = KeyBERT()
    if _yake_extractor is None:
        logger.info("Initializing YAKE extractor...")
        import yake  # type: ignore

        _yake_extractor = yake.KeywordExtractor(lan=lang, n=1, top=20)
    return _kw_model, _yake_extractor


def get_docling_converter():
    global _docling_converter
    if _docling_converter is None:
        logger.info("Initializing Docling converter...")
        from docling.document_converter import DocumentConverter  # type: ignore

        _docling_converter = DocumentConverter()
    return _docling_converter


def pil_from_bytes(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception as e:
        raise ValueError(f"Unable to open image: {e}")


def ext_from_filename(filename: str) -> str:
    base, ext = os.path.splitext(filename.lower())
    return ext


def is_pdf_upload(upload: UploadFile) -> bool:
    if upload.content_type == "application/pdf":
        return True
    return ext_from_filename(upload.filename or "").endswith(".pdf")


def printed_ocr_with_paddle(image_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    start = time.time()
    ocr = get_paddle_ocr("en")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        result = ocr.ocr(tmp_path, cls=True)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    boxes: List[Dict[str, Any]] = []
    texts: List[str] = []
    for page in result or []:
        for line in page:
            quad = line[0]
            txt = line[1][0]
            xs = [p[0] for p in quad]
            ys = [p[1] for p in quad]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            boxes.append({"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0), "text": txt})
            texts.append(txt)
    logger.info("PaddleOCR: %d boxes in %.2fs", len(boxes), time.time() - start)
    return "\n".join(texts).strip(), boxes


def printed_ocr_with_easyocr(image_bytes: bytes, lang: str = "en") -> Tuple[str, List[Dict[str, Any]]]:
    start = time.time()
    reader = get_easyocr_reader(lang)
    # easyocr can accept numpy arrays; let it handle bytes via cv2
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Unable to decode image for EasyOCR")
    result = reader.readtext(img)
    boxes: List[Dict[str, Any]] = []
    texts: List[str] = []
    for item in result:
        quad, txt, conf = item
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        boxes.append({"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0), "text": str(txt)})
        texts.append(str(txt))
    logger.info("EasyOCR(%s): %d boxes in %.2fs", lang, len(boxes), time.time() - start)
    return "\n".join(texts).strip(), boxes


def printed_ocr_with_tesseract(img: Image.Image, lang: str = "en") -> Tuple[str, List[Dict[str, Any]]]:
    start = time.time()
    try:
        import pytesseract  # type: ignore
        from pytesseract import Output  # type: ignore
    except Exception as e:
        raise RuntimeError(f"pytesseract import failed: {e}")

    lang_code = "eng" if lang == "en" else "hin"
    text = ""
    boxes: List[Dict[str, Any]] = []
    try:
        data = pytesseract.image_to_data(img, lang=lang_code, output_type=Output.DICT)
        n = len(data.get("text", []))
        for i in range(n):
            t = data["text"][i]
            if t and t.strip():
                x = int(data["left"][i])
                y = int(data["top"][i])
                w = int(data["width"][i])
                h = int(data["height"][i])
                boxes.append({"x": x, "y": y, "w": w, "h": h, "text": t})
                text += t + " "
        text = text.strip()
    except pytesseract.pytesseract.TesseractNotFoundError:
        raise RuntimeError("Tesseract not found on PATH. Install Tesseract or choose Paddle/EasyOCR.")
    except Exception as e:
        logger.exception("Tesseract OCR failed: %s", e)
        try:
            text = pytesseract.image_to_string(img, lang=lang_code)
        except Exception:
            pass
    logger.info("Tesseract(%s): %d boxes in %.2fs", lang, len(boxes), time.time() - start)
    return text.strip(), boxes


def _run_kraken_segment(ipath: str, jpath: str):
    """UTF-8 safe Kraken segmentation with quiet logging; avoids Windows console issues."""
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    cmd = ["kraken", "-q", "-i", ipath, jpath, "segment", "-bl"]
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    with open(jpath, "r", encoding="utf-8") as f:
        return json.load(f)


def _opencv_line_boxes(pil_img: Image.Image, pad: int = 32):
    """Simple, language-agnostic line segmentation with OpenCV."""
    gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    k = max(3, gray.shape[1] // 30)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, 3))
    dil = cv2.dilate(thr, kernel, iterations=1)
    cnts, _ = cv2.findContours(dil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = sorted([cv2.boundingRect(c) for c in cnts], key=lambda b: b[1])
    out: List[Dict[str, int]] = []
    for (x, y, w, h) in boxes:
        out.append({"x": max(x - 32, 0), "y": max(y - 32, 0), "w": w + 64, "h": h + 64})
    return out


def handwriting_ocr_kraken_trocr(image_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    start = time.time()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        tmp_img.write(image_bytes)
        img_path = tmp_img.name
    json_path = img_path + ".json"
    try:
        logger.info("Running kraken segmentation...")
        subprocess.run(["kraken", "-i", img_path, json_path, "segment", "-bl"], check=True, capture_output=True)
        with open(json_path, "r", encoding="utf-8") as f:
            seg = json.load(f)
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        lines = seg.get("lines") or seg.get("regions", [])
        boxes: List[Dict[str, Any]] = []
        crops: List[Tuple[Image.Image, str]] = []
        pad = 6
        if isinstance(lines, list) and len(lines) and isinstance(lines[0], dict) and "lines" not in lines[0]:
            iter_lines = lines
        else:
            iter_lines = []
            for r in seg.get("regions", []):
                iter_lines.extend(r.get("lines", []))

        for idx, ln in enumerate(iter_lines):
            lid = ln.get("id") or f"line_{idx}"
            poly = ln.get("boundary") or ln.get("polygon") or ln.get("bbox")
            if poly and isinstance(poly, list) and len(poly) >= 4 and isinstance(poly[0], (list, tuple)):
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                x0, y0, x1, y1 = int(max(0, min(xs) - pad)), int(max(0, min(ys) - pad)), int(min(w, max(xs) + pad)), int(min(h, max(ys) + pad))
            else:
                baseline = ln.get("baseline") or []
                if baseline and isinstance(baseline[0], (list, tuple)):
                    xs = [p[0] for p in baseline]
                    ys = [p[1] for p in baseline]
                    min_x, max_x = min(xs), max(xs)
                    mid_y = sum(ys) / len(ys)
                    height = 30
                    x0, x1 = int(max(0, min_x - pad)), int(min(w, max_x + pad))
                    y0, y1 = int(max(0, mid_y - height // 2)), int(min(h, mid_y + height // 2))
                else:
                    continue
            crop = img.crop((x0, y0, x1, y1))
            crops.append((crop, lid))
            boxes.append({"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0), "lineId": lid})

        proc, model = get_trocr()
        import torch  # type: ignore

        texts: List[str] = []
        texts_by_id: Dict[str, str] = {}
        for crop, lid in crops:
            pixel_values = proc(images=crop, return_tensors="pt").pixel_values
            with torch.no_grad():
                generated_ids = model.generate(pixel_values)
            text = proc.batch_decode(generated_ids, skip_special_tokens=True)[0]
            text = (text or "").strip()
            texts.append(text)
            texts_by_id[lid] = text

        for b in boxes:
            lid = b.get("lineId")
            if lid and lid in texts_by_id:
                b["text"] = texts_by_id[lid]

        logger.info("Kraken+TrOCR: %d lines in %.2fs", len(texts), time.time() - start)
        return "\n".join(texts).strip(), boxes
    except FileNotFoundError:
        raise RuntimeError("kraken CLI not found. Install kraken to use handwriting mode.")
    except subprocess.CalledProcessError as e:
        logger.error("kraken segmentation failed: %s", e.stderr.decode(errors="ignore") if e.stderr else e)
        raise RuntimeError("Kraken segmentation failed.")
    finally:
        for p in (img_path, json_path):
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass


def layout_with_docling(file_bytes: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    start = time.time()
    converter = get_docling_converter()
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1] or ".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        doc = converter.convert(tmp_path)
        document = getattr(doc, "document", doc)
        md = None
        as_dict = None
        if hasattr(document, "export_to_markdown"):
            md = document.export_to_markdown()
        elif hasattr(document, "export_markdown"):
            md = document.export_markdown()
        else:
            md = ""
        if hasattr(document, "export_to_dict"):
            as_dict = document.export_to_dict()
        elif hasattr(document, "to_dict"):
            as_dict = document.to_dict()
        else:
            as_dict = {}
        logger.info("Docling: converted in %.2fs", time.time() - start)
        return str(md or "").strip(), as_dict or {}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def summarize_text(text: str, sentences: int = 3) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    try:
        from sumy.parsers.plaintext import PlaintextParser  # type: ignore
        from sumy.nlp.tokenizers import Tokenizer  # type: ignore
        from sumy.summarizers.text_rank import TextRankSummarizer  # type: ignore

        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = TextRankSummarizer()
        sent_count = min(sentences, len(parser.document.sentences))
        if sent_count <= 0:
            return text
        summary_sents = summarizer(parser.document, sent_count)
        return " ".join([str(s) for s in summary_sents])
    except Exception as e:
        logger.warning("Summarization failed: %s", e)
        return text


def extract_keywords(text: str, lang: str = "en", max_kw: int = 10) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []


# Optional: reduce NLTK warnings (best-effort)
try:
    import nltk  # type: ignore
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
except Exception:
    pass


def _chunk_text(text: str, max_chars: int = 12000) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    size = 0
    for para in re.split(r"\n{2,}", text.strip()):
        if size + len(para) + 2 > max_chars and current:
            parts.append("\n\n".join(current))
            current, size = [para], len(para) + 2
        else:
            current.append(para)
            size += len(para) + 2
    if current:
        parts.append("\n\n".join(current))
    return parts or [""]


def _gemini_status() -> Dict[str, Optional[str]]:
    return {
        "lib_installed": "yes" if genai else "no",
        "has_api_key": "yes" if GEMINI_API_KEY else "no",
        "model": GEMINI_MODEL or None,
        "cleaning_mode": OCR_CLEANING or None,
    }

_GEMINI_READY = bool(genai and GEMINI_API_KEY)

# Log Gemini readiness once at startup (no secrets)
logger.info(
    "Gemini readiness: %s",
    json.dumps(_gemini_status()),
)


def clean_with_gemini(raw_text: str, lang_code: str) -> str:
    """Send OCR text to Gemini for cleanup. Returns cleaned text or the original on any error."""
    if not raw_text or not raw_text.strip():
        logger.info("Gemini cleanup skipped: empty text")
        return raw_text
    if not genai:
        logger.warning("Gemini cleanup skipped: google-generativeai not installed")
        return raw_text
    if not GEMINI_API_KEY:
        logger.warning("Gemini cleanup skipped: GEMINI_API_KEY not set")
        return raw_text
    try:
        genai.configure(api_key=GEMINI_API_KEY)  # type: ignore
        model_name = GEMINI_MODEL or "gemini-2.5-flash"
        model = genai.GenerativeModel(model_name)  # type: ignore
        chunks = _chunk_text(raw_text)
        logger.info("Gemini cleanup: model=%s chunks=%d mode=%s", model_name, len(chunks), OCR_CLEANING)
        cleaned_parts: List[str] = []
        for idx, chunk in enumerate(chunks, 1):
            logger.debug("Gemini cleanup: processing chunk %d/%d (len=%d)", idx, len(chunks), len(chunk))
            prompt = (
                "You are an OCR text corrector.\n"
                "Rules:\n"
                "1) Output only the corrected text (no explanations).\n"
                "2) Keep the same language; do NOT translate.\n"
                "3) Merge broken words/lines; fix spacing and punctuation.\n"
                "4) Remove obvious page noise (headers/footers/page numbers) only if clearly noise.\n"
                "5) Keep paragraphs natural.\n\n"
                f"Language code: {lang_code}\n\n"
                "Input OCR text:\n"
                f"-----\n{chunk}\n-----\n"
                "Return ONLY the corrected text."
            )
            resp = model.generate_content(prompt)  # type: ignore
            cleaned = getattr(resp, "text", "").strip() or chunk
            cleaned_parts.append(cleaned)
        out = "\n\n".join(cleaned_parts).strip() or raw_text
        logger.info("Gemini cleanup done: changed=%s", str(out != raw_text).lower())
        return out
    except Exception as e:
        logger.exception("Gemini cleaning failed")
        return raw_text
    try:
        kw_model, yake_extractor = get_keyword_models(lang)
        try:
            yake_kw = [k for k, _ in yake_extractor.extract_keywords(text)]
        except Exception:
            yake_kw = []
        try:
            kb = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=max_kw)
            kb_kw = [k for k, _ in kb]
        except Exception:
            kb_kw = []
        seen = set()
        merged: List[str] = []
        for k in yake_kw + kb_kw:
            if k and k.lower() not in seen:
                seen.add(k.lower())
                merged.append(k)
            if len(merged) >= max_kw:
                break
        return merged
    except Exception as e:
        logger.warning("Keyword extraction failed: %s", e)
        return []


app = FastAPI(title="TEXTOR OCR API", version="1.0")

# CORS: allow origins from env (comma-separated), defaulting to localhost 8080/5173
origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/v1/ocr")
async def ocr_endpoint(
    file: UploadFile = File(...),
    task: str = Form("printed"),
    lang: str = Form("en"),
    model: Optional[str] = Form(None),
):
    t0 = time.time()
    filename = file.filename or "upload"
    content = await file.read()
    logger.info("/v1/ocr: task=%s lang=%s model=%s filename=%s size=%d", task, lang, model, filename, len(content))

    if is_pdf_upload(file):
        if task != "layout":
            logger.info("PDF upload detected; routing to layout task")
        task = "layout"

    text = ""
    boxes: List[Dict[str, Any]] = []
    layout: Dict[str, Any] = {}

    try:
        meta = SUPPORTED_LANGS.get(lang, SUPPORTED_LANGS["en"])
        engine = None
        requested = None

        if task == "printed":
            engine = (model or meta.get("printed_default", "easyocr")).lower()
            if engine == "paddleocr" and lang == "en":
                try:
                    text, boxes = printed_ocr_with_paddle(content)
                except Exception as e:
                    log.warning("PaddleOCR failed, falling back to EasyOCR: %s", e)
                    text, boxes = printed_ocr_with_easyocr(content, meta.get("easyocr", "en"))
            elif engine == "easyocr":
                text, boxes = printed_ocr_with_easyocr(content, meta.get("easyocr", "en"))
            elif engine == "tesseract":
                try:
                    img = pil_from_bytes(content)
                    # map tesseract code (if not present, fallback to EasyOCR)
                    lang_code = meta.get("tesseract")
                    if not lang_code:
                        raise RuntimeError("No tesseract code for this language")
                    # printed_ocr_with_tesseract expects logical lang 'en'|'hi' for code mapping
                    logical_lang = "en" if lang_code == "eng" else "hi"
                    text, boxes = printed_ocr_with_tesseract(img, logical_lang)
                except Exception as e:
                    log.error("Tesseract error: %s; falling back to EasyOCR", e)
                    text, boxes = printed_ocr_with_easyocr(content, meta.get("easyocr", "en"))
            else:
                text, boxes = printed_ocr_with_easyocr(content, meta.get("easyocr", "en"))

        elif task == "handwriting":
            requested = (model or HANDWRITING_BEST.get(lang, "easyocr")).lower()
            if requested == "calamari":
                requested = "easyocr"

            with tempfile.TemporaryDirectory() as tdir:
                ipath = os.path.join(tdir, "in.png")
                base_img = Image.open(BytesIO(content)).convert("RGB")
                base_img.save(ipath)
                jpath = os.path.join(tdir, "lines.json")

                try:
                    seg = _run_kraken_segment(ipath, jpath)
                    crops: List[Tuple[int,int,int,int,Image.Image]] = []
                    for ln in seg.get("lines", []):
                        if "baseline" in ln and ln["baseline"]:
                            xs = [p[0] for p in ln["baseline"]]; ys = [p[1] for p in ln["baseline"]]
                            pad = 32
                            x = max(min(xs)-pad, 0); y = max(min(ys)-pad, 0)
                            w = (max(xs)-min(xs)) + 2*pad; h = (max(ys)-min(ys)) + 2*pad
                        elif "box" in ln and len(ln["box"]) == 4:
                            x,y,w,h = ln["box"]
                        else:
                            continue
                        crop = base_img.crop((x,y,x+w,y+h)).convert("RGB")
                        crops.append((int(x),int(y),int(w),int(h),crop))
                except Exception as e:
                    log.error("Kraken segmentation failed: %s; falling back to OpenCV", e)
                    bxs = _opencv_line_boxes(base_img)
                    crops = [(b["x"],b["y"],b["w"],b["h"], base_img.crop((b["x"],b["y"],b["x"]+b["w"],b["y"]+b["h"])) .convert("RGB")) for b in bxs]

                texts = []
                boxes = []

                if requested == "kraken" and lang == "hi" and KRAKEN_MODEL_PATH_HI and os.path.exists(KRAKEN_MODEL_PATH_HI):
                    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
                    for i,(x,y,w,h,crop) in enumerate(crops):
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as limg, \
                             tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as ltxt:
                            crop.save(limg.name)
                            subprocess.run(["kraken","-q","ocr","-i", limg.name, ltxt.name, "-m", KRAKEN_MODEL_PATH_HI],
                                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                            line_text = open(ltxt.name, "r", encoding="utf-8").read().strip()
                        texts.append(line_text)
                        boxes.append({"x":x,"y":y,"w":w,"h":h,"text":line_text,"lineId":str(i)})
                elif requested == "trocr" and lang == "en":
                    from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore
                    global _trocr_processor, _trocr_model
                    if _trocr_processor is None or _trocr_model is None:
                        _trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
                        _trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
                    for i,(x,y,w,h,crop) in enumerate(crops):
                        g = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2GRAY)
                        g = cv2.fastNlMeansDenoising(g, h=15)
                        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                        g = clahe.apply(g)
                        g = cv2.resize(g, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
                        crop2 = Image.fromarray(cv2.cvtColor(g, cv2.COLOR_GRAY2RGB))
                        pixel_values = _trocr_processor(images=crop2, return_tensors="pt").pixel_values
                        with torch.no_grad():
                            ids = _trocr_model.generate(pixel_values, max_length=160, num_beams=5, early_stopping=True, length_penalty=0.1)
                        line_text = _trocr_processor.batch_decode(ids, skip_special_tokens=True)[0]
                        texts.append(line_text)
                        boxes.append({"x":x,"y":y,"w":w,"h":h,"text":line_text,"lineId":str(i)})
                else:
                    code = meta.get("easyocr", "en")
                    reader = get_easy_reader([code])
                    for i,(x,y,w,h,crop) in enumerate(crops):
                        res = reader.readtext(np.array(crop))
                        line_text = " ".join([t for *_ , t, __ in res]) if res else ""
                        texts.append(line_text)
                        boxes.append({"x":x,"y":y,"w":w,"h":h,"text":line_text,"lineId":str(i)})

                text = "\n".join(texts)

        elif task == "layout":
            try:
                text, layout = layout_with_docling(content, filename)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Layout conversion failed: {e}")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported task: {task}")

        # Optionally clean OCR text via Gemini before generating summary/keywords
        raw_text = text or ""
        should_clean = (OCR_CLEANING == "always") or (OCR_CLEANING == "on_error" and bool(raw_text))
        if should_clean and raw_text:
            cleaned = clean_with_gemini(raw_text, lang)
            if cleaned != raw_text:
                # Keep raw for optional UI toggle
                if 'debug' not in locals():
                    pass
                text = cleaned
                # debug fields added below
            # else keep original

        summary = summarize_text(text) if text else ""
        keywords = extract_keywords(text, lang=lang)

        elapsed = time.time() - t0
        logger.info("/v1/ocr completed in %.2fs, boxes=%d, text_len=%d", elapsed, len(boxes or []), len(text or ""))

        debug = {
            "task": task,
            "lang": lang,
            "printed_default": SUPPORTED_LANGS.get(lang, SUPPORTED_LANGS["en"]).get("printed_default"),
            "recognizer": requested if task == "handwriting" else engine,
            "kraken_hi_model": bool(KRAKEN_MODEL_PATH_HI and os.path.exists(KRAKEN_MODEL_PATH_HI)),
            "easyocr_search": EASYOCR_DIRS,
        }

        # Enrich debug with cleaning info and include raw text if changed
        if should_clean and raw_text:
            debug["cleaned_by"] = "gemini" if _GEMINI_READY else "none"
            debug["gemini_model"] = GEMINI_MODEL if _GEMINI_READY else None

        changed = bool(should_clean and raw_text and text != raw_text)

        return {
            "text": text or "",
            "boxes": boxes or [],
            "layout": layout or {},
            "summary": summary or "",
            "keywords": keywords or [],
            "debug": debug,
            **({"raw_text": raw_text} if changed else {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/")
def root():
    return {"status": "ok", "service": "TEXTOR OCR API"}


@app.get("/v1/capabilities")
def capabilities():
    return {
        "supported_languages": list(SUPPORTED_LANGS.keys()),
        "handwriting_best": HANDWRITING_BEST,
        "env_paths_detected": {
            "kraken_hi_model_exists": bool(KRAKEN_MODEL_PATH_HI and os.path.exists(KRAKEN_MODEL_PATH_HI)),
            "tessdata_prefix": TESSDATA_PREFIX or None,
        },
    }


@app.get("/v1/gemini/status")
def gemini_status():
    """Expose Gemini readiness without secrets for debugging."""
    st = _gemini_status()
    st["ready"] = _GEMINI_READY
    return st
