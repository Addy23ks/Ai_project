import React from 'react';
import { FileText, ShieldCheck, AlertCircle } from 'lucide-react';
import type { ConfigStatus } from '../types';

interface HeaderProps {
  config: ConfigStatus | null;
}

export const Header: React.FC<HeaderProps> = ({ config }) => {
  return (
    <header className="border-b border-slate-200 bg-white shadow-sm">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-900 tracking-tight">
              Handwritten Document Extraction
            </h1>
            <p className="text-xs text-slate-500">
              Dual-Model Forensic Verification & Confidence Validation
            </p>
          </div>
        </div>

        {config && (
          <div className="hidden sm:flex items-center space-x-2 text-xs">
            {config.azure_ocr_configured ? (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <ShieldCheck className="w-3.5 h-3.5 mr-1" />
                Azure OCR Live
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-violet-50 text-violet-700 border border-violet-200" title="OCR performed by LLM vision model (Azure not configured)">
                <AlertCircle className="w-3.5 h-3.5 mr-1" />
                LLM Vision OCR
              </span>
            )}
            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-mono text-slate-600 bg-slate-100 border border-slate-200">
              {config.model_a_model} & {config.model_b_model}
            </span>
          </div>
        )}
      </div>
    </header>
  );
};
