import React, { useState } from 'react';
import type {
  DocumentResultResponse,
  ValidationStatus
} from '../types';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileDown,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  FileText,
  ShieldCheck
} from 'lucide-react';
import { ValidationDetails } from './ValidationDetails';
import { getDownloadUrl } from '../services/api';

interface ResultsViewProps {
  result: DocumentResultResponse;
  onReset: () => void;
}

export const ResultsView: React.FC<ResultsViewProps> = ({ result, onReset }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'raw'>('preview');

  const getStatusBadge = (status: ValidationStatus) => {
    switch (status) {
      case 'Passed Validation':
        return {
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-600 mr-2" />,
          classes: 'bg-emerald-50 text-emerald-800 border-emerald-200',
          title: 'Passed Validation',
        };
      case 'Requires Review':
        return {
          icon: <AlertTriangle className="w-5 h-5 text-amber-600 mr-2" />,
          classes: 'bg-amber-50 text-amber-800 border-amber-200',
          title: 'Requires Review',
        };
      case 'Failed Validation':
      default:
        return {
          icon: <XCircle className="w-5 h-5 text-rose-600 mr-2" />,
          classes: 'bg-rose-50 text-rose-800 border-rose-200',
          title: 'Failed Validation',
        };
    }
  };

  const badge = getStatusBadge(result.validation_status);

  return (
    <div className="max-w-4xl mx-auto py-10 px-4 sm:px-6 space-y-6">
      {/* Dev Mode Notice banner if mock pipeline */}
      {result.is_mock_pipeline && result.mock_notice && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>{result.mock_notice}</span>
          </div>
          <span className="font-mono text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
            DEV MODE
          </span>
        </div>
      )}

      {/* Primary Score & Status Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="flex items-center space-x-3">
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${badge.classes}`}
              >
                {badge.icon}
                {badge.title}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {result.filename}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Processed {result.page_count} page(s) on {new Date(result.created_at).toLocaleString()}
            </p>
          </div>

          <div className="flex items-baseline space-x-2 bg-slate-50 px-5 py-3 rounded-xl border border-slate-200/80">
            <span className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              {result.confidence_score}%
            </span>
            <div className="text-left">
              <span className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Confidence
              </span>
              <span className="text-xs text-slate-600">
                {result.confidence_breakdown.score_label}
              </span>
            </div>
          </div>
        </div>

        {/* Validation Summary */}
        <div className="py-4">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Validation Summary
          </h4>
          <p className="text-sm text-slate-700 leading-relaxed font-medium">
            {result.validation_summary}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-slate-100">
          <a
            href={getDownloadUrl(result.document_id, 'docx')}
            download
            className="inline-flex items-center space-x-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium transition-all shadow-sm"
          >
            <FileDown className="w-4 h-4" />
            <span>Download DOCX</span>
          </a>

          <a
            href={getDownloadUrl(result.document_id, 'pdf')}
            download
            className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-medium transition-all shadow-sm"
          >
            <FileDown className="w-4 h-4" />
            <span>Download PDF</span>
          </a>

          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center space-x-1.5 px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-lg text-xs font-medium transition-all ml-auto"
          >
            <RotateCcw className="w-4 h-4 text-slate-500" />
            <span>Upload Another Document</span>
          </button>
        </div>
      </div>

      {/* Extracted Document Viewer */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-800">
              Extracted Typed Document
            </h3>
          </div>

          <div className="flex items-center space-x-1 bg-slate-200/60 p-0.5 rounded-lg text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('preview')}
              className={`px-3 py-1 rounded-md font-medium transition-all ${
                activeTab === 'preview'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Formatted Preview
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('raw')}
              className={`px-3 py-1 rounded-md font-medium transition-all ${
                activeTab === 'raw'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Plain Text
            </button>
          </div>
        </div>

        <div className="p-6 sm:p-8 max-h-[550px] overflow-y-auto">
          {activeTab === 'preview' ? (
            <div
              className="prose prose-sm max-w-none text-slate-800 font-sans leading-relaxed"
              dangerouslySetInnerHTML={{ __html: result.formatted_preview_html }}
            />
          ) : (
            <pre className="text-xs font-mono text-slate-800 whitespace-pre-wrap leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-200">
              {result.proposed_transcription}
            </pre>
          )}
        </div>
      </div>

      {/* Expandable Validation Details */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <button
          type="button"
          onClick={() => setShowDetails(!showDetails)}
          className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-slate-50/70 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <span className="text-sm font-semibold text-slate-900">
              Validation Details & Audit Evidence
            </span>
            <span className="text-xs font-mono text-slate-400">
              (OCR, Dual-Model Agreement, Completeness, Discrepancies)
            </span>
          </div>
          {showDetails ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>

        {showDetails && (
          <div className="px-6 pb-6 border-t border-slate-100">
            <ValidationDetails
              breakdown={result.confidence_breakdown}
              discrepancies={result.discrepancies}
              corrections={result.corrections_made}
              uncertainSpans={result.uncertain_spans}
            />
          </div>
        )}
      </div>
    </div>
  );
};
