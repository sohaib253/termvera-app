export interface Organization {
  id: string;
  name: string;
  industry: string | null;
  country: string | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
}

export type MembershipRole = "owner" | "admin" | "member";

export interface MeResponse {
  user: User;
  organization: Organization;
  role: MembershipRole;
  is_admin: boolean;
}

export interface SampleDocument {
  key: string;
  filename: string;
  title: string;
  description: string;
  module: "tenderguard" | "clauserisk";
  document_type: string;
  size_bytes: number;
}

export type ProjectStatus = "draft" | "active" | "submitted" | "archived";
export type AnalysisStatus = "not_started" | "processing" | "completed" | "failed";

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  client_name: string | null;
  tender_reference: string | null;
  sector: string | null;
  status: ProjectStatus;
  submission_deadline: string | null;
  currency: string | null;
  confidentiality: string | null;
  notes: string | null;
  owner_user_id: string | null;
  created_by_user_id: string;
  is_demo: boolean;
  analysis_status: AnalysisStatus;
  analysis_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateInput {
  name: string;
  client_name?: string;
  tender_reference?: string;
  sector?: string;
  submission_deadline?: string;
  currency?: string;
  confidentiality?: string;
  notes?: string;
}

export type DocumentType = "tender" | "bid" | "supporting" | "reference";
export type ExtractionStatus = "pending" | "processing" | "completed" | "failed";

export interface TenderDocument {
  id: string;
  project_id: string;
  document_type: DocumentType;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  page_count: number | null;
  extraction_status: ExtractionStatus;
  extraction_error: string | null;
  extraction_pages_done: number | null;
  created_at: string;
}

export interface DocumentPage {
  page_number: number;
  text: string;
  char_count: number;
  extraction_method: string;
  low_text_warning: boolean;
}

export type MandatoryStatus = "mandatory" | "conditional" | "indicative" | "unclear";
export type AssessmentStatusValue =
  | "not_assessed"
  | "compliant_looking"
  | "partially_addressed"
  | "evidence_not_found"
  | "potential_non_compliance"
  | "not_applicable_pending_verification"
  | "human_verified"
  | "human_rejected";
export type EvidenceQuality = "strong" | "adequate" | "insufficient" | "none" | "unknown";
export type AssessmentConfidence = "high" | "medium" | "low";
export type Priority = "critical" | "high" | "medium" | "low" | "informational";

export interface Assessment {
  id: string;
  status: AssessmentStatusValue;
  evidence_quality: EvidenceQuality;
  assessment_confidence: AssessmentConfidence;
  priority: Priority;
  reason: string;
  missing_information: string[];
  requires_human_review: boolean;
  ai_provider: string | null;
  prompt_version: string | null;
  reviewer_status: string;
  reviewer_user_id: string | null;
  updated_at: string;
}

export interface EvidenceRecord {
  id: string;
  document_id: string;
  page_number: number;
  excerpt: string;
  retrieval_method: string;
  evidence_type: string | null;
  relevance_note: string | null;
  potential_conflict: string | null;
}

export interface ReviewAction {
  id: string;
  user_id: string | null;
  action_type: string;
  previous_status: string | null;
  new_status: string | null;
  comment: string | null;
  created_at: string;
}

export interface Requirement {
  id: string;
  project_id: string;
  source_document_id: string;
  source_page: number;
  source_clause: string | null;
  source_excerpt: string;
  title: string;
  normalized_requirement: string;
  category: string;
  mandatory_status: MandatoryStatus;
  conditions: string | null;
  required_evidence: string | null;
  extraction_uncertain: boolean;
  assessment: Assessment | null;
}

export interface RequirementDetail extends Requirement {
  evidence_records: EvidenceRecord[];
  review_actions: ReviewAction[];
}

export interface ReviewActionInput {
  new_status?: AssessmentStatusValue;
  comment?: string;
}

export interface AnalysisStatusResponse {
  analysis_status: AnalysisStatus;
  analysis_error: string | null;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
}

export type LicensePlan = "free" | "demo" | "trial" | "professional" | "enterprise";

