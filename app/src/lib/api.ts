export async function postOcr(form: FormData) {
  const base = import.meta.env.VITE_API_URL;
  const res = await fetch(`${base}/v1/ocr`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`OCR failed: ${res.status}`);
  return res.json();
}
