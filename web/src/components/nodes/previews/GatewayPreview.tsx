import React from 'react';
import { CustomNodeData } from '../../../types/workflow';
import { Network, Activity, Zap, ShieldAlert, Layers } from 'lucide-react';

interface Props {
  data: CustomNodeData;
}

export const GatewayPreview: React.FC<Props> = ({ data }) => {
  const cfg = data.config || {};
  const strategy = cfg.strategy || 'weighted_ab';
  const weightA = Number(cfg.route_a_weight ?? 80);
  const weightB = Number(cfg.route_b_weight ?? 20);
  const weightC = Number(cfg.route_c_weight ?? 0);
  const totalWeight = Math.max(1, weightA + weightB + weightC);
  const pctA = Math.round((weightA / totalWeight) * 100);
  const pctB = Math.round((weightB / totalWeight) * 100);

  const rps = cfg.rate_limit_rps || 10;
  const burst = cfg.rate_limit_burst || 20;

  return (
    <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex flex-col gap-1.5 text-[10px]">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 flex items-center gap-1">
          <Network size={11} className="text-cyan-400" />
          Gateway Strategy:
        </span>
        <span className="font-mono text-cyan-300 font-semibold uppercase text-[9px] bg-cyan-950/70 border border-cyan-800/50 px-1.5 py-0.5 rounded">
          {strategy.replace('_', ' ')}
        </span>
      </div>

      {strategy === 'weighted_ab' && (
        <div className="space-y-1 pt-0.5">
          <div className="flex justify-between text-[9px] text-slate-400 font-mono">
            <span className="text-indigo-300">Route A: {pctA}%</span>
            <span className="text-pink-300">Route B: {pctB}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden flex border border-slate-800/60">
            <div style={{ width: `${pctA}%` }} className="bg-indigo-500 h-full" />
            <div style={{ width: `${pctB}%` }} className="bg-pink-500 h-full" />
            {weightC > 0 && <div style={{ width: `${100 - pctA - pctB}%` }} className="bg-emerald-500 h-full" />}
          </div>
        </div>
      )}

      {strategy === 'rate_limiter' && (
        <div className="flex items-center justify-between text-slate-400 font-mono text-[9px] bg-slate-950/40 p-1 rounded border border-slate-800/50">
          <span className="flex items-center gap-1 text-amber-300">
            <Zap size={10} /> {rps} RPS
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-300">Burst: {burst} reqs</span>
        </div>
      )}

      {strategy === 'circuit_breaker' && (
        <div className="flex items-center justify-between text-slate-400 font-mono text-[9px]">
          <span className="flex items-center gap-1 text-rose-300">
            <ShieldAlert size={10} /> Threshold: {cfg.circuit_failure_threshold || 3} fails
          </span>
          <span className="text-slate-400">Cooldown: {cfg.circuit_recovery_seconds || 15}s</span>
        </div>
      )}

      {strategy === 'priority_tier' && (
        <div className="flex items-center justify-between text-slate-400 font-mono text-[9px]">
          <span className="flex items-center gap-1 text-purple-300">
            <Layers size={10} /> VIP → A | Pro → B | Free → C
          </span>
        </div>
      )}

      {strategy === 'round_robin' && (
        <div className="flex items-center justify-between text-slate-400 font-mono text-[9px]">
          <span className="flex items-center gap-1 text-emerald-300">
            <Activity size={10} /> Even Traffic Distribution (A/B/C)
          </span>
        </div>
      )}
    </div>
  );
};
