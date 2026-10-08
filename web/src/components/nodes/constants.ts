import { PortDefinition } from '../../types/workflow';

export const CATEGORY_COLORS: Record<string, { bg: string; border: string; badge: string; text: string }> = {
  input: { bg: 'bg-emerald-950/50', border: 'border-emerald-600/40', badge: 'bg-emerald-500/20 text-emerald-400', text: 'text-emerald-400' },
  prompt: { bg: 'bg-amber-950/50', border: 'border-amber-600/40', badge: 'bg-amber-500/20 text-amber-400', text: 'text-amber-400' },
  llm: { bg: 'bg-indigo-950/50', border: 'border-indigo-600/40', badge: 'bg-indigo-500/20 text-indigo-400', text: 'text-indigo-400' },
  logic: { bg: 'bg-rose-950/50', border: 'border-rose-600/40', badge: 'bg-rose-500/20 text-rose-400', text: 'text-rose-400' },
  tool: { bg: 'bg-blue-950/50', border: 'border-blue-600/40', badge: 'bg-blue-500/20 text-blue-400', text: 'text-blue-400' },
  memory: { bg: 'bg-purple-950/50', border: 'border-purple-600/40', badge: 'bg-purple-500/20 text-purple-400', text: 'text-purple-400' },
  media: { bg: 'bg-pink-950/50', border: 'border-pink-600/40', badge: 'bg-pink-500/20 text-pink-400', text: 'text-pink-400' },
  output: { bg: 'bg-cyan-950/50', border: 'border-cyan-600/40', badge: 'bg-cyan-500/20 text-cyan-400', text: 'text-cyan-400' },
  general: { bg: 'bg-slate-900/60', border: 'border-slate-700/60', badge: 'bg-slate-700/50 text-slate-300', text: 'text-slate-300' }
};

