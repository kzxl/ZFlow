import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { 
  MessageSquare, 
  FileText, 
  Sparkles, 
  GitBranch, 
  Wrench, 
  Database, 
  Send, 
  Code2,
  Globe,
  GitFork,
  BookOpen,
  BrainCircuit,
  UserCheck,
  Image,
  Palette,
  Eye,
  ExternalLink,
  Zap,
  Settings2, 
  CheckCircle2, 
  AlertCircle, 
  Loader2,
  Copy,
  Trash2
} from 'lucide-react';
import { CustomNodeData, NodeMetadata, PortDefinition } from '../../types/workflow';

const CATEGORY_COLORS: Record<string, { bg: string; border: string; badge: string; text: string }> = {
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

const ICONS: Record<string, React.ElementType> = {
  MessageSquare,
  FileText,
  Sparkles,
  GitBranch,
  GitFork,
  BookOpen,
  BrainCircuit,
  UserCheck,
  Image,
  Palette,
  Eye,
  Wrench,
  Database,
  Send,
  Code2,
  Globe,
  Zap
};

// Fallback port definitions in case metadata is loading
const DEFAULT_PORTS: Record<string, { inputs: PortDefinition[]; outputs: PortDefinition[] }> = {
  input: {
    inputs: [],
    outputs: [
      { name: 'query', type: 'string', label: 'User Query' },
      { name: 'session_id', type: 'string', label: 'Session ID' }
    ]
  },
  prompt: {
    inputs: [{ name: 'input_text', type: 'string', label: 'Input Text' }],
    outputs: [{ name: 'prompt', type: 'string', label: 'Prompt' }]
  },
  llm: {
    inputs: [{ name: 'prompt', type: 'string', label: 'Prompt' }],
    outputs: [{ name: 'text', type: 'string', label: 'Text' }]
  },
  router: {
    inputs: [{ name: 'input_text', type: 'string', label: 'Input Text' }],
    outputs: [
      { name: 'true_branch', type: 'string', label: 'If True' },
      { name: 'false_branch', type: 'string', label: 'If False' }
    ]
  },
  tool: {
    inputs: [{ name: 'input_arg', type: 'string', label: 'Argument' }],
    outputs: [{ name: 'result', type: 'string', label: 'Result' }]
  },
  memory: {
    inputs: [
      { name: 'session_id', type: 'string', label: 'Session ID' },
      { name: 'user_message', type: 'string', label: 'User Msg' },
      { name: 'bot_message', type: 'string', label: 'Bot Msg' }
    ],
    outputs: [
      { name: 'chat_history', type: 'array', label: 'History Array' },
      { name: 'formatted_history', type: 'string', label: 'Formatted Text' },
      { name: 'turn_count', type: 'number', label: 'Turn Count' },
      { name: 'summary', type: 'string', label: 'Summary' }
    ]
  },
  code: {
    inputs: [{ name: 'input_data', type: 'any', label: 'Input Data' }],
    outputs: [{ name: 'result', type: 'any', label: 'Output Result' }]
  },
  http: {
    inputs: [{ name: 'trigger_data', type: 'any', label: 'Trigger' }],
    outputs: [{ name: 'response_body', type: 'any', label: 'Response' }]
  },
  output: {
    inputs: [{ name: 'response_text', type: 'string', label: 'Response' }],
    outputs: [{ name: 'final_output', type: 'string', label: 'Final Output' }]
  },
  system1_reflex: {
    inputs: [{ name: 'query', type: 'string', label: 'User Query' }],
    outputs: [
      { name: 'fast_reply', type: 'string', label: '⚡ Fast Reply (System 1)' },
      { name: 'system_2', type: 'string', label: '🧠 Escalate (System 2)' },
      { name: 'blocked', type: 'string', label: '🛡️ Guardrail Block' }
    ]
  },
  permission_guard: {
    inputs: [
      { name: 'query', type: 'string', label: 'Query / Action' },
      { name: 'user_role', type: 'string', label: 'User Role' }
    ],
    outputs: [
      { name: 'granted', type: 'string', label: '✅ Granted (Authorized)' },
      { name: 'denied', type: 'string', label: '⛔ Denied (Unauthorized)' }
    ]
  },
  semantic_cache: {
    inputs: [
      { name: 'query', type: 'string', label: 'Query' },
      { name: 'response_to_cache', type: 'string', label: 'Response to Cache' }
    ],
    outputs: [
      { name: 'cache_hit', type: 'string', label: '⚡ Cache Hit (<0.1ms)' },
      { name: 'cache_miss', type: 'string', label: '🔍 Cache Miss (Forward)' }
    ]
  }
};

interface CustomFlowCardProps {
  id: string;
  type: string;
  data: CustomNodeData;
  metadata?: NodeMetadata;
  selected?: boolean;
}

export const CustomFlowCard: React.FC<CustomFlowCardProps> = ({ id, type, data, metadata, selected }) => {
  const category = metadata?.category || 'general';
  const color = CATEGORY_COLORS[category] || CATEGORY_COLORS.general;
  const IconComponent = ICONS[metadata?.icon || 'Sparkles'] || Sparkles;

  const status = data.status || 'idle';

  // Resolve inputs and outputs
  const fallback = DEFAULT_PORTS[type] || { inputs: [], outputs: [] };
  const inputs = metadata?.inputs && metadata.inputs.length > 0 ? metadata.inputs : fallback.inputs;
  let outputs = metadata?.outputs && metadata.outputs.length > 0 ? metadata.outputs : fallback.outputs;

  if (type === 'router' && data.config?.mode !== 'if_else') {
    const branches = Array.isArray(data.config?.branches) && data.config.branches.length > 0
      ? data.config.branches
      : [
          { id: 'branch_support', name: 'Support', label: 'Support' },
          { id: 'branch_sales', name: 'Sales', label: 'Sales' }
        ];

    outputs = [
      ...branches.map((b: any, idx: number) => ({
        name: b.id || `branch_${idx + 1}`,
        type: 'string',
        label: b.label || b.name || `Case ${idx + 1}`
      })),
      {
        name: 'default_branch',
        type: 'string',
        label: data.config?.default_label || 'Default / Else'
      }
    ];
  }

  if (type === 'llm_router') {
    let routes = [];
    if (typeof data.config?.routes === 'string') {
      try {
        routes = JSON.parse(data.config.routes);
      } catch {
        routes = [];
      }
    } else if (Array.isArray(data.config?.routes)) {
      routes = data.config.routes;
    }

    if (!routes || routes.length === 0) {
      routes = [
        { id: 'sales', name: 'Tư vấn Bán hàng' },
        { id: 'technical_support', name: 'Hỗ trợ Kỹ thuật' },
        { id: 'general_faq', name: 'Hỏi đáp Chung' }
      ];
    }

    outputs = [
      ...routes.map((r: any, idx: number) => ({
        name: r.id || `route_${idx + 1}`,
        type: 'string',
        label: r.name || r.id || `Nhánh ${idx + 1}`
      })),
      {
        name: data.config?.fallback_branch || 'default_branch',
        type: 'string',
        label: 'Khác / Fallback'
      }
    ];
  }

  if (type === 'system1_reflex') {
    outputs = [
      { name: 'fast_reply', type: 'string', label: '⚡ Fast Reply (System 1)' },
      { name: 'system_2', type: 'string', label: '🧠 Escalate (System 2)' },
      { name: 'blocked', type: 'string', label: '🛡️ Guardrail Block' }
    ];
  }

  if (type === 'permission_guard') {
    outputs = [
      { name: 'granted', type: 'string', label: '✅ Granted (Authorized)' },
      { name: 'denied', type: 'string', label: '⛔ Denied (Unauthorized)' }
    ];
  }

  if (type === 'semantic_cache') {
    outputs = [
      { name: 'cache_hit', type: 'string', label: '⚡ Cache Hit (<0.1ms)' },
      { name: 'cache_miss', type: 'string', label: '🔍 Cache Miss (Forward)' }
    ];
  }

  return (
    <div
      onDoubleClick={(e) => {
        e.stopPropagation();
        data.openConfigModal?.();
      }}
      className={`relative w-[270px] rounded-xl border bg-[#0d101a] backdrop-blur-md shadow-2xl transition-all duration-150 select-none ${
        selected ? 'ring-2 ring-indigo-500 shadow-[0_0_25px_rgba(99,102,241,0.35)] scale-[1.01]' : 'hover:border-slate-600/80'
      } ${
        status === 'running' ? '!border-amber-500/90 shadow-amber-500/25 ring-1 ring-amber-500' :
        status === 'completed' ? '!border-emerald-500/80' :
        status === 'error' ? '!border-rose-500/90 ring-1 ring-rose-500' : color.border
      }`}
    >
      {/* Floating Action Toolbar on Selected Node */}
      {selected && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-[#121626]/95 border border-indigo-500/50 rounded-lg p-1 shadow-2xl backdrop-blur-md z-50 animate-in fade-in zoom-in-95 duration-100">
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.openConfigModal?.();
            }}
            className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            title="Configure Node (or double-click)"
          >
            <Settings2 size={13} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onDuplicate?.();
            }}
            className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            title="Duplicate Node"
          >
            <Copy size={13} />
          </button>
          <div className="w-px h-3 bg-slate-700 mx-0.5" />
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onDelete?.();
            }}
            className="p-1 rounded text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 transition-colors"
            title="Delete Node"
          >
            <Trash2 size={13} />
          </button>
        </div>
      )}

      {/* Node Header */}
      <div className={`flex items-center justify-between px-3.5 py-2.5 rounded-t-xl border-b border-slate-800/80 ${color.bg}`}>
        <div className="flex items-center gap-2.5">
          <div className={`p-1.5 rounded-lg shadow-sm ${color.badge}`}>
            <IconComponent size={15} />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-100 tracking-wide leading-tight">
              {data.title || metadata?.name || type}
            </div>
            <div className="text-[10px] text-slate-400 capitalize font-mono mt-0.5">{category} node</div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {status === 'running' && <Loader2 size={13} className="text-amber-400 animate-spin" />}
          {status === 'completed' && <CheckCircle2 size={13} className="text-emerald-400" />}
          {status === 'error' && <AlertCircle size={13} className="text-rose-400" />}

          <button
            onClick={(e) => {
              e.stopPropagation();
              data.openConfigModal?.();
            }}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
            title="Configure Node Options"
          >
            <Settings2 size={14} />
          </button>
        </div>
      </div>

      {/* Ports Section: Left for inputs, Right for outputs */}
      {(inputs.length > 0 || outputs.length > 0) && (
        <div className="py-2 space-y-1.5 border-b border-slate-800/60 bg-[#090b12]/50">
          {/* Input Ports */}
          {inputs.map((inp) => (
            <div key={inp.name} className="relative flex items-center h-6 px-3">
              <Handle
                type="target"
                position={Position.Left}
                id={inp.name}
                className="!w-2.5 !h-2.5 !-left-[5px] !bg-indigo-400 !border-2 !border-[#0d101a] hover:!bg-indigo-300 transition-colors"
              />
              <div className="flex items-center gap-1.5 text-[11px] text-slate-300 pl-1">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400/80"></span>
                <span className="font-medium text-slate-200">{inp.label}</span>
                <span className="text-[9px] text-slate-500 font-mono">({inp.type})</span>
              </div>
            </div>
          ))}

          {/* Output Ports */}
          {outputs.map((out) => (
            <div key={out.name} className="relative flex items-center justify-end h-6 px-3">
              <div className="flex items-center gap-1.5 text-[11px] text-slate-300 pr-1">
                <span className="text-[9px] text-slate-500 font-mono">({out.type})</span>
                <span className="font-medium text-slate-200">{out.label}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/80"></span>
              </div>
              <Handle
                type="source"
                position={Position.Right}
                id={out.name}
                className="!w-2.5 !h-2.5 !-right-[5px] !bg-emerald-400 !border-2 !border-[#0d101a] hover:!bg-emerald-300 transition-colors"
              />
            </div>
          ))}
        </div>
      )}

      {/* Node Body / Options Summary */}
      <div className="p-3 text-[11px] text-slate-300 space-y-2">
        {type === 'llm' && (
          <div className="flex flex-col gap-1 bg-slate-900/60 p-2 rounded-lg border border-slate-800/60">
            <div className="flex justify-between text-slate-400">
              <span>Model:</span>
              <span className="font-mono text-indigo-300 font-semibold">{data.config?.model || 'gpt-4o-mini'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Temp:</span>
              <span className="font-mono text-slate-300">{data.config?.temperature ?? 0.7}</span>
            </div>
            {data.config?.response_format === 'json_object' && (
              <div className="flex justify-between text-amber-400 text-[10px]">
                <span>Format:</span>
                <span className="font-mono font-semibold">JSON Mode</span>
              </div>
            )}
          </div>
        )}

        {type === 'prompt' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400 line-clamp-2 italic text-[10px] leading-relaxed">
            "{data.config?.system_template || 'System Instructions...'}"
          </div>
        )}

        {type === 'router' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 space-y-1">
            <div className="flex justify-between text-slate-400">
              <span>Mode:</span>
              <span className="font-mono text-indigo-300 font-semibold uppercase text-[10px]">
                {data.config?.mode === 'if_else' ? 'If / Else' : 'Switch-Case'}
              </span>
            </div>
            {data.config?.mode === 'if_else' ? (
              <div className="flex justify-between text-slate-400">
                <span>Pattern:</span>
                <span className="font-mono text-rose-300 truncate max-w-[140px]">{data.config?.target_pattern || 'none'}</span>
              </div>
            ) : (
              <div className="flex justify-between text-slate-400">
                <span>Branches:</span>
                <span className="font-mono text-emerald-300 font-semibold">
                  {(data.config?.branches?.length || 2) + 1} Routes
                </span>
              </div>
            )}
          </div>
        )}

        {type === 'tool' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
            <span>Tool:</span>
            <span className="font-mono text-blue-300 font-semibold">{data.config?.tool_name || 'datetime_now'}</span>
          </div>
        )}

        {type === 'code' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 font-mono text-[10px] text-purple-300 truncate">
            def main(inputs, context): ...
          </div>
        )}

        {type === 'http' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex flex-col gap-0.5 text-slate-400">
            <div className="flex justify-between">
              <span>Method:</span>
              <span className="font-mono text-cyan-300 font-semibold">{data.config?.method || 'POST'}</span>
            </div>
            <div className="text-[10px] text-slate-500 truncate">{data.config?.url || 'https://...'}</div>
          </div>
        )}

        {type === 'image_gen' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 space-y-1.5">
            <div className="flex justify-between text-slate-400">
              <span>Provider:</span>
              <span className="font-mono text-pink-300 font-semibold uppercase text-[10px]">
                {data.config?.provider || 'simulator'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Ratio:</span>
              <span className="font-mono text-slate-300">{data.config?.aspect_ratio || '1:1'}</span>
            </div>
            {/* Live ComfyUI-style Image Preview on Canvas Card */}
            {(data.lastOutput?.image_url || data.config?.preview_url) && (
              <div className="mt-1.5 rounded-lg overflow-hidden border border-pink-500/40 relative group shadow-md">
                <img
                  src={data.lastOutput?.image_url || data.config?.preview_url}
                  alt="AI Generated"
                  className="w-full h-28 object-cover rounded-md hover:scale-105 transition-transform duration-200"
                />
                <a
                  href={data.lastOutput?.image_url || data.config?.preview_url}
                  target="_blank"
                  rel="noreferrer"
                  className="absolute top-1 right-1 p-1 bg-black/80 hover:bg-black text-white rounded text-[10px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5 shadow"
                  title="Mở ảnh kích thước đầy đủ"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink size={10} />
                </a>
              </div>
            )}
          </div>
        )}

        {type === 'prompt_styler' && (
          <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 flex flex-col gap-1.5 text-slate-400">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-slate-400">Enchant Level:</span>
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold flex items-center gap-1 ${
                data.config?.enchant_level === 'masterpiece_epic' 
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' 
                  : data.config?.enchant_level === 'ai_magic_rewrite'
                  ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                  : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
              }`}>
                <Sparkles size={10} />
                {data.config?.enchant_level === 'masterpiece_epic' ? 'Epic 8K' :
                 data.config?.enchant_level === 'ai_magic_rewrite' ? 'AI Magic' :
                 data.config?.enchant_level || 'Vivid'}
              </span>
            </div>
            
            <div className="flex justify-between text-[10px]">
              <span>Style & Light:</span>
              <span className="font-mono text-slate-200 truncate max-w-[140px]">
                {data.config?.style || 'cinematic'} • {data.config?.lighting || 'dramatic'}
              </span>
            </div>

            {data.config?.atmosphere && data.config.atmosphere !== 'none' && (
              <div className="flex justify-between text-[10px]">
                <span>Atmosphere:</span>
                <span className="font-mono text-cyan-300 truncate max-w-[140px]">
                  {data.config.atmosphere.replace('_', ' ')}
                </span>
              </div>
            )}

            {/* Enchanted Prompt Output Preview */}
            {(data.lastOutput?.positive_prompt || data.lastOutput?.styled_prompt) && (
              <div className="mt-1 pt-1.5 border-t border-slate-800/80">
                <div className="flex items-center justify-between text-[9px] text-slate-500 mb-0.5">
                  <span className="flex items-center gap-1 text-pink-400 font-semibold">
                    <Sparkles size={9} /> Enchanted Output
                  </span>
                  {data.lastOutput?.detected_subject && (
                    <span className="px-1 py-0.2 bg-slate-800 text-slate-300 rounded font-mono">
                      #{data.lastOutput.detected_subject}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-300 italic line-clamp-2 leading-tight bg-black/40 p-1.5 rounded border border-slate-800/60 font-mono">
                  "{data.lastOutput?.positive_prompt || data.lastOutput?.styled_prompt}"
                </p>
              </div>
            )}
          </div>
        )}

        {type === 'vision' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex flex-col gap-1 text-slate-400">
            <div className="flex justify-between">
              <span>Task:</span>
              <span className="font-mono text-indigo-300 font-semibold text-[10px]">{data.config?.task_mode || 'general_description'}</span>
            </div>
          </div>
        )}

        {type === 'rag' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
            <span>Top Chunks:</span>
            <span className="font-mono text-purple-300 font-semibold">{data.config?.top_k || 3}</span>
          </div>
        )}

        {type === 'agent' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
            <span>Loops:</span>
            <span className="font-mono text-indigo-300 font-semibold">{data.config?.max_iterations || 4} iters</span>
          </div>
        )}

        {type === 'human_input' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
            <span>Approval:</span>
            <span className="font-mono text-rose-300 font-semibold">{data.config?.action_type || 'approve_reject'}</span>
          </div>
        )}

        {type === 'input' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400 line-clamp-2 text-[10px]">
            Query: <span className="text-emerald-300 italic">"{data.config?.default_query || 'Xin chào!'}"</span>
          </div>
        )}

        {type === 'output' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400 flex justify-between">
            <span>API Output Key:</span>
            <span className="font-mono text-cyan-300 font-semibold">"{data.config?.output_key || 'reply'}"</span>
          </div>
        )}

        {type === 'system1_reflex' && (
          <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 flex flex-col gap-1.5 text-slate-400">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-slate-400">Mode:</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1 font-mono">
                <Zap size={10} />
                System 1 (&lt;1ms)
              </span>
            </div>
            {data.lastOutput?.decision && (
              <div className="flex items-center justify-between text-[10px]">
                <span>Quyết định:</span>
                <span className={`font-mono font-semibold px-1 py-0.5 rounded text-[9px] ${
                  data.lastOutput.decision === 'fast_reply' 
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' 
                    : data.lastOutput.decision === 'blocked'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                }`}>
                  {data.lastOutput.decision === 'fast_reply' ? '⚡ Fast Reply' :
                   data.lastOutput.decision === 'blocked' ? '🛡️ Guardrail' : '🧠 Escalate System 2'}
                </span>
              </div>
            )}
            {data.lastOutput?.latency_ms !== undefined && (
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>Reflex Time:</span>
                <span className="text-amber-300 font-semibold">{data.lastOutput.latency_ms} ms</span>
              </div>
            )}
            {data.lastOutput?.reply && (
              <p className="text-[10px] text-slate-300 italic line-clamp-2 leading-tight bg-black/40 p-1.5 rounded border border-slate-800/60 font-mono mt-0.5">
                "{data.lastOutput.reply}"
              </p>
            )}
          </div>
        )}

        {type === 'permission_guard' && (
          <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 flex flex-col gap-1.5 text-slate-400">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-slate-400">Min Role:</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 uppercase font-mono">
                {data.config?.required_role || 'staff'}
              </span>
            </div>
            {data.lastOutput?.active_branch && (
              <div className="flex items-center justify-between text-[10px]">
                <span>Quyết định:</span>
                <span className={`font-mono font-semibold px-1 py-0.5 rounded text-[9px] ${
                  data.lastOutput.active_branch === 'granted' 
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' 
                    : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                }`}>
                  {data.lastOutput.active_branch === 'granted' ? '✅ Granted' : '⛔ Denied'}
                </span>
              </div>
            )}
            {data.lastOutput?.reason && (
              <p className="text-[10px] text-slate-400 line-clamp-1 italic">
                {data.lastOutput.reason}
              </p>
            )}
          </div>
        )}

        {type === 'semantic_cache' && (
          <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 flex flex-col gap-1.5 text-slate-400">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-slate-400">Threshold:</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-blue-500/20 text-blue-300 border border-blue-500/40">
                {(data.config?.similarity_threshold ?? 0.85) * 100}% Sim
              </span>
            </div>
            {data.lastOutput?.active_branch && (
              <div className="flex items-center justify-between text-[10px]">
                <span>Status:</span>
                <span className={`font-mono font-semibold px-1 py-0.5 rounded text-[9px] ${
                  data.lastOutput.active_branch === 'cache_hit' 
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' 
                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                }`}>
                  {data.lastOutput.active_branch === 'cache_hit' ? '⚡ 0.1ms Cache Hit' : '🔍 Cache Miss'}
                </span>
              </div>
            )}
            {data.lastOutput?.cached_response && (
              <p className="text-[10px] text-slate-300 italic line-clamp-2 leading-tight bg-black/40 p-1.5 rounded border border-slate-800/60 font-mono mt-0.5">
                "{data.lastOutput.cached_response}"
              </p>
            )}
          </div>
        )}

        {data.executionTimeMs !== undefined && (
          <div className="text-[10px] text-right text-slate-500 font-mono pt-1">
            ⚡ {data.executionTimeMs} ms
          </div>
        )}
      </div>
    </div>
  );
};
