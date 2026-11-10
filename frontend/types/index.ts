// Types mirroring the backend Pydantic schemas.

export type Severity = "critical" | "high" | "medium" | "low" | "informational";
export type Confidence = "confirmed" | "suspicious" | "inconclusive";
export type EvidenceSource =
  | "simulation"
  | "onchain"
  | "explorer"
  | "source_code"
  | "abi"
  | "bytecode"
  | "heuristic";
export type AnalysisStatus = "queued" | "running" | "completed" | "failed";

export interface Finding {
  id: string;
  title: string;
  category: string;
  severity: Severity;
  confidence: Confidence;
  source: EvidenceSource;
  description: string;
  evidence: Record<string, unknown>;
  impact?: string | null;
  recommendation?: string | null;
  references: string[];
  metadata: Record<string, unknown>;
}

export interface TokenMetadata {
  name: string | null;
  symbol: string | null;
  decimals: number | null;
  total_supply: number | null;
  metadata_complete: boolean;
  errors: string[];
}

export interface ProxyInfo {
  is_proxy: boolean;
  proxy_type: string | null;
  implementation: string | null;
  admin: string | null;
  beacon: string | null;
  detection_methods: string[];
}

export interface PairInfo {
  address: string;
  dex_name: string;
  factory: string;
  router: string;
  token0: string | null;
  token1: string | null;
  reserve_token: number | null;
  reserve_native: number | null;
  liquidity_native_wei: number | null;
  has_liquidity: boolean;
}

export interface TokenInfo {
  address: string;
  chain_id: number;
  chain_name: string;
  is_contract: boolean;
  bytecode_size: number;
  metadata: TokenMetadata;
  owner: string | null;
  ownership_renounced: boolean | null;
  is_verified: boolean | null;
  verification_source: string | null;
  proxy: ProxyInfo;
  contract_type: string;
  erc20_compliant: boolean | null;
  detected_functions: Record<string, boolean>;
  pairs: PairInfo[];
  creation_block: number | null;
  notes: string[];
}

export interface TxResult {
  success: boolean;
  gas_used: number | null;
  error: string | null;
  revert_reason: string | null;
  tx_hash: string | null;
  decoded_log_count: number;
}

export interface ScenarioResult {
  name: string;
  wallet: string;
  fork_block: number;
  buy_amount_wei: number;
  expected_tokens_out: number | null;
  tokens_received: number | null;
  buy_tax_bps: number | null;
  buy_result: TxResult;
  sell_amount_tokens: number | null;
  expected_native_out: number | null;
  native_received_wei: number | null;
  sell_tax_bps: number | null;
  sell_result: TxResult | null;
  gas_price_wei: number | null;
  notes: string[];
}

export interface SimulationReport {
  performed: boolean;
  reason: string | null;
  fork_block: number | null;
  chain_id: number;
  token_address: string;
  pair: Record<string, unknown> | null;
  router: string | null;
  factory: string | null;
  scenarios: ScenarioResult[];
  buy_success_any: boolean;
  sell_success_any: boolean;
  buy_tax_bps: number | null;
  sell_tax_bps: number | null;
  can_buy_cannot_sell: boolean;
  limitations: string[];
}

export interface RiskAssessment {
  score: number;
  classification: string;
  explanation: string[];
  contributing_findings: string[];
  uncertainties: string[];
  disclaimer: string;
}

export interface AnalysisResult {
  analysis_id: string;
  chain_id: number;
  token_address: string;
  status: AnalysisStatus;
  analysis_depth: string;
  block_number: number | null;
  duration_ms: number | null;
  token: TokenInfo | null;
  findings: Finding[];
  risk: RiskAssessment | null;
  simulation: SimulationReport | null;
  tax: Record<string, unknown> | null;
  owner_analysis: Record<string, unknown> | null;
  warnings: string[];
  error: string | null;
}

export interface AnalysisCreated {
  analysis_id: string;
  status: AnalysisStatus;
  poll_url: string;
}

export interface AnalysisSummary {
  analysis_id: string;
  chain_id: number;
  token_address: string;
  status: AnalysisStatus;
  risk_score: number | null;
  risk_classification: string | null;
  created_at: string;
}

export interface Stats {
  total_analyses: number;
  high_risk: number;
  critical_risk: number;
  average_duration_ms: number | null;
}

export interface ChainInfo {
  chain_id: number;
  name: string;
  native_symbol: string;
  testnet: boolean;
  rpc_configured: boolean;
  explorer_api: boolean;
  dexes: string[];
}
