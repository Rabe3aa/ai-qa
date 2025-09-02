export interface DashboardStats {
  total_calls: number;
  processed_calls: number;
  pending_calls: number;
  failed_calls: number;
  average_score: number | null;
  total_processing_time: number | null;
}
export interface AgentPerformance {
  agent_name: string;
  total_calls: number;
  average_score: number | null;
  recent_calls: number;
}
export interface Project {
  id: number;
  name: string;
  description?: string | null;
  company_id: number;
  created_at?: string;
  is_active: boolean;
}

export interface Call {
  id: number;
  project_id: number;
  filename: string;
  agent_name?: string | null;
  customer_name?: string | null;
  s3_key: string;
  s3_output_key?: string | null;
  transcription_job_name?: string | null;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  call_duration?: number | null;
  uploaded_at: string;
  processed_at?: string | null;
  error_message?: string | null;
}

export interface QAReport {
  id: number;
  call_id: number;
  transcript?: string | null;
  corrected_transcript?: string | null;
  agent_summary?: string | null;
  qa_scores?: Record<string, any> | null;
  qa_feedback?: string | null;
  overall_score?: number | null;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  model_used?: string | null;
  processing_time_seconds?: number | null;
  created_at: string;
}
