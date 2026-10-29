import React, { useState, useRef } from 'react';
import { Upload, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';

interface UploadZoneProps {
  onStartExtraction: (file: File) => void;
  isProcessing: boolean;
  maxSizeMb?: number;
}

const ALLOWED_EXTS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'];

export const UploadZone: React.FC<UploadZoneProps> = ({
  onStartExtraction,
  isProcessing,
  maxSizeMb = 20
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndSetFile = (file: File) => {
    setError(null);
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setError(`Unsupported file type. Please upload a PDF, PNG, JPG, JPEG, or TIFF.`);
      setSelectedFile(null);
      return;
    }

    if (file.size > maxSizeMb * 1024 * 1024) {
      setError(`File size exceeds ${maxSizeMb}MB limit.`);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleExtractClick = () => {
    if (selectedFile) {
      onStartExtraction(selectedFile);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-12 px-4 sm:px-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">
          Handwritten Document Extraction
        </h2>
        <p className="mt-2 text-sm text-slate-600 max-w-lg mx-auto">
          Extract, reconstruct, and validate handwritten notes, letters, and forms into a clean typed document with multi-stage verification.
        </p>
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xl p-8 sm:p-12 text-center transition-all bg-white ${
          dragOver
            ? 'border-blue-500 bg-blue-50/50 scale-[1.01]'
            : selectedFile
            ? 'border-emerald-400 bg-emerald-50/20'
            : 'border-slate-300 hover:border-slate-400'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
          onChange={handleFileChange}
          className="hidden"
          disabled={isProcessing}
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div
            className={`w-14 h-14 rounded-full flex items-center justify-center ${
              selectedFile
                ? 'bg-emerald-100 text-emerald-600'
                : 'bg-blue-50 text-blue-600'
            }`}
          >
            {selectedFile ? (
              <CheckCircle2 className="w-7 h-7" />
            ) : (
              <Upload className="w-7 h-7" />
            )}
          </div>

          <div>
            {selectedFile ? (
              <div className="space-y-1">
                <p className="text-sm font-semibold text-slate-900">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-slate-500 font-mono">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-medium text-slate-800">
                  Drag and drop your document here, or{' '}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-blue-600 hover:text-blue-700 font-semibold underline underline-offset-2"
                  >
                    Browse Files
                  </button>
                </p>
                <p className="text-xs text-slate-500 mt-2">
                  Supports PDF, PNG, JPG, JPEG, and TIFF (up to {maxSizeMb}MB, max 10 pages)
                </p>
              </div>
            )}
          </div>

          {selectedFile && !isProcessing && (
            <button
              type="button"
              onClick={() => {
                setSelectedFile(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
              }}
              className="text-xs text-slate-500 hover:text-rose-600 underline"
            >
              Choose a different file
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-center space-x-2 text-rose-700 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="mt-6 flex justify-center">
        <button
          type="button"
          onClick={handleExtractClick}
          disabled={!selectedFile || isProcessing}
          className={`w-full sm:w-auto px-8 py-3 rounded-lg font-medium text-sm inline-flex items-center justify-center space-x-2 transition-all shadow-sm ${
            !selectedFile || isProcessing
              ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20 hover:shadow-md'
          }`}
        >
          <span>Extract and Validate</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      <div className="mt-10 border-t border-slate-200 pt-6">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-center mb-3">
          Verification Pipeline Architecture
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs text-slate-600">
          <div className="p-2.5 rounded-lg bg-white border border-slate-200">
            <span className="font-semibold block text-slate-800">1. Image Prep</span>
            Orientation & Deskew
          </div>
          <div className="p-2.5 rounded-lg bg-white border border-slate-200">
            <span className="font-semibold block text-slate-800">2. Azure Read</span>
            Word-Weighted OCR
          </div>
          <div className="p-2.5 rounded-lg bg-white border border-slate-200">
            <span className="font-semibold block text-slate-800">3. Model A</span>
            Transcription Correction
          </div>
          <div className="p-2.5 rounded-lg bg-white border border-slate-200">
            <span className="font-semibold block text-slate-800">4. Model B</span>
            Forensic Verification
          </div>
        </div>
      </div>
    </div>
  );
};
