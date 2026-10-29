import React from 'react';
import type {
  ConfidenceBreakdown,
  Discrepancy,
  Correction,
  UncertainSpan
} from '../types';
import { ShieldAlert, CheckCircle, HelpCircle } from 'lucide-react';

interface ValidationDetailsProps {
  breakdown: ConfidenceBreakdown;
  discrepancies: Discrepancy[];
  corrections: Correction[];
  uncertainSpans: UncertainSpan[];
}

export const ValidationDetails: React.FC<ValidationDetailsProps> = ({
  breakdown,
  discrepancies,
  corrections,
  uncertainSpans
}) => {
  return (
    <div className="space-y-6 pt-2">
      {/* 4 Core Evidence Pillars */}
      <div>
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Component Confidence Breakdown (Heuristic Weights)
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-slate-500">Azure OCR Confidence</span>
              <span className="text-xs font-semibold text-blue-600">Weight 35%</span>
            </div>
            <div className="text-xl font-bold text-slate-800">
              {breakdown.ocr_confidence}%
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Word-weighted primary OCR score
            </p>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-slate-500">Independent Verification</span>
              <span className="text-xs font-semibold text-blue-600">Weight 30%</span>
            </div>
            <div className="text-xl font-bold text-slate-800">
              {breakdown.verification_agreement}%
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Model B findings & penalty audit
            </p>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-slate-500">Normalized Alignment</span>
              <span className="text-xs font-semibold text-blue-600">Weight 20%</span>
            </div>
            <div className="text-xl font-bold text-slate-800">
              {breakdown.text_agreement}%
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Levenshtein sequence token similarity
            </p>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-slate-500">Completeness & Integrity</span>
              <span className="text-xs font-semibold text-blue-600">Weight 15%</span>
            </div>
            <div className="text-xl font-bold text-slate-800">
              {breakdown.completeness_score}%
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Page coverage & dropped line deductions
            </p>
          </div>
        </div>
      </div>

      {breakdown.status_override_applied && (
        <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 flex items-start space-x-2.5">
          <ShieldAlert className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-amber-900">
            <span className="font-semibold block">Guardrail Override Triggered:</span>
            {breakdown.override_reason}
          </div>
        </div>
      )}

      {/* Discrepancies */}
      {discrepancies.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
            <span>Detected Discrepancies ({discrepancies.length})</span>
          </h4>
          <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100">
            {discrepancies.map((d, i) => (
              <div key={i} className="p-3 bg-white text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-1.5 py-0.5 rounded font-mono font-semibold text-[10px] ${
                        d.severity === 'CRITICAL'
                          ? 'bg-rose-100 text-rose-700'
                          : d.severity === 'MATERIAL'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {d.severity}
                    </span>
                    <span className="font-semibold text-slate-800">{d.type}</span>
                  </div>
                  <span className="text-slate-400">Page {d.page}</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                  <div className="bg-slate-50 p-1.5 rounded">
                    <span className="text-[10px] text-slate-400 block uppercase">Proposed:</span>
                    <span className="font-mono text-slate-700">{d.text_segment || '(none)'}</span>
                  </div>
                  <div className="bg-slate-50 p-1.5 rounded">
                    <span className="text-[10px] text-slate-400 block uppercase">Expected / Image Evidence:</span>
                    <span className="font-mono text-emerald-700">{d.expected_segment || '(none)'}</span>
                  </div>
                </div>
                {d.evidence && (
                  <p className="text-[11px] text-slate-500 italic mt-0.5">
                    Evidence: {d.evidence}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Model A Corrections Made */}
      {corrections.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Model A Transcription Corrections ({corrections.length})
          </h4>
          <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100">
            {corrections.map((c, i) => (
              <div key={i} className="p-2.5 bg-white text-xs flex items-start space-x-3">
                <CheckCircle className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="line-through text-slate-400 font-mono">{c.original_ocr}</span>
                    <span className="text-slate-400">→</span>
                    <span className="font-semibold text-slate-900 font-mono">{c.corrected}</span>
                  </div>
                  <p className="text-[11px] text-slate-500">{c.reason}</p>
                  {c.evidence && (
                    <p className="text-[10px] text-slate-400 italic">Visual clue: {c.evidence}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Uncertain Spans */}
      {uncertainSpans.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Flagged Ambiguous Handwriting Spans ({uncertainSpans.length})
          </h4>
          <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100">
            {uncertainSpans.map((u, i) => (
              <div key={i} className="p-2.5 bg-white text-xs flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <HelpCircle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                  <span className="font-mono font-medium text-amber-900 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                    {u.text}
                  </span>
                  <span className="text-slate-500">{u.reason}</span>
                </div>
                <span className="text-slate-400 text-[11px]">Page {u.page} ({u.location})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
