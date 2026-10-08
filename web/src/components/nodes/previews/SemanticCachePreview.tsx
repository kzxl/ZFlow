import React from 'react';
import { CustomNodeData } from '../../../types/workflow';

interface Props {
  data: CustomNodeData;
}

export const SemanticCachePreview: React.FC<Props> = ({ data }) => {
  return (
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
  );
};