export const DEFAULT_PORTS: Record<string, { inputs: PortDefinition[]; outputs: PortDefinition[] }> = {
  input: {
    inputs: [],
    outputs: [
      { name: 'query', type: 'string', label: 'User Query' },
      { name: 'payload', type: 'object', label: 'Structured Payload (JSON)' },
      { name: 'task_type', type: 'string', label: 'Task Type / Purpose' },
      { name: 'metadata', type: 'object', label: 'Envelope Metadata' },
      { name: 'session_id', type: 'string', label: 'Session ID' },
      { name: 'access_token', type: 'string', label: 'Access Token (JWT)' }
    ]
  },
  output: {
    inputs: [{ name: 'input', type: 'any', label: 'Final Content' }],
    outputs: [{ name: 'output', type: 'any', label: 'Output Result' }]
  },
  prompt: {
    inputs: [
      { name: 'input', type: 'string', label: 'Query / Input' },
      { name: 'history', type: 'string', label: 'History (Opt)' },
      { name: 'context', type: 'string', label: 'Context (Opt)' }
    ],
    outputs: [
      { name: 'prompt', type: 'string', label: 'Built Prompt' },
      { name: 'system_prompt', type: 'string', label: 'System Directive' }
    ]
  },
  llm: {
    inputs: [
      { name: 'prompt', type: 'string', label: 'Input Prompt' },
      { name: 'system_prompt', type: 'string', label: 'System Prompt' },
      { name: 'chat_history', type: 'array', label: 'History' }
    ],
    outputs: [
      { name: 'reply', type: 'string', label: 'LLM Response' },
      { name: 'token_count', type: 'number', label: 'Token Count' }
    ]
  },
  router: {
    inputs: [{ name: 'input', type: 'any', label: 'Condition Target' }],
    outputs: [
      { name: 'branch_true', type: 'any', label: 'True / Matched' },
      { name: 'branch_false', type: 'any', label: 'False / Default' }
    ]
  },
  llm_router: {
    inputs: [
      { name: 'query', type: 'string', label: 'User Query' },
      { name: 'chat_history', type: 'array', label: 'Chat History' }
    ],
    outputs: [
      { name: 'selected_branch', type: 'string', label: 'Selected Branch' },
      { name: 'reasoning', type: 'string', label: 'Routing Reasoning' },
      { name: 'query_passthrough', type: 'string', label: 'Query Passthrough' }
    ]
  },
  system1_reflex: {
    inputs: [{ name: 'query', type: 'string', label: 'Incoming Query' }],
    outputs: [
      { name: 'fast_reply', type: 'string', label: '⚡ Fast Reply (< 1ms)' },
      { name: 'system_2', type: 'string', label: '🧠 Escalate System 2' },
      { name: 'blocked', type: 'string', label: '🛡️ Blocked Guardrail' }
    ]
  },
  permission_guard: {
    inputs: [
      { name: 'query', type: 'string', label: 'Incoming Query / Action' },
      { name: 'user_role', type: 'string', label: 'User Role (Opt)' }
    ],
    outputs: [
      { name: 'granted', type: 'string', label: '✅ Granted' },
      { name: 'denied', type: 'string', label: '⛔ Denied' }
    ]
  },
  semantic_cache: {
    inputs: [
      { name: 'query', type: 'string', label: 'Incoming Query' },
      { name: 'response_to_cache', type: 'string', label: 'Response to Write (Opt)' }
    ],
    outputs: [
      { name: 'cache_hit', type: 'string', label: '⚡ Cache Hit (<0.1ms)' },
      { name: 'cache_miss', type: 'string', label: '🔍 Cache Miss' }
    ]
  },
  memory: {
    inputs: [
      { name: 'user_message', type: 'string', label: 'User Message' },
      { name: 'bot_message', type: 'string', label: 'Bot Message' }
    ],
    outputs: [
      { name: 'formatted_history', type: 'string', label: 'Formatted History' },
      { name: 'expanded_context', type: 'string', label: 'Expanded Context' },
      { name: 'chat_history', type: 'array', label: 'History Array' }
    ]
  },
  rag: {
    inputs: [
      { name: 'query', type: 'string', label: 'Search Query' },
      { name: 'user_role', type: 'string', label: 'User Role (Opt)' },
      { name: 'learn_fact', type: 'string', label: 'Learn Fact (Opt)' }
    ],
    outputs: [
      { name: 'context', type: 'string', label: 'Retrieved Docs' },
      { name: 'augmented_prompt', type: 'string', label: 'Augmented Prompt' }
    ]
  },
  image_gen: {
    inputs: [
      { name: 'prompt', type: 'string', label: 'Image Prompt' },
      { name: 'negative_prompt', type: 'string', label: 'Negative Prompt' }
    ],
    outputs: [
      { name: 'image_url', type: 'string', label: 'Generated Image URL' },
      { name: 'metadata', type: 'any', label: 'Generation Meta' }
    ]
  },
  prompt_styler: {
    inputs: [{ name: 'prompt', type: 'string', label: 'Raw Idea / Concept' }],
    outputs: [
      { name: 'enchanted_prompt', type: 'string', label: 'Enchanted Prompt' },
      { name: 'negative_prompt', type: 'string', label: 'Negative Prompt' }
    ]
  },
  vision: {
    inputs: [
      { name: 'image_url', type: 'string', label: 'Image URL / Base64' },
      { name: 'instruction', type: 'string', label: 'Instruction' }
    ],
    outputs: [
      { name: 'analysis', type: 'string', label: 'Visual Analysis' },
      { name: 'ocr_text', type: 'string', label: 'Extracted OCR' }
    ]
  },
  tool: {
    inputs: [{ name: 'input', type: 'any', label: 'Tool Arguments' }],
    outputs: [{ name: 'result', type: 'any', label: 'Tool Output' }]
  },
  code: {
    inputs: [{ name: 'input', type: 'any', label: 'Input Payload' }],
    outputs: [{ name: 'result', type: 'any', label: 'Python Return' }]
  },
  http: {
    inputs: [{ name: 'body', type: 'any', label: 'Request Body' }],
    outputs: [
      { name: 'response', type: 'any', label: 'HTTP Response' },
      { name: 'status_code', type: 'number', label: 'Status Code' }
    ]
  },
  agent: {
    inputs: [
      { name: 'goal', type: 'string', label: 'Agent Goal' },
      { name: 'context', type: 'string', label: 'Context Docs' }
    ],
    outputs: [
      { name: 'final_answer', type: 'string', label: 'Final Answer' },
      { name: 'steps', type: 'array', label: 'Execution Steps' }
    ]
  },
  human_input: {
    inputs: [{ name: 'content', type: 'string', label: 'Pending Content' }],
    outputs: [
      { name: 'approved', type: 'string', label: 'Approved Path' },
      { name: 'rejected', type: 'string', label: 'Rejected Path' }
    ]
  },
  subflow: {
    inputs: [
      { name: 'input', type: 'string', label: 'Query / Payload' },
      { name: 'variables', type: 'object', label: 'Injected Vars (Opt)' }
    ],
    outputs: [
      { name: 'output', type: 'string', label: 'Primary Output' },
      { name: 'reply', type: 'string', label: 'Assistant Reply' },
      { name: 'all_outputs', type: 'object', label: 'Subflow Vars' }
    ]
  },
  webhook: {
    inputs: [],
    outputs: [
      { name: 'payload', type: 'object', label: 'Webhook Body' },
      { name: 'headers', type: 'object', label: 'HTTP Headers' },
      { name: 'event', type: 'string', label: 'Event Name' },
      { name: 'task_type', type: 'string', label: 'Task Type / Purpose' },
      { name: 'metadata', type: 'object', label: 'Envelope Metadata' },
      { name: 'query', type: 'string', label: 'Normalized Query' },
      { name: 'access_token', type: 'string', label: 'Access Token (JWT)' }
    ]
  },
  gateway: {
    inputs: [
      { name: 'input', type: 'any', label: 'Request / Payload' },
      { name: 'context', type: 'object', label: 'Headers / Ctx (Opt)' }
    ],
    outputs: [
      { name: 'route_a', type: 'any', label: '🔀 Route A (Primary)' },
      { name: 'route_b', type: 'any', label: '🔀 Route B (Secondary)' },
      { name: 'route_c', type: 'any', label: '🔀 Route C (Tertiary)' },
      { name: 'throttled', type: 'any', label: '⏳ Throttled (Rate Limit)' },
      { name: 'fallback', type: 'any', label: '🛡️ Fallback (Circuit Open)' }
    ]
  },
  auth: {
    inputs: [
      { name: 'input', type: 'any', label: 'Payload / Query' },
      { name: 'credentials', type: 'object', label: 'Credentials / Token' },
      { name: 'headers', type: 'object', label: 'HTTP Headers (Opt)' }
    ],
    outputs: [
      { name: 'authenticated', type: 'any', label: '✅ Authenticated' },
      { name: 'unauthorized', type: 'object', label: '⛔ Unauthorized (401)' },
      { name: 'access_token', type: 'string', label: 'JWT Token' },
      { name: 'session_id', type: 'string', label: 'Session ID' }
    ]
  }
};
