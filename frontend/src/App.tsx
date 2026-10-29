import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { UploadZone } from './components/UploadZone';
import { ProcessingState } from './components/ProcessingState';
import { ResultsView } from './components/ResultsView';
import type {
  ConfigStatus,
  DocumentStatusResponse,
  DocumentResultResponse
} from './types';
import {
  uploadDocument,
  startExtraction,
  getDocumentStatus,
  getDocumentResult,
  getConfigStatus
} from './services/api';
import { AlertCircle } from 'lucide-react';

type ScreenState = 'upload' | 'processing' | 'results';

export const App: React.FC = () => {
  const [screen, setScreen] = useState<ScreenState>('upload');
  const [config, setConfig] = useState<ConfigStatus | null>(null);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [status, setStatus] = useState<DocumentStatusResponse | null>(null);
  const [result, setResult] = useState<DocumentResultResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    getConfigStatus()
      .then(setConfig)
      .catch((err) => console.warn('Could not load config status:', err));
  }, []);

  const handleStartExtraction = async (file: File) => {
    try {
      setErrorMessage(null);
      setCurrentFile(file);
      setScreen('processing');

      // 1. Upload
      const uploadRes = await uploadDocument(file);

      // 2. Start Extraction
      await startExtraction(uploadRes.document_id);

      // 3. Poll for progress
      pollStatus(uploadRes.document_id);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(err.message || 'Failed to upload document.');
      setScreen('upload');
    }
  };

  const pollStatus = (docId: string) => {
    const interval = setInterval(async () => {
      try {
        const statusRes = await getDocumentStatus(docId);
        setStatus(statusRes);

        if (statusRes.status === 'COMPLETED') {
          clearInterval(interval);
          const finalResult = await getDocumentResult(docId);
          setResult(finalResult);
          setScreen('results');
        } else if (statusRes.status === 'FAILED') {
          clearInterval(interval);
          setErrorMessage(statusRes.error_message || 'Document processing failed.');
          setScreen('upload');
        }
      } catch (err: any) {
        clearInterval(interval);
        setErrorMessage(err.message || 'Error checking processing status.');
        setScreen('upload');
      }
    }, 1200);
  };

  const handleReset = () => {
    setScreen('upload');
    setCurrentFile(null);
    setStatus(null);
    setResult(null);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 selection:bg-blue-100 selection:text-blue-900">
      <Header config={config} />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-rose-800 text-sm shadow-sm animate-fade-in">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold block">Processing Error</span>
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs text-rose-600 hover:underline font-medium"
            >
              Dismiss
            </button>
          </div>
        )}

        {screen === 'upload' && (
          <UploadZone
            onStartExtraction={handleStartExtraction}
            isProcessing={false}
            maxSizeMb={config?.max_upload_size_mb || 20}
          />
        )}

        {screen === 'processing' && (
          <ProcessingState
            status={status}
            filename={currentFile?.name || 'Document'}
          />
        )}

        {screen === 'results' && result && (
          <ResultsView
            result={result}
            onReset={handleReset}
          />
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        Handwritten Document Extraction System &bull; Azure AI Document Intelligence &bull; Dual-Model Validation
      </footer>
    </div>
  );
};

export default App;
