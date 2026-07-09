'use client';

import React from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip,
} from 'recharts';

const DIMENSION_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
];

const FRAMEWORK_DIMS: Record<string, { label: string; color: string }[]> = {
  big_five: [
    { label: 'Openness', color: '#3B82F6' },
    { label: 'Conscientiousness', color: '#10B981' },
    { label: 'Extraversion', color: '#F59E0B' },
    { label: 'Agreeableness', color: '#8B5CF6' },
    { label: 'Neuroticism', color: '#EF4444' },
  ],
  communication_style: [
    { label: 'Directness', color: '#3B82F6' },
    { label: 'Expressiveness', color: '#10B981' },
    { label: 'Responsiveness', color: '#F59E0B' },
    { label: 'Formality', color: '#8B5CF6' },
    { label: 'Conflict Style', color: '#EC4899' },
  ],
  emotional_intelligence: [
    { label: 'Self-awareness', color: '#3B82F6' },
    { label: 'Self-regulation', color: '#10B981' },
    { label: 'Motivation', color: '#F59E0B' },
    { label: 'Empathy', color: '#EC4899' },
    { label: 'Social Skills', color: '#8B5CF6' },
  ],
  attachment: [
    { label: 'Secure', color: '#10B981' },
    { label: 'Anxious', color: '#F59E0B' },
    { label: 'Avoidant', color: '#EF4444' },
    { label: 'Disorganized', color: '#8B5CF6' },
  ],
};

interface Props {
  scores: Record<string, number>;
  frameworkId: string;
  classification?: string | null;
}

export default function ScoreChart({ scores, frameworkId, classification }: Props) {
  const dims = FRAMEWORK_DIMS[frameworkId];
  if (!dims || !scores || Object.keys(scores).length === 0) return null;

  const labelToKey = (label: string): string =>
    label.toLowerCase().replace(/[\s-]/g, '_');

  const data = dims.map((d) => ({
    name: d.label,
    value: scores[labelToKey(d.label)] ?? 5,
    fullMark: 10,
  }));

  const isRadar = frameworkId === 'big_five';

  return (
    <div className="flex flex-col items-center w-full mb-4" style={{ background: 'var(--bg-surface)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
      {classification && (
        <div className="flex items-center gap-2 px-4 pt-3 pb-1 self-start">
          <span className="text-[10px] uppercase text-[var(--text-muted)] font-bold">Classification:</span>
          <span
            className="px-2 py-0.5 rounded text-[10px] font-bold"
            style={{
              background:
                classification === 'Secure' ? 'rgba(16, 185, 129, 0.15)' :
                classification === 'Anxious' ? 'rgba(245, 158, 11, 0.15)' :
                classification === 'Avoidant' ? 'rgba(239, 68, 68, 0.15)' :
                'rgba(139, 92, 246, 0.15)',
              color:
                classification === 'Secure' ? '#10B981' :
                classification === 'Anxious' ? '#F59E0B' :
                classification === 'Avoidant' ? '#EF4444' :
                '#8B5CF6',
            }}
          >
            {classification}
          </span>
        </div>
      )}

      <div className="w-full" style={{ height: isRadar ? 200 : 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          {isRadar ? (
            <RadarChart data={data} margin={{ top: 20, right: 30, bottom: 5, left: 30 }}>
              <PolarGrid stroke="var(--border-subtle)" />
              <PolarAngleAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} />
              <PolarRadiusAxis angle={90} domain={[0, 10]} tick={false} axisLine={false} />
              <Radar
                name="Score"
                dataKey="value"
                stroke="#3B82F6"
                fill="#3B82F6"
                fillOpacity={0.2}
                strokeWidth={2}
              />
            </RadarChart>
          ) : (
            <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 80 }}>
              <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 9, fill: 'var(--text-muted)' }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-secondary)', width: 70 }} width={70} />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-surface-raised)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  fontSize: '10px',
                  color: 'var(--text-primary)',
                }}
              />
              <Bar dataKey="value" fill="#3B82F6" radius={[0, 3, 3, 0]} barSize={16} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
