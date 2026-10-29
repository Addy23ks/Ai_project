import type {
  DocumentUploadResponse,
  DocumentStatusResponse,
  DocumentResultResponse,
  ConfigStatus
} from '../types';

const API_BASE = '/api';

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to upload document' }));
    throw new Error(errorData.detail || 'Upload failed');
  }

  return res.json();
}

export async function startExtraction(documentId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/extract`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to initiate extraction' }));
    throw new Error(errorData.detail || 'Extraction initiation failed');
  }
}

export async function getDocumentStatus(documentId: string): Promise<DocumentStatusResponse> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/status`);

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to get status' }));
    throw new Error(errorData.detail || 'Status check failed');
  }

  return res.json();
}

export async function getDocumentResult(documentId: string): Promise<DocumentResultResponse> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/result`);

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to get result' }));
    throw new Error(errorData.detail || 'Result retrieval failed');
  }

  return res.json();
}

export function getDownloadUrl(documentId: string, format: 'docx' | 'pdf'): string {
  return `${API_BASE}/documents/${documentId}/download?format=${format}`;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
  });
}

export async function getConfigStatus(): Promise<ConfigStatus> {
  const res = await fetch(`${API_BASE}/documents/config-status`);
  if (!res.ok) {
    throw new Error('Failed to retrieve configuration status');
  }
  return res.json();
}