export interface License {
  plan: LicensePlan;
  status: string;
  seat_limit: number;
  project_limit: number;
  monthly_document_limit: number;
  monthly_analysis_limit: number;
  monthly_contract_limit: number;
  monthly_clause_analysis_limit: number;
  enabled_modules: string[];
  expires_at: string | null;
  state: LicenseState;
  read_only: boolean;
  ends_at: string | null;
  days_left: number | null;
  licensed_to: string | null;
  license_id: string | null;
  /** This computer's ID, for requesting a key bound to this PC. */
  machine_id: string | null;
  /** Set when the active key only works on one computer. */
  bound_machine_id: string | null;
}

/** trial: free trial running; trial_expired / expired: view-only;
 *  active: paid up; grace: lapsed but still fully usable for a few days. */
export type LicenseState =
  /** Free early access: no countdown, no limits. */
  | "free"
  | "trial"
  | "trial_expired"
  | "active"
  | "grace"
  | "expired"
  /** A per-PC key, and this workspace was copied to a different PC. */
  | "other_machine";

export interface DesktopStatus {
  desktop: boolean;
  setup_required: boolean;
  /** False during free early access. */
  billing_enabled?: boolean;
}

export interface UpcomingDeadline {
  project_id: string;
  name: string;
  client_name: string | null;
  submission_deadline: string;
  days_remaining: number;
}

export interface DashboardSummary {
  projects_total: number;
  projects_active: number;
  requirements_awaiting_review: number;
  critical_requirements: number;
  overdue_deadlines: number;
  upcoming_deadlines: UpcomingDeadline[];
  contracts_total: number;
  contracts_analyzed: number;
  findings_unreviewed: number;
  findings_by_severity: Record<string, number>;
}

export interface Usage {
  license: License;
  projects_used: number;
  documents_used_this_period: number;
  analyses_used_this_period: number;
  contracts_used: number;
  clause_analyses_used_this_period: number;
  period_start: string;
}

// ---------------------------------------------------------------------------
// ClauseRisk module
// ---------------------------------------------------------------------------

export type ContractType =
  | "commercial"
  | "epc"
  | "oil_and_gas"
  | "engineering"
  | "construction"
  | "services"
  | "other";
export type ContractStatus = "draft" | "under_review" | "active" | "superseded" | "archived";
export type ContractAnalysisStatus = "not_started" | "processing" | "completed" | "failed";

