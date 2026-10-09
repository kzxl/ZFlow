import { NodeMetadata, WorkflowDefinition } from '../types/workflow';

const BASE_URL = '';

export async function fetchNodeDefinitions(): Promise<NodeMetadata[]> {
  const res = await fetch(`${BASE_URL}/api/nodes`);
  if (!res.ok) throw new Error(`Failed to fetch node definitions: ${res.statusText}`);
  const data = await res.json();
  return data.nodes;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  node_count: number;
  edge_count: number;
}

export async function listWorkflows(): Promise<WorkflowSummary[]> {
  const res = await fetch(`${BASE_URL}/api/workflows`);
  if (!res.ok) throw new Error(`Failed to list workflows: ${res.statusText}`);
  const data = await res.json();
  return data.workflows;
}

export async function fetchWorkflow(id: string): Promise<WorkflowDefinition> {
  const res = await fetch(`${BASE_URL}/api/workflows/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`Failed to fetch workflow: ${res.statusText}`);
  return await res.json();
}

export async function saveWorkflow(workflow: WorkflowDefinition): Promise<{ status: string; id: string; name: string }> {
  const res = await fetch(`${BASE_URL}/api/workflows`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(workflow)
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to save workflow: ${errText || res.statusText}`);
  }
  return await res.json();
}

export async function deleteWorkflow(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/workflows/${encodeURIComponent(id)}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete workflow: ${res.statusText}`);
}

export interface StreamCallbacks {
  onNodeStart?: (data: { node_id: string; title: string; type: string; step: number }) => void;
  onToken?: (data: { node_id: string; token: string }) => void;
  onNodeComplete?: (data: { node_id: string; type: string; output: any; duration_ms: number }) => void;
  onNodeError?: (data: { node_id: string; error: string }) => void;
  onWorkflowComplete?: (data: { session_id: string; final_output: string; total_time_ms: number; benchmarks?: any }) => void;
  onError?: (err: any) => void;
}

export async function streamChatWorkflow(
  workflow: WorkflowDefinition,
  input: string,
  sessionId: string,
  callbacks: StreamCallbacks
): Promise<void> {
  try {
    const res = await fetch(`${BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow,
        input,
        session_id: sessionId
      })
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Stream request failed (${res.status}): ${errText}`);
    }

    if (!res.body) throw new Error('ReadableStream not supported by browser/runtime');

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep partial line

      let currentEvent = 'message';

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        if (line.startsWith('event: ')) {
          currentEvent = line.substring(7).trim();
        } else if (line.startsWith('data: ')) {
          const rawData = line.substring(6).trim();
          try {
            const parsedData = JSON.parse(rawData);

            switch (currentEvent) {
              case 'node_start':
                callbacks.onNodeStart?.(parsedData);
                break;
              case 'token':
                callbacks.onToken?.(parsedData);
                break;
              case 'node_complete':
                callbacks.onNodeComplete?.(parsedData);
                break;
              case 'node_error':
                callbacks.onNodeError?.(parsedData);
                break;
              case 'workflow_complete':
                callbacks.onWorkflowComplete?.(parsedData);
                break;
              case 'error':
                callbacks.onError?.(new Error(parsedData.error || 'Lỗi thực thi server'));
                break;
              default:
                break;
            }
          } catch (e) {
            console.error('Failed to parse SSE JSON data:', rawData, e);
          }
        }
      }
    }
  } catch (error) {
    callbacks.onError?.(error);
  }
}

export interface SessionSummary {
  session_id: string;
  turn_count: number;
  last_updated: number;
  last_message?: string;
  last_role?: string;
}

export interface SessionStats {
  session_id: string;
  turn_count: number;
  user_turns: number;
  assistant_turns: number;
  total_chars: number;
  estimated_tokens: number;
  last_updated: number;
}

export async function fetchMemorySessions(): Promise<SessionSummary[]> {
  const res = await fetch(`${BASE_URL}/api/memory/sessions`);
  if (!res.ok) throw new Error(`Failed to fetch sessions: ${res.statusText}`);
  const data = await res.json();
  return data.sessions || [];
}

export async function fetchSessionHistory(
  sessionId: string
): Promise<{ session_id: string; stats: SessionStats; history: Array<{ role: string; content: string; timestamp: number }> }> {
  const res = await fetch(`${BASE_URL}/api/memory/sessions/${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(`Failed to fetch session history: ${res.statusText}`);
  return await res.json();
}

export async function clearSessionMemory(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/memory/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to clear session: ${res.statusText}`);
}

export interface EnchantPromptPayload {
  prompt: string;
  enchant_level?: string;
  style?: string;
  lighting?: string;
  camera?: string;
  atmosphere?: string;
  artist?: string;
  extra_boosters?: string;
  enable_subject_detailing?: boolean;
}

export interface EnchantPromptResponse {
  original_prompt: string;
  enchanted_prompt: string;
  negative_prompt: string;
  detected_subject: string;
  enchant_level: string;
  added_traits: string[];
}

export async function enchantPromptApi(payload: EnchantPromptPayload): Promise<EnchantPromptResponse> {
  const res = await fetch(`${BASE_URL}/api/enchant-prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Failed to enchant prompt: ${res.statusText}`);
  return await res.json();
}

export interface NodeTelemetryData {
  node_id: string;
  in_flight: number;
  total_completed: number;
  total_errors: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  heat_status: 'idle' | 'normal' | 'busy' | 'congested' | 'error';
}

export interface ActiveRequestInfo {
  session_id: string;
  flow_id: string;
  user_id: string;
  current_node_id: string;
  elapsed_seconds: number;
}

export interface TelemetrySnapshot {
  timestamp: number;
  total_in_flight: number;
  workflow_in_flight: number;
  current_rps: number;
  p95_latency_ms: number;
  error_rate_pct: number;
  total_completed: number;
  total_failed: number;
  nodes: Record<string, NodeTelemetryData>;
  active_requests_count: number;
  active_requests: ActiveRequestInfo[];
}

export async function fetchTelemetrySnapshot(flowId?: string): Promise<TelemetrySnapshot> {
  const url = flowId ? `${BASE_URL}/api/v1/telemetry/snapshot?flow_id=${encodeURIComponent(flowId)}` : `${BASE_URL}/api/v1/telemetry/snapshot`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch telemetry snapshot: ${res.statusText}`);
  return await res.json();
}

export function subscribeTelemetryStream(
  flowId?: string,
  onMessage?: (snap: TelemetrySnapshot) => void,
  onError?: (err: any) => void
): () => void {
  const url = flowId ? `${BASE_URL}/api/v1/telemetry/live?flow_id=${encodeURIComponent(flowId)}` : `${BASE_URL}/api/v1/telemetry/live`;
  const es = new EventSource(url);

  es.addEventListener('telemetry', (event) => {
    try {
      const parsed: TelemetrySnapshot = JSON.parse(event.data);
      if (onMessage) onMessage(parsed);
    } catch (err) {
      console.error('Failed to parse telemetry event:', err);
    }
  });

  es.onerror = (err) => {
    if (onError) onError(err);
  };

  return () => {
    es.close();
  };
}

export async function resetTelemetry(): Promise<void> {
  await fetch(`${BASE_URL}/api/v1/telemetry/reset`, { method: 'POST' });
}


