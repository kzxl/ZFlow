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
  Settings2, 
  CheckCircle2, 
  AlertCircle, 
  Loader2 
} from 'lucide-react';
import { CustomNodeData, NodeMetadata } from '../../types/workflow';

const CATEGORY_COLORS: Record<string, { bg: string; border: string; badge: string; text: string }> = {
  input: { bg: 'bg-emerald-950/40', border: 'border-emerald-600/50', badge: 'bg-emerald-500/20 text-emerald-400', text: 'text-emerald-400' },
  prompt: { bg: 'bg-amber-950/40', border: 'border-amber-600/50', badge: 'bg-amber-500/20 text-amber-400', text: 'text-amber-400' },
  llm: { bg: 'bg-indigo-950/40', border: 'border-indigo-600/50', badge: 'bg-indigo-500/20 text-indigo-400', text: 'text-indigo-400' },
  logic: { bg: 'bg-rose-950/40', border: 'border-rose-600/50', badge: 'bg-rose-500/20 text-rose-400', text: 'text-rose-400' },
  tool: { bg: 'bg-blue-950/40', border: 'border-blue-600/50', badge: 'bg-blue-500/20 text-blue-400', text: 'text-blue-400' },
  memory: { bg: 'bg-purple-950/40', border: 'border-purple-600/50', badge: 'bg-purple-500/20 text-purple-400', text: 'text-purple-400' },
  output: { bg: 'bg-cyan-950/40', border: 'border-cyan-600/50', badge: 'bg-cyan-500/20 text-cyan-400', text: 'text-cyan-400' },
  general: { bg: 'bg-slate-900/60', border: 'border-slate-700', badge: 'bg-slate-700/50 text-slate-300', text: 'text-slate-300' }
};

const ICONS: Record<string, React.ElementType> = {
  MessageSquare,
  FileText,
  Sparkles,
  GitBranch,
  Wrench,
  Database,
  Send,
  Code2,
  Globe
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

  return (
    <div
      className={`min-w-[240px] max-w-[280px] rounded-xl border bg-[#0e121e]/90 backdrop-blur-md shadow-2xl transition-all duration-200 ${
        selected ? 'ring-2 ring-indigo-500 shadow-indigo-500/20' : 'hover:border-slate-600'
      } ${
        status === 'running' ? 'border-amber-500/80 shadow-amber-500/20 ring-1 ring-amber-500' :
        status === 'completed' ? 'border-emerald-500/80' :
        status === 'error' ? 'border-rose-500/80 ring-1 ring-rose-500' : color.border
      }`}
    >
      {/* Node Header */}
      <div className={`flex items-center justify-between px-3.5 py-2.5 rounded-t-xl border-b border-slate-800/80 ${color.bg}`}>
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg ${color.badge}`}>
            <IconComponent size={15} />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-100 tracking-wide">
              {data.title || metadata?.name || type}
            </div>
            <div className="text-[10px] text-slate-400 capitalize">{category} Node</div>
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
          </div>
        )}

        {type === 'prompt' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400 line-clamp-2 italic">
            "{data.config?.system_template || 'System Instructions...'}"
          </div>
        )}

        {type === 'router' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
            <span>Pattern:</span>
            <span className="font-mono text-rose-300">{data.config?.target_pattern || 'none'}</span>
          </div>
        )}

        {type === 'tool' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
            <span>Tool:</span>
            <span className="font-mono text-blue-300 font-semibold">{data.config?.tool_name || 'datetime_now'}</span>
          </div>
        )}

        {type === 'input' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400 line-clamp-2">
            Default: <span className="text-emerald-300">"{data.config?.default_query || 'Xin chào!'}"</span>
          </div>
        )}

        {type === 'code' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 font-mono text-[10px] text-purple-300 line-clamp-2">
            Python def main(inputs, ctx)...
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

        {type === 'output' && (
          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400">
            Field: <span className="font-mono text-cyan-300">"{data.config?.output_key || 'reply'}"</span>
          </div>
        )}

        {data.executionTimeMs !== undefined && (
          <div className="text-[10px] text-right text-slate-500 font-mono">
            {data.executionTimeMs} ms
          </div>
        )}
      </div>

      {/* Target Handles (Inputs) */}
      <div className="absolute left-0 top-1/2 -translate-y-1/2 flex flex-col gap-3 -translate-x-[5px]">
        {metadata?.inputs.map((inp, idx) => (
          <div key={inp.name} className="relative group flex items-center">
            <Handle
              type="target"
              position={Position.Left}
              id={inp.name}
              style={{ top: `${(idx + 1) * 25}px` }}
              className="!w-2.5 !h-2.5 !bg-indigo-400 !border-2 !border-slate-950"
            />
            <span className="hidden group-hover:block absolute left-4 bg-slate-900 border border-slate-700 text-slate-200 text-[10px] px-1.5 py-0.5 rounded shadow z-50 whitespace-nowrap">
              {inp.label} ({inp.type})
            </span>
          </div>
        ))}
      </div>

      {/* Source Handles (Outputs) */}
      <div className="absolute right-0 top-1/2 -translate-y-1/2 flex flex-col gap-3 translate-x-[5px]">
        {metadata?.outputs.map((out, idx) => (
          <div key={out.name} className="relative group flex items-center">
            <Handle
              type="source"
              position={Position.Right}
              id={out.name}
              style={{ top: `${(idx + 1) * 25}px` }}
              className="!w-2.5 !h-2.5 !bg-emerald-400 !border-2 !border-slate-950"
            />
            <span className="hidden group-hover:block absolute right-4 bg-slate-900 border border-slate-700 text-slate-200 text-[10px] px-1.5 py-0.5 rounded shadow z-50 whitespace-nowrap">
              {out.label} ({out.type})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