export interface Contract {
  id: string;
  project_id: string;
  name: string;
  contract_type: ContractType;
  status: ContractStatus;
  counterparty_name: string | null;
  effective_date: string | null;
  notes: string | null;
  is_demo: boolean;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ContractVersion {
  id: string;
  contract_id: string;
  document_id: string;
  version_number: number;
  version_label: string;
  analysis_status: ContractAnalysisStatus;
  analysis_error: string | null;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
  analysis_stage: string | null;
  analysis_progress_current: number;
  analysis_progress_total: number;
  created_at: string;
  document: ContractVersionDocument | null;
}

/** The uploaded file behind a contract version, and how far text
 *  extraction (OCR, for a scan) has got. */
export interface ContractVersionDocument {
  original_filename: string;
  page_count: number | null;
  extraction_status: ExtractionStatus;
  extraction_error: string | null;
  extraction_pages_done: number | null;
}

export interface ContractDetail extends Contract {
  versions: ContractVersion[];
}

export interface ContractListItem extends Contract {
  project_name: string;
}

export interface ContractCreateInput {
  name: string;
  contract_type?: ContractType;
  counterparty_name?: string;
  effective_date?: string;
  notes?: string;
}

export interface ContractUpdateInput {
  name?: string;
  contract_type?: ContractType;
  status?: ContractStatus;
  counterparty_name?: string;
  effective_date?: string;
  notes?: string;
}

export interface ContractAnalysisStatusResponse {
  analysis_status: ContractAnalysisStatus;
  analysis_error: string | null;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
  /** Populated while processing: which stage is running, and how far
   *  through it. A local-model run can take over an hour, so these drive a
   *  real progress bar rather than an indefinite spinner. */
  analysis_stage: string | null;
  analysis_progress_current: number;
  analysis_progress_total: number;
}

export type SourceConfidence = "high" | "medium" | "low";

export interface Clause {
  id: string;
  contract_version_id: string;
  clause_number: string | null;
  title: string;
  text: string;
  page_start: number;
  page_end: number;
  sequence_index: number;
  category: string | null;
  subcategory: string | null;
  source_confidence: SourceConfidence | null;
  extraction_error: string | null;
  referenced_clauses: string[];
  extracted_obligations: string[];
  extracted_rights: string[];
  extracted_conditions: string[];
  extracted_exceptions: string[];
  extracted_amounts: string[];
  extracted_dates: string[];
  extracted_percentages: string[];
  extracted_time_periods: string[];
}

export interface CrossClauseLink {
  id: string;
  clause_a_id: string;
  clause_b_id: string;
  relationship_type: string;
  basis: "explicit_reference" | "category_pattern";
  note: string | null;
}

export interface ClauseDetail extends Clause {
  links: CrossClauseLink[];
}

export type RiskSeverity = "critical" | "high" | "medium" | "low" | "informational";
export type AffectedParty = "contractor" | "client" | "both" | "third_party" | "unclear";
export type RiskUncertainty =
  | "explicit"
  | "not_applicable"
  | "not_found"
  | "ambiguous"
  | "conflicting"
  | "requires_review";
export type FindingReviewerStatus =
  | "unreviewed"
  | "accepted"
  | "rejected"
  | "marked_for_negotiation"
  | "reviewed";

export interface RiskEvidenceItem {
  document_id: string | null;
  clause_id: string | null;
  /** Page in the PDF file, as a viewer's page box counts it. */
  page: number | null;
  /** The page number printed on that page ("7 of 12"), when there is one. */
  page_label?: string | null;
  clause_number?: string | null;
  clause_title?: string | null;
  section_title?: string | null;
  excerpt: string;
  verified: boolean;
}

export interface RiskFinding {
  id: string;
  contract_version_id: string;
  clause_id: string | null;
  category: string;
  risk_type: string;
  /** Human-readable name for risk_type, resolved by the API so the
   *  taxonomy lives only in the backend. */
  risk_type_label: string;
  severity: RiskSeverity;
  risk_description: string;
  contractual_effect: string | null;
  potential_exposure: string | null;
  trigger: string | null;
  affected_party: AffectedParty;
  uncertainty: RiskUncertainty;
  recommended_review_action: string | null;
  computed_score: number;
  reviewer_status: FindingReviewerStatus;
  assigned_to_user_id: string | null;
  ai_provider: string | null;
  prompt_version: string | null;
  updated_at: string;
  evidence: RiskEvidenceItem[];
  related_clauses: string[];
  risk_factors: Record<string, unknown>;
}

export interface FindingReviewAction {
  id: string;
  user_id: string | null;
  action_type: string;
  previous_status: string | null;
  new_status: string | null;
  comment: string | null;
  created_at: string;
}

export interface RiskFindingDetail extends RiskFinding {
  review_actions: FindingReviewAction[];
}

export interface RiskFindingListItem extends RiskFinding {
  contract_id: string;
  contract_name: string;
  clause_number: string | null;
}

export const RISK_SEVERITY_ORDER: RiskSeverity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "informational",
];

export interface FindingReviewActionInput {
  new_status?: FindingReviewerStatus;
  assign_to_user_id?: string;
  comment?: string;
}

export type ChangeType = "added" | "deleted" | "modified";
export type Materiality = "material" | "minor";

export interface ContractChange {
  id: string;
  change_type: ChangeType;
  clause_number: string | null;
  category: string | null;
  base_clause_id: string | null;
  compared_clause_id: string | null;
  description: string;
  materiality: Materiality;
  financial_delta: string | null;
}

export interface ContractComparison {
  id: string;
  contract_id: string;
  base_version_id: string;
  compared_version_id: string;
  created_at: string;
  changes: ContractChange[];
}

export interface CompareVersionsInput {
  base_version_id: string;
  compared_version_id: string;
}
