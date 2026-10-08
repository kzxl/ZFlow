import React, { useRef } from 'react';
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
  Database
} from 'lucide-react';

interface HeaderProps {
  flowName: string;
  onFlowNameChange: (name: string) => void;
  onSave: () => void;
  onResetDefault: () => void;
  onLoadMemoryFlow?: () => void;
  onClear: () => void;
  onExport: () => void;
  onImport: (content: string) => void;
  onOpenApiModal: () => void;
  isChatOpen: boolean;
  onToggleChat: () => void;
  isSaving?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  flowName,
  onFlowNameChange,
  onSave,
  onResetDefault,
  onLoadMemoryFlow,
  onClear,
  onExport,
  onImport,
  onOpenApiModal,
  isChatOpen,
  onToggleChat,
  isSaving
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

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
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px]">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          FastAPI Engine Online
        </div>
      </div>

      {/* Toolbar Buttons */}
      <div className="flex items-center gap-2">
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

        <button
          onClick={onSave}
          disabled={isSaving}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg shadow-sm transition-colors"
        >
          <Save size={13} />
          <span>{isSaving ? 'Saving...' : 'Save Flow'}</span>
        </button>

        <button
          onClick={onOpenApiModal}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-cyan-300 hover:text-white bg-cyan-950/40 hover:bg-cyan-900/60 border border-cyan-800/60 rounded-lg shadow-sm transition-colors"
          title="View API Call Snippets & Webhook URL"
        >
          <Terminal size={13} />
          <span>API Trigger</span>
        </button>

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
