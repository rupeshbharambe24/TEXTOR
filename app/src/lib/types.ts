export type OcrTask = 'printed' | 'handwriting' | 'layout';
export type ModelKey =
  | 'paddleocr' | 'easyocr' | 'tesseract'
  | 'trocr' | 'kraken' | 'calamari'
  | 'docling';

export interface OcrBox {
  x: number;
  y: number;
  w: number;
  h: number;
  text?: string;
  lineId?: string;
}

export interface OcrJobResult {
  text: string;
  boxes?: OcrBox[];
  layout?: any;
  summary?: string;
  keywords?: string[];
  debug?: { task?: string; lang?: string; printed_default?: string; recognizer?: string; kraken_hi_model?: boolean };
  raw_text?: string;
}
