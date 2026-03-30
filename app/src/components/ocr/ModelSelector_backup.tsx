import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import * as React from 'react';
import type { Lang, ModelKey, OcrTask } from '@/lib/types';

export interface ModelSelectorProps {
  task: OcrTask;
  lang: Lang;
  model?: ModelKey;
  onChange: (v: { task: OcrTask; lang: Lang; model?: ModelKey }) => void;
}

const defaultModelFor = (task: OcrTask, lang: Lang): ModelKey => {
  if (task === 'printed') return lang === 'hi' ? 'easyocr' : 'paddleocr';
  if (task === 'handwriting') return 'kraken';
  return 'docling';
};

const modelOptionsFor = (task: OcrTask, lang: Lang): ModelKey[] => {
  if (task === 'printed' && lang === 'en') return ['paddleocr', 'easyocr', 'tesseract'];
  if (task === 'printed' && lang === 'hi') return ['easyocr', 'tesseract'];
  if (task === 'handwriting') return ['kraken', 'trocr', 'calamari'];
  return ['docling'];
};

const taskOptions: { label: string; value: OcrTask }[] = [
  { label: 'Printed OCR', value: 'printed' },
  { label: 'Handwriting (lines)', value: 'handwriting' },
  { label: 'Document Layout', value: 'layout' },
];

const langOptions: { label: string; value: Lang }[] = [
  { label: 'English (en)', value: 'en' },
  { label: 'Hindi (hi)', value: 'hi' },
];

export default function ModelSelector({ task, lang, model, onChange }: ModelSelectorProps) {
  const options = React.useMemo(() => modelOptionsFor(task, lang), [task, lang]);
  const currentModel: ModelKey = model && options.includes(model) ? model : defaultModelFor(task, lang);

  const setTask = (v: OcrTask) => {
    const opts = modelOptionsFor(v, lang);
    const m = opts.includes(currentModel) ? currentModel : defaultModelFor(v, lang);
    onChange({ task: v, lang, model: m });
  };
  const setLang = (v: Lang) => {
    const opts = modelOptionsFor(task, v);
    const m = opts.includes(currentModel) ? currentModel : defaultModelFor(task, v);
    onChange({ task, lang: v, model: m });
  };
  const setModel = (v: ModelKey) => onChange({ task, lang, model: v });

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Options</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Task</Label>
          <Select value={task} onValueChange={(v) => setTask(v as OcrTask)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select task" />
            </SelectTrigger>
            <SelectContent>
              {taskOptions.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Language</Label>
          <Select value={lang} onValueChange={(v) => setLang(v as Lang)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select language" />
            </SelectTrigger>
            <SelectContent>
              {langOptions.map((l) => (
                <SelectItem key={l.value} value={l.value}>
                  {l.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Model</Label>
          <Select value={currentModel} onValueChange={(v) => setModel(v as ModelKey)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {options.map((m) => (
                <SelectItem key={m} value={m}>
                  {m}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
