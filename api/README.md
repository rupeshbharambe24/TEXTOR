# TEXTOR OCR API (FastAPI)

A lightweight OCR and document layout service providing multiple free OSS models and utilities. Designed to work with the Vite + React frontend.

- REST: FastAPI (`/v1/ocr`)
- OCR models: PaddleOCR, EasyOCR, Tesseract (fallback)
- Handwriting: Kraken (segmentation, `segment -bl`) + TrOCR recognition
- PDFs/Layout: Docling (Markdown + JSON)
- NLP: Sumy TextRank (summary), KeyBERT + YAKE (keywords)

## Quickstart

1) Create a Python env (recommended)

```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
```

2) Install dependencies

```
pip install -r requirements.txt
```

3) Run the server

```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
  
CORS is enabled for `http://localhost:5173` (Vite default).

## Windows notes (Tesseract)

- Tesseract is optional. PaddleOCR/EasyOCR work without it.
- If you want to use Tesseract for English/Hindi fallback:
  - Install Tesseract for Windows: https://github.com/UB-Mannheim/tesseract/wiki
  - Ensure `tesseract.exe` is on your PATH (reopen shell after install).
  - Hindi data file `hin.traineddata` (if not included) goes under your Tesseract `tessdata` directory. Typical paths:
    - `C:\\Program Files\\Tesseract-OCR\\tessdata\\hin.traineddata`

If Tesseract is missing, the backend gracefully skips it and uses PaddleOCR/EasyOCR.

## Model downloads

On first run, models are downloaded automatically:
- PaddleOCR/EasyOCR: detection/recognition weights
- TrOCR: `microsoft/trocr-base-handwritten`
- Kraken: installed via pip; `kraken` CLI should be available on PATH
- Docling: loads components on first use

## Endpoint

POST `/v1/ocr` (multipart/form-data)
- `file`: image or PDF
- `task`: `printed` | `handwriting` | `layout`
- `lang`: `en` | `hi`
- `model` (optional): `paddleocr` | `easyocr` | `tesseract` | `trocr` | `kraken` | `calamari` | `pp-structure` | `docling`

Response JSON:
```
{
  "text": "string",
  "boxes": [ { "x": 0, "y": 0, "w": 0, "h": 0, "text": "optional", "lineId": "optional" } ],
  "layout": { },
  "summary": "string",
  "keywords": ["array","of","strings"]
}
```

Notes:
- If a PDF is uploaded with `task=printed`/`handwriting`, the server automatically switches to `layout` and uses Docling.
- Kraken segmentation output and JSON schemas vary; the code handles common patterns by creating padded rectangles for each line.
- Summarization and keywords are computed only if `text` is non-empty.

## Dev tips

- Logs include which branch/model was chosen, timings, and counts of boxes/lines.
- Heavy models are kept as singletons to avoid re-download and speed up multiple requests.
- If the `kraken` CLI is not found, handwriting mode returns an informative error.

