import React from 'react';
import { CustomNodeData } from '../../../types/workflow';

interface Props {
  data: CustomNodeData;
}

export const PermissionGuardPreview: React.FC<Props> = ({ data }) => {
  return (
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
  );
};
