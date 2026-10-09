import React from 'react';
import { 
  X, 
  Activity, 
  Flame, 
  Clock, 
  Zap, 
  AlertTriangle, 
  RotateCcw, 
  CheckCircle2, 
  User, 
  Cpu
} from 'lucide-react';
import { TelemetrySnapshot, resetTelemetry } from '../api/client';

interface TelemetryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  snapshot: TelemetrySnapshot | null;
  onReset: () => void;
}

export const TelemetryDrawer: React.FC<TelemetryDrawerProps> = ({
  isOpen,
  onClose,
  snapshot,
  onReset
}) => {
  if (!isOpen) return null;

  const totalInFlight = snapshot?.total_in_flight || 0;
  const currentRps = snapshot?.current_rps || 0;
  const p95Latency = snapshot?.p95_latency_ms || 0;
  const errorRate = snapshot?.error_rate_pct || 0;
  const activeRequests = snapshot?.active_requests || [];
  const nodes = snapshot?.nodes || {};

  const handleReset = async () => {
    try {
      await resetTelemetry();
      onReset();
    } catch (e) {
      console.error('Failed to reset telemetry', e);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-[420px] bg-[#090b12] border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="h-14 px-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-400">
            <Activity size={16} className="animate-pulse" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
              Live Traffic & Observability
            </h3>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping inline-block" />
              Streaming telemetry (350ms frame)
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleReset}
            title="Reset telemetry counters"
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <RotateCcw size={14} />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* KPI Metric Grid */}
      <div className="p-4 grid grid-cols-2 gap-2.5 border-b border-slate-800/60 bg-slate-950/30">
        {/* Concurrency */}
        <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>In-Flight Requests</span>
            <Flame size={12} className={totalInFlight > 0 ? "text-amber-400 animate-bounce" : "text-slate-500"} />
          </div>
          <div className="mt-1 text-xl font-mono font-bold text-slate-100 flex items-baseline gap-1">
            <span>{totalInFlight}</span>
            <span className="text-[9px] font-normal text-slate-500">active</span>
          </div>
        </div>

        {/* Throughput */}
        <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>Sliding Throughput</span>
            <Zap size={12} className="text-cyan-400" />
          </div>
          <div className="mt-1 text-xl font-mono font-bold text-slate-100 flex items-baseline gap-1">
            <span>{currentRps}</span>
            <span className="text-[9px] font-normal text-slate-500">RPS (5s)</span>
          </div>
        </div>

        {/* P95 Latency */}
        <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>P95 Duration</span>
            <Clock size={12} className="text-indigo-400" />
          </div>
          <div className="mt-1 text-xl font-mono font-bold text-slate-100 flex items-baseline gap-1">
            <span>{p95Latency}</span>
            <span className="text-[9px] font-normal text-slate-500">ms</span>
          </div>
        </div>

        {/* Error Rate */}
        <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>Error Rate</span>
            <AlertTriangle size={12} className={errorRate > 0 ? "text-rose-400" : "text-emerald-500"} />
          </div>
          <div className="mt-1 text-xl font-mono font-bold text-slate-100 flex items-baseline gap-1">
            <span>{errorRate}</span>
            <span className="text-[9px] font-normal text-slate-500">%</span>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Active Requests List */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Cpu size={13} className="text-indigo-400" />
              <span>In-Flight Requests ({activeRequests.length})</span>
            </h4>
          </div>

          {activeRequests.length === 0 ? (
            <div className="p-4 rounded-xl border border-dashed border-slate-800/80 text-center text-slate-500 text-xs">
              Chưa có request đang chạy. Gửi tin nhắn hoặc gọi API để quan sát lưu lượng.
            </div>
          ) : (
            <div className="space-y-1.5">
              {activeRequests.map((req) => (
                <div
                  key={req.session_id}
                  className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors text-xs font-mono space-y-1"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-cyan-400 font-semibold truncate max-w-[200px]" title={req.session_id}>
                      {req.session_id}
                    </span>
                    <span className="text-amber-400 font-bold text-[10px] bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-800/60">
                      ⏱ {req.elapsed_seconds}s
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <User size={10} className="text-slate-500" />
                      {req.user_id}
                    </span>
                    <span className="text-slate-300 bg-slate-800/80 px-1.5 py-0.2 rounded">
                      Node: <span className="text-indigo-300">{req.current_node_id || 'Starting'}</span>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Node Heatmap Summary */}
        <div>
          <h4 className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Activity size={13} className="text-emerald-400" />
            <span>Node Heatmap & Latency</span>
          </h4>

          {Object.keys(nodes).length === 0 ? (
            <div className="p-4 rounded-xl border border-dashed border-slate-800/80 text-center text-slate-500 text-xs">
              Chưa có dữ liệu nodes.
            </div>
          ) : (
            <div className="space-y-1.5">
              {Object.values(nodes).map((n) => {
                const heatColor = 
                  n.heat_status === 'congested' ? 'border-rose-500/80 text-rose-300 bg-rose-950/40' :
                  n.heat_status === 'busy' ? 'border-amber-500/80 text-amber-300 bg-amber-950/40' :
                  n.heat_status === 'normal' && n.in_flight > 0 ? 'border-emerald-500/80 text-emerald-300 bg-emerald-950/40' :
                  'border-slate-800 text-slate-300 bg-slate-900/60';

                return (
                  <div
                    key={n.node_id}
                    className={`p-2.5 rounded-lg border text-xs font-mono flex items-center justify-between ${heatColor}`}
                  >
                    <div className="space-y-0.5">
                      <div className="font-semibold text-[11px] truncate max-w-[190px]" title={n.node_id}>
                        {n.node_id}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {n.total_completed} finished • avg {n.avg_duration_ms}ms
                      </div>
                    </div>

                    <div className="text-right">
                      {n.in_flight > 0 ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                          🔥 {n.in_flight} active
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500">idle</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
