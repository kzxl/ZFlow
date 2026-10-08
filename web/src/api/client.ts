import { NodeMetadata, WorkflowDefinition } from '../types/workflow';

const BASE_URL = '';

export async function fetchNodeDefinitions(): Promise<NodeMetadata[]> {
  const res = await fetch(`${BASE_URL}/api/nodes`);
  if (!res.ok) throw new Error(`Failed to fetch node definitions: ${res.statusText}`);
  const data = await res.json();
  return data.nodes;
}

export async function listWorkflows(): Promise<{ id: string; name: string; description: string; node_count: number }[]> {
  const res = await fetch(`${BASE_URL}/api/workflows`);
  if (!res.ok) throw new Error(`Failed to list workflows: ${res.statusText}`);
  const data = await res.json();
  return data.workflows;
}

export async function fetchWorkflow(id: string): Promise<WorkflowDefinition> {
  const res = await fetch(`${BASE_URL}/api/workflows/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch workflow: ${res.statusText}`);
  return await res.json();
}

export async function saveWorkflow(workflow: WorkflowDefinition): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/workflows`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(workflow)
  });
  if (!res.ok) throw new Error(`Failed to save workflow: ${res.statusText}`);
}

export interface StreamCallbacks {
  onNodeStart?: (data: { node_id: string; title: string; type: string; step: number }) => void;
  onToken?: (data: { node_id: string; token: string }) => void;
  onNodeComplete?: (data: { node_id: string; type: string; output: any; duration_ms: number }) => void;
  onNodeError?: (data: { node_id: string; error: string }) => void;
  onWorkflowComplete?: (data: { session_id: string; final_output: string; total_time_ms: number }) => void;
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
