import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import ModelSelector from '@/components/ocr/ModelSelector';
import PreviewOverlay from '@/components/ocr/PreviewOverlay';
import { useOcrJob } from '@/hooks/useOcrJob';
import type { ModelKey, OcrJobResult, OcrTask } from '@/lib/types';
import type { Lang } from '@/lib/languages';

export default function OcrPage() {
  const { toast } = useToast();
  const [task, setTask] = React.useState<OcrTask>('printed');
  const [lang, setLang] = React.useState<Lang>('en');
  const [model, setModel] = React.useState<ModelKey | undefined>('paddleocr');
  const [file, setFile] = React.useState<File | null>(null);
  const [imageUrl, setImageUrl] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<OcrJobResult | null>(null);
  const [showRaw, setShowRaw] = React.useState(false);

  const mutation = useOcrJob();

  const onSelectorChange = (v: { task: OcrTask; lang: Lang; model?: ModelKey }) => {
    setTask(v.task);
    setLang(v.lang);
    setModel(v.model);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    setResult(null);
    if (f) {
      if (f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')) {
        setImageUrl(null);
      } else {
        const url = URL.createObjectURL(f);
        setImageUrl(url);
      }
    } else {
      setImageUrl(null);
    }
  };

  const handleRun = async () => {
    if (!file) {
      toast({ title: 'No file selected', description: 'Please choose an image or PDF file.' });
      return;
    }
    const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    let taskToSend: OcrTask = task;
    let modelToSend = model;
    if (isPdf && task !== 'layout') {
      taskToSend = 'layout';
      modelToSend = 'docling';
      setTask('layout');
      setModel('docling');
      toast({ title: 'Switched to Document Layout', description: 'PDF works best with Document Layout.' });
    }
    const form = new FormData();
    form.append('file', file);
    form.append('task', taskToSend);
    form.append('lang', lang);
    if (modelToSend) form.append('model', modelToSend);

    setResult(null);
    mutation.mutate(form, {
      onSuccess: (data: OcrJobResult) => {
        setResult(data);
      },
      onError: (err: any) => {
        const msg = err?.message || 'Something went wrong';
        toast({ title: 'OCR failed', description: msg });
      },
    });
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ocr_result.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <h1 className="text-3xl font-bold">OCR Playground</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <ModelSelector task={task} lang={lang} model={model} onChange={onSelectorChange} />
          <Card>
            <CardHeader>
              <CardTitle>Upload</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input type="file" accept="image/*,.pdf" onChange={onFileChange} />
              <Button onClick={handleRun} disabled={mutation.isPending}>
                {mutation.isPending ? 'Processing…' : 'Run'}
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2 space-y-4">
          {imageUrl && result?.boxes && (
            <Card>
              <CardHeader>
                <CardTitle>Preview</CardTitle>
              </CardHeader>
              <CardContent>
                <PreviewOverlay imageUrl={imageUrl} boxes={result.boxes?.map(b => ({ x: b.x, y: b.y, w: b.w, h: b.h }))} />
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Text</CardTitle>
              </CardHeader>
              <CardContent>
                {result?.raw_text && (
                  <label className="inline-flex items-center gap-2 text-sm mb-2">
                    <input type="checkbox" checked={showRaw} onChange={(e)=>setShowRaw(e.target.checked)} />
                    Show raw OCR instead of corrected
                  </label>
                )}
                <pre className="whitespace-pre-wrap text-sm">
                  {showRaw && result?.raw_text ? result.raw_text : (result?.text || '')}
                </pre>
              </CardContent>
            </Card>
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed">{result?.summary || ''}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Keywords</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{result?.keywords?.join(', ') || ''}</p>
                </CardContent>
              </Card>
              {result?.debug && (
                <Card>
                  <CardHeader>
                    <CardTitle>Debug</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs text-muted-foreground">{JSON.stringify(result.debug, null, 2)}</pre>
                  </CardContent>
                </Card>
              )}
              <Button variant="secondary" onClick={handleDownload} disabled={!result}>Download JSON</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
