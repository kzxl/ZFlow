import React from 'react';
import { CustomNodeData } from '../../../types/workflow';
import { Key, ShieldCheck, UserCheck, Lock } from 'lucide-react';

interface Props {
  data: CustomNodeData;
}

export const AuthPreview: React.FC<Props> = ({ data }) => {
  const cfg = data.config || {};
  const action = cfg.action || 'verify_bearer_token';
  const uname = cfg.default_username || 'staff';
  const expiry = cfg.token_expiry_seconds || 3600;

  return (
    <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex flex-col gap-1.5 text-[10px]">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 flex items-center gap-1">
          <Key size={11} className="text-amber-400" />
          Auth Action:
        </span>
        <span className="font-mono text-amber-300 font-semibold uppercase text-[9px] bg-amber-950/70 border border-amber-800/50 px-1.5 py-0.5 rounded">
          {action.replace(/_/g, ' ')}
        </span>
      </div>

      {action === 'login_issue_token' && (
        <div className="space-y-1 pt-0.5 font-mono text-[9px] text-slate-400">
          <div className="flex justify-between items-center bg-slate-950/40 p-1 rounded border border-slate-800/50">
            <span className="flex items-center gap-1 text-slate-300">
              <UserCheck size={10} className="text-emerald-400" /> User:
            </span>
            <span className="text-emerald-300 font-semibold">{uname}</span>
          </div>
          <div className="flex justify-between text-slate-500">
            <span>Expiry: {Math.round(expiry / 60)} mins</span>
            <span className="text-indigo-400">JWT (HS256)</span>
          </div>
        </div>
      )}

      {action === 'verify_bearer_token' && (
        <div className="space-y-1 pt-0.5 font-mono text-[9px] text-slate-400">
          <div className="flex items-center justify-between bg-slate-950/40 p-1 rounded border border-slate-800/50">
            <span className="flex items-center gap-1 text-slate-300">
              <Lock size={10} className="text-amber-400" /> Header:
            </span>
            <span className="text-amber-300 font-semibold truncate max-w-[120px]">Bearer &lt;token&gt;</span>
          </div>
          <div className="flex items-center justify-between text-slate-500">
            <span>Auto-bind Claims:</span>
            <span className="text-emerald-400">Role, Tier, Session</span>
          </div>
        </div>
      )}

      {action === 'mock_session_bind' && (
        <div className="flex items-center justify-between text-[9px] font-mono text-slate-400">
          <span className="flex items-center gap-1 text-purple-300">
            <ShieldCheck size={10} /> Local Dev Mock Active
          </span>
        </div>
      )}
    </div>
  );
};
