import React from 'react';
import { CustomNodeData } from '../../../types/workflow';

interface Props {
  data: CustomNodeData;
}

export const RouterPreview: React.FC<Props> = ({ data }) => {
  return (
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
  );
};
