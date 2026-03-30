export type Lang = 'en'|'hi'|'ta'|'te'|'bn'|'gu'|'kn'|'ml';

export const LANGUAGES: { code: Lang; label: string; handwriting: 'best'|'fallback'|'none'; }[] = [
  { code: 'en', label: 'English', handwriting: 'best' },
  { code: 'hi', label: 'Hindi (Devanagari)', handwriting: 'best' },
  { code: 'ta', label: 'Tamil', handwriting: 'fallback' },
  { code: 'te', label: 'Telugu', handwriting: 'fallback' },
  { code: 'bn', label: 'Bengali', handwriting: 'fallback' },
  { code: 'gu', label: 'Gujarati', handwriting: 'fallback' },
  { code: 'kn', label: 'Kannada', handwriting: 'fallback' },
  { code: 'ml', label: 'Malayalam', handwriting: 'fallback' },
];

