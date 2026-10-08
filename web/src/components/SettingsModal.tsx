import React, { useState, useEffect } from 'react';
import { 
  X, 
  Settings2, 
  Key, 
  Globe, 
  Zap, 
  Check, 
  Sliders, 
  Cpu, 
  Server, 
  Database, 
  Trash2, 
  RefreshCw, 
  ShieldCheck,
  Radio,
  ExternalLink
} from 'lucide-react';
import { WorkflowSummary } from '../api/client';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  savedWorkflows?: WorkflowSummary[];
  onActiveFlowChanged?: (newActiveId: string) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  savedWorkflows = [],
  onActiveFlowChanged
}) => {
  const [activeTab, setActiveTab] = useState<'providers' | 'routing' | 'engine' | 'maintenance'>('providers');
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [cacheMessage, setCacheMessage] = useState('');

  const currentHost = window.location.origin.includes('5173')
    ? 'http://127.0.0.1:8000'
    : window.location.origin;

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${currentHost}/api/settings`);
      const data = await res.json();
      if (data && data.settings) {
        setSettings(data.settings);
      }
    } catch (e) {
      console.error('Failed to load settings:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveSuccess(false);
    try {
      const res = await fetch(`${currentHost}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings })
      });
      if (res.ok) {
        setSaveSuccess(true);
        if (settings.active_flow_id && onActiveFlowChanged) {
          onActiveFlowChanged(settings.active_flow_id);
        }
        setTimeout(() => setSaveSuccess(false), 2500);
      }
    } catch (e) {
      console.error('Failed to save settings:', e);
    } finally {
      setSaving(false);
    }
  };

  const handleClearCache = async () => {
    if (!window.confirm('Bạn có chắc muốn xóa toàn bộ bộ nhớ Semantic Cache (<0.1ms) không?')) return;
    try {
      const res = await fetch(`${currentHost}/api/settings/clear-cache`, { method: 'POST' });
      if (res.ok) {
        setCacheMessage('Đã dọn dẹp sạch toàn bộ cache!');
        setTimeout(() => setCacheMessage(''), 3000);
      }
    } catch (e) {
      console.error('Failed to clear cache:', e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-3xl bg-[#0b0e17] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/20">
              <Settings2 size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                Cài Đặt Hệ Thống ZFlow
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                  Sovereign Studio
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Quản lý API Keys toàn cục, định tuyến Active Workflow, ComfyUI và tinh chỉnh Engine
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800/80 bg-slate-950/50 px-6 gap-2 pt-2">
          <button
            onClick={() => setActiveTab('providers')}
            className={`flex items-center gap-2 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'providers'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Key size={13} />
            <span>AI Providers & Keys</span>
          </button>

          <button
            onClick={() => setActiveTab('routing')}
            className={`flex items-center gap-2 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'routing'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Radio size={13} />
            <span>Active Workflow & Route</span>
          </button>

          <button
            onClick={() => setActiveTab('engine')}
            className={`flex items-center gap-2 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'engine'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sliders size={13} />
            <span>Engine & RAG Tuning</span>
          </button>

          <button
            onClick={() => setActiveTab('maintenance')}
            className={`flex items-center gap-2 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'maintenance'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database size={13} />
            <span>Database & Cache</span>
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 text-xs text-slate-300">
          {loading ? (
            <div className="py-12 text-center text-slate-500">Đang tải cấu hình hệ thống...</div>
          ) : (
            <>
              {/* TAB 1: AI Providers & Keys */}
              {activeTab === 'providers' && (
                <div className="space-y-4">
                  <div className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/20 text-slate-400 text-[11px] leading-relaxed">
                    💡 **Mẹo:** Các API Key nhập tại đây sẽ được chia sẻ toàn cục cho tất cả các Node (LLM, ImageGen, Vision) trong mọi workflow nếu Node đó không cấu hình API Key riêng.
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-300 flex items-center justify-between">
                        <span>OpenAI API Key:</span>
                        <span className="text-[10px] text-slate-500 font-mono">sk-...</span>
                      </label>
                      <input
                        type="password"
                        placeholder="sk-proj-..."
                        value={settings.openai_api_key || ''}
                        onChange={(e) => setSettings({ ...settings, openai_api_key: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-300 flex items-center justify-between">
                        <span>Google Gemini API Key:</span>
                        <span className="text-[10px] text-slate-500 font-mono">AIzaSy...</span>
                      </label>
                      <input
                        type="password"
                        placeholder="AIzaSy..."
                        value={settings.gemini_api_key || ''}
                        onChange={(e) => setSettings({ ...settings, gemini_api_key: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-300 flex items-center justify-between">
                        <span>DeepSeek API Key:</span>
                        <span className="text-[10px] text-slate-500 font-mono">sk-...</span>
                      </label>
                      <input
                        type="password"
                        placeholder="sk-..."
                        value={settings.deepseek_api_key || ''}
                        onChange={(e) => setSettings({ ...settings, deepseek_api_key: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-300 flex items-center justify-between">
                        <span>Anthropic Claude API Key:</span>
                        <span className="text-[10px] text-slate-500 font-mono">sk-ant-...</span>
                      </label>
                      <input
                        type="password"
                        placeholder="sk-ant-..."
                        value={settings.claude_api_key || ''}
                        onChange={(e) => setSettings({ ...settings, claude_api_key: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="border-t border-slate-800/80 pt-4 space-y-3">
                    <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                      <Server size={14} className="text-amber-400" />
                      Máy Chủ LLM & Tạo Ảnh Cục Bộ (Sovereign Local Engines)
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-semibold text-slate-300">
                          Ollama Host URL:
                        </label>
                        <input
                          type="text"
                          placeholder="http://localhost:11434"
                          value={settings.ollama_base_url || 'http://localhost:11434'}
                          onChange={(e) => setSettings({ ...settings, ollama_base_url: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[11px] font-semibold text-slate-300">
                          ComfyUI Host URL:
                        </label>
                        <input
                          type="text"
                          placeholder="http://127.0.0.1:8188"
                          value={settings.comfyui_base_url || 'http://127.0.0.1:8188'}
                          onChange={(e) => setSettings({ ...settings, comfyui_base_url: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: Active Workflow & Dynamic Route */}
              {activeTab === 'routing' && (
                <div className="space-y-4">
                  <div className="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-500/20 space-y-2">
                    <div className="flex items-center gap-2 text-cyan-300 font-semibold text-xs">
                      <Radio size={14} className="animate-pulse" />
                      Định Tuyến Động Active Workflow (Smart Routing)
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Khi các ứng dụng bên ngoài (Discord Bot, Telegram Bot, CRM, Webhook) gọi vào endpoint
                      <code className="mx-1 px-1.5 py-0.5 rounded bg-black/60 text-cyan-300 font-mono text-[10px]">
                        /api/v1/flows/active/run
                      </code>
                      hoặc
                      <code className="mx-1 px-1.5 py-0.5 rounded bg-black/60 text-cyan-300 font-mono text-[10px]">
                        /api/v1/flows/active/stream
                      </code>, ZFlow sẽ tự động chuyển tiếp input vào Workflow được chọn dưới đây và trích xuất đúng toàn bộ output fields!
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-200">
                      Chọn Workflow Đang Kích Hoạt (Active Workflow):
                    </label>
                    <select
                      value={settings.active_flow_id || 'intelligent_enterprise_chatbot_flow'}
                      onChange={(e) => setSettings({ ...settings, active_flow_id: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2.5 text-xs text-slate-100 focus:outline-none font-mono"
                    >
                      {savedWorkflows.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.name} (#{w.id}) — {w.node_count} nodes
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 space-y-2">
                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Endpoints Công Khai Của Active Workflow:
                    </div>
                    <div className="space-y-1 font-mono text-[11px]">
                      <div className="flex items-center justify-between p-2 rounded bg-black/40 border border-slate-800">
                        <span className="text-emerald-400 font-bold">POST</span>
                        <span className="text-slate-300">{currentHost}/api/v1/flows/active/run</span>
                        <span className="text-[10px] text-slate-500">Sync Batch</span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded bg-black/40 border border-slate-800">
                        <span className="text-cyan-400 font-bold">POST</span>
                        <span className="text-slate-300">{currentHost}/api/v1/flows/active/stream</span>
                        <span className="text-[10px] text-slate-500">Real-time SSE</span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded bg-black/40 border border-slate-800">
                        <span className="text-blue-400 font-bold">GET</span>
                        <span className="text-slate-300">{currentHost}/api/v1/flows/active/schema</span>
                        <span className="text-[10px] text-slate-500">I/O Schema</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: Engine & RAG Tuning */}
              {activeTab === 'engine' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-300">
                        Mô hình LLM Mặc định:
                      </label>
                      <input
                        type="text"
                        placeholder="gpt-4o-mini"
                        value={settings.default_model || 'gpt-4o-mini'}
                        onChange={(e) => setSettings({ ...settings, default_model: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-300">
                        Nhiệt độ Mặc định (Temperature):
                      </label>
                      <input
                        type="number"
                        step="0.05"
                        min="0"
                        max="2"
                        value={settings.default_temperature ?? 0.7}
                        onChange={(e) => setSettings({ ...settings, default_temperature: parseFloat(e.target.value) })}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-300">
                        Kích thước Cửa sổ Bộ nhớ (Turns):
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="50"
                        value={settings.memory_window_size ?? 6}
                        onChange={(e) => setSettings({ ...settings, memory_window_size: parseInt(e.target.value, 10) })}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-slate-300">
                        RAG Top-K Tài Liệu Mặc Định:
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="20"
                        value={settings.rag_top_k ?? 3}
                        onChange={(e) => setSettings({ ...settings, rag_top_k: parseInt(e.target.value, 10) })}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-slate-200">Kích hoạt 2-Tier Semantic Cache</div>
                      <div className="text-[10px] text-slate-400">Phản hồi các câu hỏi tương đồng &lt; 0.1ms và zero token cost</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.enable_semantic_cache !== false}
                      onChange={(e) => setSettings({ ...settings, enable_semantic_cache: e.target.checked })}
                      className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-950 border-slate-700"
                    />
                  </div>
                </div>
              )}

              {/* TAB 4: Maintenance */}
              {activeTab === 'maintenance' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs font-semibold text-slate-200">Xóa Bộ Nhớ Semantic Cache</div>
                        <div className="text-[10px] text-slate-400">
                          Xóa toàn bộ các bản ghi băm SHA256 và câu trả lời đã lưu trong `semantic_cache.db`.
                        </div>
                      </div>
                      <button
                        onClick={handleClearCache}
                        className="px-3 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      >
                        <Trash2 size={13} />
                        <span>Wipe Cache</span>
                      </button>
                    </div>
                    {cacheMessage && (
                      <div className="p-2 rounded bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-[11px] font-medium animate-in fade-in">
                        {cacheMessage}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800/80 bg-slate-950 flex items-center justify-between">
          <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-emerald-400" />
            <span>Dữ liệu lưu an toàn tại server/storage/settings.json</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors"
            >
              Đóng
            </button>

            <button
              onClick={handleSave}
              disabled={saving}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold shadow-md transition-all ${
                saveSuccess
                  ? 'bg-emerald-600 text-white ring-2 ring-emerald-400'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30'
              }`}
            >
              {saveSuccess ? <Check size={14} /> : <Zap size={14} />}
              <span>{saving ? 'Đang lưu...' : saveSuccess ? 'Đã lưu cấu hình!' : 'Lưu Thay Đổi'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
