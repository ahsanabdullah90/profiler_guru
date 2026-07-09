'use client';

import React, { useState } from 'react';
import { apiFetch } from '../store/api';
import { ClipboardCheck, Loader2, AlertTriangle, CheckCircle } from 'lucide-react';

const INSTRUMENTS: Record<string, { label: string; description: string }> = {
  phq9: {
    label: 'PHQ-9 Depression Screening',
    description: '9 items, 0-27 scale. Assesses depression severity over the past 2 weeks.',
  },
  gad7: {
    label: 'GAD-7 Anxiety Screening',
    description: '7 items, 0-21 scale. Assesses generalized anxiety severity over the past 2 weeks.',
  },
  bhs: {
    label: 'Beck Hopelessness Scale',
    description: '20 yes/no items, 0-20 scale. Assesses hopelessness severity.',
  },
};

const BAND_COLORS: Record<string, string> = {
  Minimal: '#10B981',
  Mild: '#F59E0B',
  Moderate: '#F97316',
  'Moderately Severe': '#EF4444',
  Severe: '#DC2626',
  Normal: '#10B981',
};

interface Props {
  contactName: string;
}

export default function QuestionnaireRunner({ contactName }: Props) {
  const [selectedInstrument, setSelectedInstrument] = useState<string>('phq9');
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ total: number; band: string; item_count: number; max_score: number; responses: Record<string, number> } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // We need to fetch the instrument questions from the backend.
  // Since they're not exposed via API, we'll use a cached fetch.
  // Actually — the items are in the framework definitions on the backend.
  // Let me fetch them via a lightweight endpoint or hardcode them.
  // For now, let's use the backend's frameworks endpoint to get items.
  // But there's no frameworks endpoint yet. Let me just fetch from the assessment endpoint.

  // Actually, the simplest approach: the items are known constants.
  // I'll define them inline for the 3 instruments.
  // This mirrors the backend definitions exactly.

  const INSTRUMENT_ITEMS: Record<string, { id: string; prompt: string; responses: { value: number; label: string }[]; reverse?: boolean }[]> = {
    phq9: [
      { id: 'q1', prompt: 'Little interest or pleasure in doing things', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q2', prompt: 'Feeling down, depressed, or hopeless', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q3', prompt: 'Trouble falling or staying asleep, or sleeping too much', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q4', prompt: 'Feeling tired or having little energy', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q5', prompt: 'Poor appetite or overeating', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q6', prompt: 'Feeling bad about yourself — or that you are a failure or have let yourself or your family down', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q7', prompt: 'Trouble concentrating on things, such as reading the newspaper or watching television', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q8', prompt: 'Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q9', prompt: 'Thoughts that you would be better off dead, or of hurting yourself', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'More than half the days' }, { value: 3, label: 'Nearly every day' }] },
    ],
    gad7: [
      { id: 'q1', prompt: 'Feeling nervous, anxious, or on edge', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'Over half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q2', prompt: 'Not being able to stop or control worrying', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'Over half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q3', prompt: 'Worrying too much about different things', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'Over half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q4', prompt: 'Trouble relaxing', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'Over half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q5', prompt: 'Being so restless that it is hard to sit still', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'Over half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q6', prompt: 'Becoming easily annoyed or irritable', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'Over half the days' }, { value: 3, label: 'Nearly every day' }] },
      { id: 'q7', prompt: 'Feeling afraid, as if something awful might happen', responses: [{ value: 0, label: 'Not at all' }, { value: 1, label: 'Several days' }, { value: 2, label: 'Over half the days' }, { value: 3, label: 'Nearly every day' }] },
    ],
    bhs: [
      { id: 'q1', prompt: 'I look forward to the future with hope and enthusiasm.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q2', prompt: 'I might as well give up because I cannot make things better for myself.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q3', prompt: 'When things are going badly, I am helped by knowing they cannot stay that way forever.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q4', prompt: 'I cannot imagine what my life would be like in 10 years.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q5', prompt: 'I have enough time to accomplish the things I want to do.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q6', prompt: 'In the future, I expect to succeed in what concerns me most.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q7', prompt: 'My future seems dark to me.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q8', prompt: 'I happen to be particularly lucky, and I expect to get more of the good things in life than the average person.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q9', prompt: 'I just cannot get the breaks, and there is no reason I will in the future.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q10', prompt: 'My past experiences have prepared me well for the future.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q11', prompt: 'All I can see ahead of me is unpleasantness rather than pleasantness.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q12', prompt: 'I do not expect to get what I really want.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q13', prompt: 'When I look ahead to the future, I expect I will be happier than I am now.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q14', prompt: 'Things just do not work out the way I want them to.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q15', prompt: 'I have great faith in the future.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q16', prompt: 'I never get what I want, so it is foolish to want anything.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q17', prompt: 'It is very unlikely that I will get any real satisfaction in the future.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q18', prompt: 'The future seems vague and uncertain to me.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
      { id: 'q19', prompt: 'I can look forward to more good times than bad times.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }] },
      { id: 'q20', prompt: 'There is no use in really trying to get something I want because I probably will not get it.', responses: [{ value: 0, label: 'False' }, { value: 1, label: 'True' }], reverse: true },
    ],
  };

  const items = INSTRUMENT_ITEMS[selectedInstrument] || [];
  const allAnswered = items.length > 0 && items.every((item) => responses[item.id] !== undefined);

  const handleSubmit = async () => {
    if (!allAnswered) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const data = await apiFetch<{ status: string; result: { total: number; band: string; item_count: number; max_score: number; responses: Record<string, number> } }>(
        `/clinical/${contactName}/assessments`,
        {
          method: 'POST',
          body: JSON.stringify({
            framework_id: selectedInstrument,
            responses,
          }),
        },
      );
      setResult(data.result);
    } catch (err) {
      const e = err as Error;
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setResponses({});
    setResult(null);
    setError(null);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Instrument selector */}
      <div className="flex gap-1.5 flex-wrap">
        {Object.entries(INSTRUMENTS).map(([id, inst]) => (
          <button
            key={id}
            type="button"
            onClick={() => { setSelectedInstrument(id); setResponses({}); setResult(null); setError(null); }}
            className="px-2.5 py-1 rounded-lg text-[10px] font-bold cursor-pointer transition-all"
            style={{
              background: selectedInstrument === id ? 'var(--brand-primary)' : 'var(--bg-surface-raised)',
              border: `1px solid ${selectedInstrument === id ? 'var(--brand-primary)' : 'var(--border-subtle)'}`,
              color: selectedInstrument === id ? '#fff' : 'var(--text-secondary)',
            }}
          >
            {inst.label}
          </button>
        ))}
      </div>

      {selectedInstrument && INSTRUMENTS[selectedInstrument] ? (
        <p className="text-[9px] text-[var(--text-muted)] italic">{INSTRUMENTS[selectedInstrument].description}</p>
      ) : null}

      {/* Questions */}
      {result ? (
        /* Score result */
        <div className="p-4 rounded-lg flex flex-col items-center gap-2" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
          <CheckCircle className="w-6 h-6" style={{ color: BAND_COLORS[result.band] || '#10B981' }} />
          <span className="text-2xl font-bold" style={{ color: BAND_COLORS[result.band] || 'var(--text-primary)' }}>
            {result.total} / {result.max_score}
          </span>
          <span
            className="px-2 py-0.5 rounded text-[11px] font-bold"
            style={{
              background: `${BAND_COLORS[result.band] || '#10B981'}20`,
              color: BAND_COLORS[result.band] || 'var(--text-primary)',
            }}
          >
            {result.band}
          </span>
          <button
            type="button"
            onClick={handleReset}
            className="mt-2 px-3 py-1 rounded-lg text-[10px] font-bold cursor-pointer"
            style={{ background: 'var(--bg-surface-raised)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}
          >
            Run Again
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-2 max-h-80 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
            {items.map((item) => (
              <div key={item.id} className="p-2.5 rounded-lg" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                <p className="text-[11px] text-[var(--text-primary)] mb-1.5 leading-relaxed">{item.prompt}</p>
                <div className="flex gap-1 flex-wrap">
                  {item.responses.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setResponses((prev) => ({ ...prev, [item.id]: opt.value }))}
                      className="px-2 py-0.5 rounded text-[9px] font-medium cursor-pointer transition-all"
                      style={{
                        background: responses[item.id] === opt.value ? 'var(--brand-primary)' : 'var(--bg-surface-inset)',
                        border: `1px solid ${responses[item.id] === opt.value ? 'var(--brand-primary)' : 'var(--border-subtle)'}`,
                        color: responses[item.id] === opt.value ? '#fff' : 'var(--text-secondary)',
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {error ? (
            <div className="flex items-center gap-2 p-2 rounded-lg text-[10px]" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#EF4444' }}>
              <AlertTriangle className="w-3 h-3 shrink-0" />
              {error}
            </div>
          ) : null}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!allAnswered || submitting}
            className="w-full py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-2 cursor-pointer text-white disabled:opacity-40 transition-all"
            style={{ background: 'var(--brand-primary)' }}
          >
            {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ClipboardCheck className="w-3.5 h-3.5" />}
            {submitting ? 'Scoring...' : `Score ${INSTRUMENTS[selectedInstrument]?.label || ''}`}
          </button>
        </>
      )}
    </div>
  );
}
