// TypeScript mirrors of the Pydantic schemas in backend/models/schemas.py

export type ProviderStatus = 'live_granite' | 'cached_demo'
export type StepExecutor = 'human' | 'ai' | 'hybrid'
export type GuardrailType =
  | 'human_approval'
  | 'confidence_threshold'
  | 'exception_routing'
  | 'manual_fallback'
  | 'skill_preservation'
  | 'audit_trail'
export type AnalysisStatus = 'pending' | 'running' | 'complete' | 'error'
export type ReadinessLabel = 'Low' | 'Medium' | 'High'
export type RiskLabel = 'Low' | 'Medium' | 'High'
export type OverheadSource = 'proposal' | 'default'

export interface WorkflowStep {
  step_id: string
  event_type: string
  label: string
  avg_duration_minutes: number
  occurrence_count: number
  is_hidden_work: boolean
  is_in_official: boolean
}

export interface HiddenWorkEvidence {
  event_id: string
  ticket_id: string
  event_type: string
  duration_minutes: number
  notes: string
  description: string
}

export interface HiddenWorkSummary {
  total_hidden_events: number
  total_hidden_minutes: number
  hidden_work_ratio: number
  hidden_event_types: string[]
  evidence: HiddenWorkEvidence[]
}

export interface OverheadAssumption {
  field: string
  value: number
  source: OverheadSource
  default_value: number | null
}

export interface AnalysisMetrics {
  official_total_minutes: number
  actual_total_minutes: number
  ai_automated_total_minutes: number
  hybrid_total_minutes: number
  hidden_work_ratio: number
  gross_time_saved: number
  review_overhead: number
  correction_overhead: number
  exception_overhead: number
  maintenance_overhead: number
  failure_recovery_overhead: number
  ai_overhead: number
  ai_tax: number
  net_time_saved: number
  burden_concentration: number
  automation_readiness: number
  automation_readiness_label: ReadinessLabel
  skill_loss_risk: RiskLabel
  missing_fallback_count: number
  overhead_assumptions: OverheadAssumption[]
}

export interface GuardrailItem {
  id: string
  label: string
  type: GuardrailType
  description: string
}

export interface SaferStep {
  step_id: string
  label: string
  executor: StepExecutor
  requires_approval: boolean
  fallback_procedure: string | null
  confidence_threshold: number | null
}

export interface GraniteOutput {
  workflow_gap_narrative: string
  hidden_work_narrative: string
  redesign_recommendations: string[]
  guardrails: GuardrailItem[]
  safer_workflow_steps: SaferStep[]
  provider: ProviderStatus
}

export interface AnalysisResult {
  analysis_id: string
  scenario_id: string
  status: AnalysisStatus
  created_at: string
  completed_at: string | null
  official_workflow: WorkflowStep[]
  actual_workflow: WorkflowStep[]
  hidden_work: HiddenWorkSummary
  metrics: AnalysisMetrics
  granite_output: GraniteOutput | null
  provider_status: ProviderStatus
  disclaimer: string
}

export interface ScenarioMeta {
  scenario_id: string
  name: string
  description: string
  event_count: number
  ticket_count: number
}

export interface HealthResponse {
  status: string
  provider: ProviderStatus
  version: string
}

export interface ProviderStatusResponse {
  provider: ProviderStatus
}
