import React from 'react';
import { Zap } from 'lucide-react';
import { CustomNodeData } from '../../../types/workflow';

interface Props {
  data: CustomNodeData;
}

export const System1Preview: React.FC<Props> = ({ data }) => {
  return (
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
  );
};
