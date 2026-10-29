import React from 'react';
import { Loader2, Check, Clock } from 'lucide-react';
import type { DocumentStatusResponse } from '../types';

interface ProcessingStateProps {
  status: DocumentStatusResponse | null;
  filename: string;
}

const PIPELINE_STEPS = [
  { key: 'PREPROCESSING', label: 'Image Preprocessing & Deskew' },
  { key: 'OCR_PROCESSING', label: 'Azure Document Intelligence OCR' },
  { key: 'TRANSCRIPTION', label: 'Model A: Transcription Correction' },
  { key: 'VERIFICATION', label: 'Model B: Independent Verification' },
  { key: 'ALIGNMENT_SCORING', label: 'Deterministic Sequence Alignment' },
  { key: 'GENERATING_DOCS', label: 'DOCX & PDF Document Generation' },
];

export const ProcessingState: React.FC<ProcessingStateProps> = ({ status, filename }) => {
  const currentStepIndex = PIPELINE_STEPS.findIndex(s => s.key === status?.status);
  const progressPercent = status?.progress_percent || 10;

  return (
    <div className="max-w-xl mx-auto py-16 px-4">
      <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-sm text-center">
        <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4 animate-spin">
          <Loader2 className="w-6 h-6" />
        </div>

        <h3 className="text-lg font-semibold text-slate-900">
          Extracting and Validating Document
        </h3>
        <p className="text-xs text-slate-500 font-mono mt-1 mb-6 truncate">
          {filename}
        </p>

        {/* Progress bar */}
        <div className="w-full bg-slate-100 rounded-full h-2 mb-2 overflow-hidden">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between items-center text-xs text-slate-500 mb-6 font-mono">
          <span>{status?.current_step || 'Initializing...'}</span>
          <span>{progressPercent}%</span>
        </div>

        {/* Steps tracker */}
        <div className="space-y-2.5 text-left border-t border-slate-100 pt-6">
          {PIPELINE_STEPS.map((step, idx) => {
            const isCompleted = currentStepIndex > idx || status?.status === 'COMPLETED';
            const isCurrent = currentStepIndex === idx;

            return (
              <div key={step.key} className="flex items-center space-x-3 text-xs">
                <div
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                    isCompleted
                      ? 'bg-emerald-100 text-emerald-600'
                      : isCurrent
                      ? 'bg-blue-100 text-blue-600 animate-pulse'
                      : 'bg-slate-100 text-slate-400'
                  }`}
                >
                  {isCompleted ? (
                    <Check className="w-3 h-3 stroke-[3]" />
                  ) : isCurrent ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Clock className="w-3 h-3" />
                  )}
                </div>
                <span
                  className={`${
                    isCompleted
                      ? 'text-slate-700 font-medium'
                      : isCurrent
                      ? 'text-blue-700 font-semibold'
                      : 'text-slate-400'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
