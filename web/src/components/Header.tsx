import React, { useRef, useState } from 'react';
import { 
  Play, 
  Save, 
  RotateCcw, 
  Download, 
  Upload, 
  Trash2, 
  MessageSquareCode, 
  CheckCircle, 
  Activity,
  Terminal,
  Database,
  FolderOpen,
  ChevronDown,
  Check,
  Plus,
  Settings,
  Flame,
  Radio
} from 'lucide-react';
import { WorkflowSummary, TelemetrySnapshot } from '../api/client';

interface HeaderProps {
  flowName: string;
  onFlowNameChange: (name: string) => void;
  currentFlowId: string;
  savedWorkflows?: WorkflowSummary[];
  onSelectWorkflow?: (flowId: string) => void;
  onNewWorkflow?: () => void;
  onSave: () => void;
  onSaveAs?: () => void;
  onResetDefault: () => void;
  onLoadMemoryFlow?: () => void;
  onClear: () => void;
  onExport: () => void;
  onImport: (content: string) => void;
  onOpenApiModal: () => void;
  onOpenSettings?: () => void;
  isChatOpen: boolean;
  onToggleChat: () => void;
  isSaving?: boolean;
  isSavedSuccess?: boolean;
  isTelemetryEnabled?: boolean;
  onToggleTelemetry?: () => void;
  onOpenTelemetryDrawer?: () => void;
  telemetrySnapshot?: TelemetrySnapshot | null;
}

