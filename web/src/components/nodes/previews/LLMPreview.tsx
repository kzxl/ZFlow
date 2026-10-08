import React from 'react';
import { CustomNodeData } from '../../../types/workflow';

interface Props {
  data: CustomNodeData;
}

export const LLMPreview: React.FC<Props> = ({ data }) => {
  return (
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
  );
};
