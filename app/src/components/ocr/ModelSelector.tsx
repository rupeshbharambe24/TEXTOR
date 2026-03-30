import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import * as React from 'react';
import type { ModelKey, OcrTask } from '@/lib/types';
import { LANGUAGES, type Lang } from '@/lib/languages';
import { modelsFor, defaultModel } from '@/lib/modelOptions';

export interface ModelSelectorProps {
  task: OcrTask;
  lang: Lang;
  model?: ModelKey;
  onChange: (v: { task: OcrTask; lang: Lang; model?: ModelKey }) => void;
}

const modelOptionsFor = (task: OcrTask, lang: Lang): ModelKey[] => modelsFor(task, lang);

const taskOptions: { label: string; value: OcrTask }[] = [
  { label: 'Printed OCR', value: 'printed' },
  { label: 'Handwriting (lines)', value: 'handwriting' },
  { label: 'Document Layout', value: 'layout' },
];

const langOptions: { label: string; value: Lang }[] = LANGUAGES.map(l => ({ label: l.label, value: l.code }));

export default function ModelSelector({ task, lang, model, onChange }: ModelSelectorProps) {
  const options = React.useMemo(() => modelOptionsFor(task, lang), [task, lang]);
  const currentModel: ModelKey = model && options.includes(model) ? model : defaultModel(task, lang);

  const setTask = (v: OcrTask) => {
    const m = defaultModel(v, lang);
    onChange({ task: v, lang, model: m });
  };
  const setLang = (v: Lang) => {
    const m = defaultModel(task, v);
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
          {task === 'handwriting' && LANGUAGES.find(l => l.code === lang)?.handwriting === 'fallback' && (
            <p className="text-xs text-muted-foreground mt-1">Handwriting uses a fallback recognizer for this script.</p>
          )}
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
