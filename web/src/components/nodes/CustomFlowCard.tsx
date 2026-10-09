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
  Zap, 
  Settings2, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Copy, 
  Trash2 
} from 'lucide-react';
import { CustomNodeData, NodeMetadata, PortDefinition } from '../../types/workflow';
import { CATEGORY_COLORS, DEFAULT_PORTS } from './constants';
import { NodeBodyPreview } from './previews/NodeBodyPreview';

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

interface CustomFlowCardProps {
  id: string;
  data: CustomNodeData;
  type?: string;
  selected?: boolean;
}

export const CustomFlowCard: React.FC<CustomFlowCardProps> = ({ id, data, type = 'general', selected }) => {
  const metadata = data.metadata as NodeMetadata | undefined;
  const category = metadata?.category || 'general';
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.general;

  // Resolve node icon
  const IconComponent = (metadata?.icon && ICONS[metadata.icon]) 
    ? ICONS[metadata.icon] 
    : (ICONS[type] || MessageSquare);

  // Dynamic port definitions fallback
  const defaultPortDef = DEFAULT_PORTS[type] || { inputs: [], outputs: [] };
  const inputs: PortDefinition[] = metadata?.inputs || defaultPortDef.inputs;
  const outputs: PortDefinition[] = metadata?.outputs || defaultPortDef.outputs;

  const status = data.status || 'idle';
  const telemetry = data.telemetry;
  const inFlightCount = telemetry?.in_flight || 0;
  const heatStatus = telemetry?.heat_status || 'idle';

  // Dynamic border & glow depending on traffic heat
  let trafficBorderClass = colors.border;
  if (heatStatus === 'congested') {
    trafficBorderClass = 'border-rose-500 shadow-[0_0_22px_rgba(244,63,94,0.45)] ring-2 ring-rose-500/50 animate-pulse';
  } else if (heatStatus === 'busy') {
    trafficBorderClass = 'border-amber-400 shadow-[0_0_18px_rgba(251,191,36,0.35)] ring-1 ring-amber-400/40';
  } else if (inFlightCount > 0) {
    trafficBorderClass = 'border-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.35)] ring-1 ring-emerald-400/40';
  }

  return (
    <div
      className={`relative rounded-xl border transition-all duration-200 select-none shadow-xl min-w-[240px] max-w-[320px] bg-slate-950/90 backdrop-blur-md ${
        selected
          ? 'border-indigo-500 ring-2 ring-indigo-500/40 shadow-indigo-500/10'
          : `${trafficBorderClass} hover:border-slate-500/60`
      }`}
    >
      {/* Node Header */}
      <div className={`flex items-center justify-between p-3 border-b border-slate-800/80 rounded-t-xl ${colors.bg}`}>
        <div className="flex items-center gap-2 overflow-hidden pr-2">
          <div className={`p-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 ${colors.text} shrink-0`}>
            <IconComponent size={16} />
          </div>
          <div className="overflow-hidden">
            <div className="flex items-center gap-1.5">
              <h4 className="text-xs font-semibold text-slate-100 truncate tracking-wide">
                {data.title || metadata?.name || type}
              </h4>
              {inFlightCount > 0 && (
                <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/50 animate-pulse shrink-0">
                  🔥 {inFlightCount}
                </span>
              )}
            </div>
            <span className={`text-[9px] uppercase font-mono tracking-wider px-1.5 py-0.2 rounded border ${colors.badge}`}>
              {category}
            </span>
          </div>
        </div>

        {/* Action Controls & Status */}
        <div className="flex items-center gap-1 shrink-0">
          {status === 'running' && <Loader2 size={13} className="text-amber-400 animate-spin" />}
          {status === 'completed' && <CheckCircle2 size={13} className="text-emerald-400" />}
          {status === 'error' && <AlertCircle size={13} className="text-rose-400" />}

          {data.openConfigModal && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                data.openConfigModal?.();
              }}
              title="Cấu hình Node"
              className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 rounded transition-colors"
            >
              <Settings2 size={13} />
            </button>
          )}

          {data.onDuplicate && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                data.onDuplicate?.();
              }}
              title="Nhân bản Node"
              className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 rounded transition-colors"
            >
              <Copy size={13} />
            </button>
          )}

          {data.onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                data.onDelete?.();
              }}
              title="Xóa Node"
              className="p-1 text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 rounded transition-colors"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Inputs Handles */}
      {inputs.length > 0 && (
        <div className="py-2 px-3 border-b border-slate-800/40 space-y-1.5 bg-slate-950/40">
          {inputs.map((port, idx) => (
            <div key={`in_${port.name}_${idx}`} className="relative flex items-center justify-start group">
              <Handle
                type="target"
                position={Position.Left}
                id={port.name}
                className="!w-2.5 !h-2.5 !bg-indigo-400 !border-2 !border-slate-900 hover:!bg-indigo-300 transition-colors"
                style={{ top: '50%', transform: 'translateY(-50%)' }}
              />
              <span className="text-[10px] text-slate-400 font-mono pl-3 group-hover:text-slate-200 transition-colors">
                {port.label || port.name}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Outputs Handles */}
      {outputs.length > 0 && (
        <div className="py-2 px-3 border-b border-slate-800/40 space-y-1.5 bg-slate-950/40">
          {outputs.map((port, idx) => (
            <div key={`out_${port.name}_${idx}`} className="relative flex items-center justify-end group">
              <span className="text-[10px] text-slate-400 font-mono pr-3 group-hover:text-slate-200 transition-colors text-right">
                {port.label || port.name}
              </span>
              <Handle
                type="source"
                position={Position.Right}
                id={port.name}
                className="!w-2.5 !h-2.5 !bg-emerald-400 !border-2 !border-slate-900 hover:!bg-emerald-300 transition-colors"
                style={{ top: '50%', transform: 'translateY(-50%)' }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Node Body / Options Summary */}
      <div className="p-3 text-[11px] text-slate-300 space-y-2">
        <NodeBodyPreview type={type} data={data} />

        {data.executionTimeMs !== undefined && (
          <div className="text-[10px] text-right text-slate-500 font-mono pt-1">
            ⚡ {data.executionTimeMs} ms
          </div>
        )}

        {telemetry && (telemetry.total_completed > 0 || telemetry.in_flight > 0) && (
          <div className="pt-1.5 border-t border-slate-800/60 flex items-center justify-between text-[9px] font-mono text-slate-400">
            <span className="flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full ${inFlightCount > 0 ? 'bg-amber-400 animate-ping' : 'bg-emerald-400'}`} />
              {telemetry.total_completed} finished
            </span>
            <span className="text-slate-500">
              avg {telemetry.avg_duration_ms}ms
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