export const Header: React.FC<HeaderProps> = ({
  flowName,
  onFlowNameChange,
  currentFlowId,
  savedWorkflows = [],
  onSelectWorkflow,
  onNewWorkflow,
  onSave,
  onSaveAs,
  onResetDefault,
  onLoadMemoryFlow,
  onClear,
  onExport,
  onImport,
  onOpenApiModal,
  onOpenSettings,
  isChatOpen,
  onToggleChat,
  isSaving,
  isSavedSuccess,
  isTelemetryEnabled = true,
  onToggleTelemetry,
  onOpenTelemetryDrawer,
  telemetrySnapshot
}) => {
  const [isFlowDropdownOpen, setIsFlowDropdownOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const totalInFlight = telemetrySnapshot?.total_in_flight || 0;
  const currentRps = telemetrySnapshot?.current_rps || 0;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target?.result as string;
        if (text) onImport(text);
      };
      reader.readAsText(file);
    }
  };

  return (
    <header className="h-14 bg-[#090c14] border-b border-slate-800/80 px-4 flex items-center justify-between select-none z-20">
      {/* Title & Status */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={flowName}
          onChange={(e) => onFlowNameChange(e.target.value)}
          className="bg-transparent hover:bg-slate-900 focus:bg-slate-900 border border-transparent hover:border-slate-800 focus:border-indigo-500 rounded px-2 py-1 text-sm font-semibold text-slate-100 focus:outline-none transition-colors"
          title="Click to rename workflow"
        />

        {/* Saved Workflows Selector */}
        <div className="relative">
          <button
            onClick={() => setIsFlowDropdownOpen(!isFlowDropdownOpen)}
            className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-[11px] text-slate-300 font-mono transition-colors"
            title="Danh sách workflow đã lưu"
          >
            <FolderOpen size={12} className="text-amber-400" />
            <span className="max-w-[130px] truncate">#{currentFlowId}</span>
            <ChevronDown size={11} className={`text-slate-400 transition-transform ${isFlowDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {isFlowDropdownOpen && (
            <div className="absolute left-0 mt-1.5 w-64 bg-slate-950 border border-slate-800 rounded-xl shadow-2xl p-1.5 z-50 text-xs animate-in fade-in duration-100">
              <div className="flex items-center justify-between px-2 py-1 border-b border-slate-800 text-[10px] text-slate-500 font-semibold uppercase">
                <span>Workflow lưu trữ ({savedWorkflows.length})</span>
                {onNewWorkflow && (
                  <button
                    onClick={() => {
                      onNewWorkflow();
                      setIsFlowDropdownOpen(false);
                    }}
                    className="text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5"
                  >
                    <Plus size={10} /> Mới
                  </button>
                )}
              </div>
              <div className="max-h-56 overflow-y-auto mt-1 space-y-0.5">
                {savedWorkflows.map((w) => (
                  <div
                    key={w.id}
                    onClick={() => {
                      onSelectWorkflow?.(w.id);
                      setIsFlowDropdownOpen(false);
                    }}
                    className={`px-2.5 py-1.5 rounded-lg cursor-pointer flex items-center justify-between transition-colors ${
                      w.id === currentFlowId
                        ? 'bg-indigo-600/20 text-indigo-300 font-medium'
                        : 'text-slate-300 hover:bg-slate-900 hover:text-white'
                    }`}
                  >
                    <div className="overflow-hidden pr-2">
                      <div className="truncate font-semibold">{w.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono truncate">#{w.id}</div>
                    </div>
                    <span className="text-[10px] text-slate-500 shrink-0 font-mono">
                      {w.node_count} nodes
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px]">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          FastAPI Engine
        </div>
      </div>

      {/* Toolbar Buttons */}
      <div className="flex items-center gap-2">
        {/* Live Telemetry Radar HUD */}
        {onOpenTelemetryDrawer && (
          <div className="flex items-center rounded-lg bg-slate-900/80 border border-slate-800 p-0.5 text-xs shadow-sm">
            <button
              onClick={onOpenTelemetryDrawer}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all ${
                isTelemetryEnabled
                  ? totalInFlight > 0
                    ? 'bg-amber-950/70 border border-amber-500/50 text-amber-300 shadow-[0_0_12px_rgba(251,191,36,0.3)]'
                    : 'bg-emerald-950/60 border border-emerald-500/40 text-emerald-300'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Mở bảng điều khiển kiểm toán Concurrency & Latency Heatmap"
            >
              <Activity
                size={13}
                className={isTelemetryEnabled ? (totalInFlight > 0 ? 'text-amber-400 animate-spin' : 'text-emerald-400 animate-pulse') : 'text-slate-500'}
              />
              <span className="font-semibold text-[11px]">
                {isTelemetryEnabled ? (
                  totalInFlight > 0 ? (
                    <span className="flex items-center gap-1 font-mono">
                      <Flame size={11} className="text-amber-400" />
                      {totalInFlight} active • {currentRps} rps
                    </span>
                  ) : (
                    <span>Live Traffic</span>
                  )
                ) : (
                  <span>Radar Tắt</span>
                )}
              </span>
            </button>

            {onToggleTelemetry && (
              <button
                onClick={onToggleTelemetry}
                className={`p-1.5 rounded-md hover:bg-slate-800 transition-colors ${
                  isTelemetryEnabled ? 'text-emerald-400' : 'text-slate-600'
                }`}
                title={isTelemetryEnabled ? "Tạm dừng live stream telemetry" : "Bật live stream telemetry"}
              >
                <Radio size={12} className={isTelemetryEnabled ? "animate-pulse" : ""} />
              </button>
            )}
          </div>
        )}

        <button
          onClick={onResetDefault}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors"
          title="Reload starter template"
        >
          <RotateCcw size={13} />
          <span>Starter Flow</span>
        </button>

        {onLoadMemoryFlow && (
          <button
            onClick={onLoadMemoryFlow}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-purple-300 hover:text-white bg-purple-950/40 hover:bg-purple-900/60 border border-purple-800/50 rounded-lg transition-colors"
            title="Nạp mẫu workflow có bộ nhớ hội thoại SQLite"
          >
            <Database size={13} className="text-purple-400" />
            <span>Memory Flow</span>
          </button>
        )}

        <button
          onClick={onClear}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-400 hover:text-rose-400 bg-slate-900 hover:bg-rose-950/20 border border-slate-800 hover:border-rose-900/50 rounded-lg transition-colors"
          title="Clear canvas"
        >
          <Trash2 size={13} />
        </button>

        <div className="h-4 w-px bg-slate-800 mx-1"></div>

        <button
          onClick={onExport}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors"
          title="Export Workflow JSON"
        >
          <Download size={13} />
          <span>Export</span>
        </button>

        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors"
          title="Import Workflow JSON"
        >
          <Upload size={13} />
          <span>Import</span>
        </button>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".json"
          className="hidden"
        />

        {/* Save Actions */}
        <button
          onClick={onSave}
          disabled={isSaving}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg shadow-sm transition-all ${
            isSavedSuccess
              ? 'bg-emerald-600 text-white shadow-emerald-600/30 ring-1 ring-emerald-400'
              : 'text-white bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/30'
          }`}
          title="Lưu workflow hiện tại vào hệ thống"
        >
          {isSavedSuccess ? <Check size={13} /> : <Save size={13} />}
          <span>{isSaving ? 'Đang lưu...' : isSavedSuccess ? 'Đã lưu!' : 'Lưu Flow'}</span>
        </button>

        {onSaveAs && (
          <button
            onClick={onSaveAs}
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors"
            title="Lưu thành bản sao mới (Save As)"
          >
            <span>Lưu mới...</span>
          </button>
        )}

        <button
          onClick={onOpenApiModal}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-cyan-300 hover:text-white bg-cyan-950/40 hover:bg-cyan-900/60 border border-cyan-800/60 rounded-lg shadow-sm transition-colors"
          title="View API Call Snippets & Webhook URL"
        >
          <Terminal size={13} />
          <span>API Trigger</span>
        </button>

        {onOpenSettings && (
          <button
            onClick={onOpenSettings}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg shadow-sm transition-colors"
            title="Cài đặt hệ thống, API Keys và Active Flow"
          >
            <Settings size={13} className="text-indigo-400" />
            <span>Cài đặt</span>
          </button>
        )}

        <div className="h-4 w-px bg-slate-800 mx-1"></div>

        {/* Live Chat Drawer Toggle */}
        <button
          onClick={onToggleChat}
          className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg shadow-lg transition-all duration-150 ${
            isChatOpen
              ? 'bg-indigo-600 text-white shadow-indigo-600/30 ring-2 ring-indigo-400'
              : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-indigo-500/25'
          }`}
        >
          <MessageSquareCode size={14} />
          <span>Live Chat Simulator</span>
        </button>
      </div>
    </header>
  );
};
