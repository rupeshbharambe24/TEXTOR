import type { OcrTask, ModelKey } from '@/lib/types';
import type { Lang } from '@/lib/languages';

export function modelsFor(task: OcrTask, lang: Lang): ModelKey[] {
  if (task === 'printed') {
    return lang === 'en' ? ['paddleocr','easyocr','tesseract'] : ['easyocr','tesseract'];
  }
  if (task === 'handwriting') {
    return lang === 'en' ? ['trocr','kraken','easyocr']
         : lang === 'hi' ? ['kraken','trocr','easyocr']
         : ['easyocr'];
  }
  if (task === 'layout') return ['docling'];
  return ['easyocr'];
}

export function defaultModel(task: OcrTask, lang: Lang): ModelKey {
  if (task === 'printed') return lang === 'en' ? 'paddleocr' : 'easyocr';
  if (task === 'handwriting') return lang === 'en' ? 'trocr' : (lang === 'hi' ? 'kraken' : 'easyocr');
  if (task === 'layout') return 'docling';
  return 'easyocr';
}

