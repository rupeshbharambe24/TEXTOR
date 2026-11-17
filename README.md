<p align="center">
  <img src="https://img.shields.io/badge/TEXTOR-Document%20AI%20%26%20OCR-purple?style=for-the-badge&logo=files&logoColor=white" alt="TEXTOR" />
</p>

<h1 align="center">TEXTOR</h1>
<p align="center">
  <strong>Multi-Engine OCR, Document Parsing, and NLP Analysis Platform</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/PaddleOCR-0062B8?style=flat-square" />
  <img src="https://img.shields.io/badge/TrOCR-Handwriting-EE4C2C?style=flat-square" />
  <img src="https://img.shields.io/badge/Gemini-AI%20Correction-4285F4?style=flat-square&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" />
</p>

---

## Overview

TEXTOR is a document intelligence platform that extracts, analyzes, and summarizes text from images, PDFs, and handwritten documents. It combines multiple OCR engines with NLP pipelines to handle printed text, handwriting, and complex document layouts.

## Features

### Multi-Engine OCR
- **PaddleOCR** — Primary engine for printed text (multilingual)
- **EasyOCR** — Secondary engine with broad language support
- **Tesseract** — Fallback engine (English + Hindi)
- Automatic engine selection based on document type

### Handwriting Recognition
- **Kraken** — Page segmentation and baseline detection
- **TrOCR** (Microsoft) — Transformer-based handwriting recognition
- Specialized for doctor prescriptions and handwritten notes

### Document Parsing
- **Docling** — PDF/document layout analysis
- Outputs structured Markdown and JSON
- Handles multi-column layouts, tables, and figures

### NLP Analysis
- **Sumy TextRank** — Extractive text summarization
- **KeyBERT + YAKE** — Keyword extraction (hybrid approach)
- **Gemini AI** — Intelligent text correction and analysis

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| **Backend API** | FastAPI, Uvicorn, Python |
| **OCR Engines** | PaddleOCR, EasyOCR, Tesseract |
| **Handwriting** | Kraken, TrOCR (HuggingFace Transformers) |
| **Document AI** | Docling (PDF parsing) |
| **NLP** | Sumy, KeyBERT, YAKE |
| **AI** | Google Gemini (text correction) |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |

## Project Structure

```
TEXTOR/
├── api/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py         # API routes and endpoints
│   │   └── settings.py     # Configuration
│   ├── scripts/
│   │   └── fetch_models.py # Download model weights
│   ├── .env.example        # Gemini / Kraken / Tesseract / CORS settings
│   └── requirements.txt
├── app/                    # React frontend
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── pages/          # Route pages
│   │   ├── hooks/          # Custom hooks
│   │   └── lib/            # API client, model/language options
│   ├── .env.example        # VITE_API_URL
│   └── package.json
└── notebooks/              # Research & experiments
    ├── trocr.ipynb         # TrOCR handwriting recognition
    ├── TROCRN.ipynb        # TrOCR experiments (variant)
    ├── Donut.ipynb         # Donut (OCR-free document understanding) experiments
    └── doctors-handwritten-prescription.ipynb
```

## Getting Started

### Backend
```bash
cd api
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env         # optional: GEMINI_API_KEY, model paths, CORS
python scripts/fetch_models.py   # optional: pre-download TrOCR/EasyOCR/Tesseract data into models/
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd app
npm install
cp .env.example .env         # optional: defaults to http://localhost:8000
npm run dev
```

API docs at `http://localhost:8000/docs`. Frontend at `http://localhost:8080`.

## License

Released under the [MIT License](LICENSE).
