export type NodeCategory = 'input' | 'prompt' | 'llm' | 'logic' | 'tool' | 'memory' | 'output' | 'media' | 'general';

export interface PortDefinition {
  name: string;
  type: string;
  label: string;
  required?: boolean;
  description?: string;
}

export interface ConfigFieldSchema {
  type: 'string' | 'textarea' | 'number' | 'select' | 'password' | 'boolean';
  label: string;
  default?: any;
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
}

export interface NodeMetadata {
  type: string;
  name: string;
  category: NodeCategory;
  description: string;
  icon: string;
  inputs: PortDefinition[];
  outputs: PortDefinition[];
  configSchema: Record<string, ConfigFieldSchema>;
}

export interface CustomNodeData extends Record<string, unknown> {
  title: string;
  config: Record<string, any>;
  status?: 'idle' | 'running' | 'completed' | 'error';
  lastOutput?: Record<string, any>;
  executionTimeMs?: number;
  telemetry?: {
    node_id: string;
    in_flight: number;
    total_completed: number;
    total_errors: number;
    avg_duration_ms: number;
    p95_duration_ms: number;
    heat_status: 'idle' | 'normal' | 'busy' | 'congested' | 'error';
  };
  onConfigChange?: (config: Record<string, any>) => void;
  openConfigModal?: () => void;
  onDuplicate?: () => void;
  onDelete?: () => void;
  [key: string]: unknown;
}

export interface NodeBenchmarkItem {
  node_id: string;
  title?: string;
  type?: string;
  step?: number;
  start_offset_ms?: number;
  duration_ms: number;
  tokens?: number;
  cost_usd?: number;
  status?: 'success' | 'error';
  error?: string;
}

export interface ExecutionBenchmark {
  ttftMs?: number;
  totalTimeMs?: number;
  tokenCount?: number;
  tokensPerSec?: number;
  estimatedCostUsd?: number;
  estimatedCostVnd?: number;
  nodeLatencies?: {
    nodeId: string;
    title?: string;
    type?: string;
    durationMs: number;
  }[];
  nodes?: NodeBenchmarkItem[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  tokens?: number;
  benchmark?: ExecutionBenchmark;
  nodeSteps?: {
    nodeId: string;
    title: string;
    type: string;
    durationMs?: number;
    status: 'running' | 'completed' | 'error';
  }[];
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  description?: string;
  nodes: any[];
  edges: any[];
}

export type ContextMenuType = 'pane' | 'node' | 'edge';

export interface ContextMenuState {
  isOpen: boolean;
  type: ContextMenuType;
  x: number;
  y: number;
  flowPosition?: { x: number; y: number };
  targetId?: string;
  nodeData?: {
    id: string;
    type: string;
    title: string;
    config: Record<string, any>;
  };
  edgeData?: {
    id: string;
    source: string;
    target: string;
    sourceHandle?: string | null;
    targetHandle?: string | null;
  };
}
