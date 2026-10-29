export type ValidationStatus =
  | 'Passed Validation'
  | 'Requires Review'
  | 'Failed Validation'
  | 'Processing Failed';

export type ProcessingStep =
  | 'PENDING'
  | 'PREPROCESSING'
  | 'OCR_PROCESSING'
  | 'TRANSCRIPTION'
  | 'VERIFICATION'
  | 'ALIGNMENT_SCORING'
  | 'GENERATING_DOCS'
  | 'COMPLETED'
  | 'FAILED';

export interface UncertainSpan {
  text: string;
  page: number;
  location: string;
  reason: string;
}

export interface Correction {
  original_ocr: string;
  corrected: string;
  reason: string;
  evidence: string;
  page: number;
}

export interface Discrepancy {
  type: string;
  text_segment: string;
  expected_segment: string;
  severity: 'CRITICAL' | 'MATERIAL' | 'MINOR';
  evidence: string;
  page: number;
}

export interface ConfidenceBreakdown {
  ocr_confidence: number;
  verification_agreement: number;
  text_agreement: number;
  completeness_score: number;
  preliminary_score: number;
  final_score: number;
  score_label: string;
  status_override_applied: boolean;
  override_reason?: string;
  weights_used: Record<string, number>;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  file_size: number;
  page_count: number;
  created_at: string;
  status: ProcessingStep;
}

export interface DocumentStatusResponse {
  document_id: string;
  status: ProcessingStep;
  progress_percent: number;
  current_step: string;
  error_message?: string;
}

export interface DocumentResultResponse {
  document_id: string;
  filename: string;
  validation_status: ValidationStatus;
  confidence_score: number;
  confidence_breakdown: ConfidenceBreakdown;
  validation_summary: string;
  why_summary: string;
  proposed_transcription: string;
  formatted_preview_html: string;
  uncertain_spans: UncertainSpan[];
  corrections_made: Correction[];
  discrepancies: Discrepancy[];
  page_count: number;
  created_at: string;
  is_mock_pipeline: boolean;
  mock_notice?: string;
}

export interface ConfigStatus {
  azure_ocr_configured: boolean;
  model_a_configured: boolean;
  model_a_provider: string;
  model_a_model: string;
  model_b_configured: boolean;
  model_b_provider: string;
  model_b_model: string;
  max_upload_size_mb: number;
  max_document_pages: number;
  pass_threshold: number;
  review_threshold: number;
}
