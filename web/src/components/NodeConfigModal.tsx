import React, { useState, useEffect } from 'react';
import { X, Check, Sliders, Plus, Trash2, GitBranch } from 'lucide-react';
import { NodeMetadata } from '../types/workflow';

interface NodeConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodeId: string | null;
  nodeTitle: string;
  nodeConfig: Record<string, any>;
  metadata?: NodeMetadata;
  onSave: (nodeId: string, newTitle: string, newConfig: Record<string, any>) => void;
}

export const NodeConfigModal: React.FC<NodeConfigModalProps> = ({
  isOpen,
  onClose,
  nodeId,
  nodeTitle,
  nodeConfig,
  metadata,
  onSave
}) => {
  const [title, setTitle] = useState(nodeTitle);
  const [config, setConfig] = useState<Record<string, any>>({});

  useEffect(() => {
    if (isOpen) {
      setTitle(nodeTitle);
      setConfig({ ...nodeConfig });
    }
  }, [isOpen, nodeTitle, nodeConfig]);

  if (!isOpen || !nodeId || !metadata) return null;

  const handleChange = (key: string, value: any) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    onSave(nodeId, title, config);
    onClose();
  };

  const schema = metadata.configSchema || {};
  const isRouter = metadata.type === 'router';

  // Router branch management
  const routerMode = config.mode || 'switch_case';
  const routerBranches: Array<{ id: string; name: string; operator: string; value: string }> =
    Array.isArray(config.branches) && config.branches.length > 0
      ? config.branches
      : [
          { id: 'branch_support', name: 'Support', operator: 'contains', value: 'giúp|hỗ trợ|support|help' },
          { id: 'branch_sales', name: 'Sales', operator: 'contains', value: 'mua|báo giá|tư vấn|order' }
        ];

  const handleAddBranch = () => {
    const nextIdx = routerBranches.length + 1;
    const newId = `branch_${Date.now().toString().slice(-4)}`;
    const newBranch = {
      id: newId,
      name: `Case ${nextIdx}`,
      operator: 'contains',
      value: ''
    };
    setConfig((prev) => ({
      ...prev,
      mode: 'switch_case',
      branches: [...routerBranches, newBranch]
    }));
  };

  const handleUpdateBranch = (idx: number, field: string, value: string) => {
    const updated = routerBranches.map((b, i) => (i === idx ? { ...b, [field]: value } : b));
    setConfig((prev) => ({
      ...prev,
      mode: 'switch_case',
      branches: updated
    }));
  };

  const handleDeleteBranch = (idx: number) => {
    if (routerBranches.length <= 1) return;
    const updated = routerBranches.filter((_, i) => i !== idx);
    setConfig((prev) => ({
      ...prev,
      mode: 'switch_case',
      branches: updated
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-[#0e121e] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
              <Sliders size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Configure {metadata.name}
              </h2>
              <p className="text-[11px] text-slate-400">Node ID: {nodeId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Custom Node Title */}
          <div>
            <label className="block text-slate-300 font-medium mb-1.5">Node Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Router Mode & Custom Branch Builder */}
          {isRouter && (
            <div className="space-y-4">
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Routing Architecture</label>
                <div className="grid grid-cols-2 gap-2 bg-slate-950 p-1 rounded-xl border border-slate-800">
                  <button
                    type="button"
                    onClick={() => handleChange('mode', 'switch_case')}
                    className={`py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                      routerMode === 'switch_case'
                        ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <GitBranch size={13} />
                    <span>Switch-Case (Multi-Branch)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChange('mode', 'if_else')}
                    className={`py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                      routerMode === 'if_else'
                        ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <span>Simple If / Else</span>
                  </button>
                </div>
              </div>

              {routerMode === 'switch_case' ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-slate-200">Branch Routes</span>
                      <p className="text-[10px] text-slate-500">Evaluates from top to bottom, first match wins.</p>
                    </div>
                    <button
                      type="button"
                      onClick={handleAddBranch}
                      className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 rounded-lg transition-colors"
                    >
                      <Plus size={13} />
                      <span>Add Branch</span>
                    </button>
                  </div>

                  <div className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
                    {routerBranches.map((b, idx) => (
                      <div
                        key={b.id || idx}
                        className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2.5 relative group"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-md bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-mono font-bold text-[10px]">
                              {idx + 1}
                            </span>
                            <input
                              type="text"
                              value={b.name}
                              placeholder="Branch Name (e.g. Support)"
                              onChange={(e) => handleUpdateBranch(idx, 'name', e.target.value)}
                              className="px-2 py-1 bg-slate-900 border border-slate-700/80 rounded-md text-slate-200 font-medium text-xs focus:outline-none focus:border-indigo-500"
                            />
                            <span className="text-[10px] font-mono text-slate-500">
                              Port: {b.id}
                            </span>
                          </div>

                          {routerBranches.length > 1 && (
                            <button
                              type="button"
                              onClick={() => handleDeleteBranch(idx)}
                              className="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 rounded transition-colors"
                              title="Delete Branch"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>

                        <div className="grid grid-cols-3 gap-2">
                          <div className="col-span-1">
                            <label className="text-[10px] text-slate-400 block mb-1">Operator</label>
                            <select
                              value={b.operator || 'contains'}
                              onChange={(e) => handleUpdateBranch(idx, 'operator', e.target.value)}
                              className="w-full px-2 py-1.5 bg-slate-900 border border-slate-700/80 rounded-md text-slate-300 text-[11px] focus:outline-none focus:border-indigo-500"
                            >
                              <option value="contains">Contains (chứa)</option>
                              <option value="not_contains">Not Contains</option>
                              <option value="equals">Equals (chính xác)</option>
                              <option value="starts_with">Starts With</option>
                              <option value="ends_with">Ends With</option>
                              <option value="regex">Regex Pattern</option>
                            </select>
                          </div>

                          <div className="col-span-2">
                            <label className="text-[10px] text-slate-400 block mb-1">Pattern (Keyword / Regex)</label>
                            <input
                              type="text"
                              value={b.value}
                              placeholder="e.g. mua|giá|báo giá"
                              onChange={(e) => handleUpdateBranch(idx, 'value', e.target.value)}
                              className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700/80 rounded-md text-slate-200 font-mono text-[11px] focus:outline-none focus:border-indigo-500"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Default / Fallback Branch */}
                  <div className="p-3 bg-slate-950/40 border border-slate-800/60 border-dashed rounded-xl flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-slate-300 text-xs">Default Fallback Branch</span>
                      <p className="text-[10px] text-slate-500">Activates if no case conditions match.</p>
                    </div>
                    <input
                      type="text"
                      value={config.default_label || 'Default / Else'}
                      onChange={(e) => handleChange('default_label', e.target.value)}
                      placeholder="Default / Else"
                      className="w-48 px-2.5 py-1.5 bg-slate-900 border border-slate-700/80 rounded-md text-slate-300 text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Evaluation Rule</label>
                    <select
                      value={config.rule_type || 'contains'}
                      onChange={(e) => handleChange('rule_type', e.target.value)}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="contains">Contains (chứa từ khóa, ngăn cách bởi |)</option>
                      <option value="starts_with">Starts With</option>
                      <option value="regex">Regex Match</option>
                      <option value="equals">Equals Exact</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Keyword / Pattern</label>
                    <input
                      type="text"
                      value={config.target_pattern ?? 'giúp|hỗ trợ|support|help'}
                      onChange={(e) => handleChange('target_pattern', e.target.value)}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-[11px]"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Dynamic Configuration Schema Fields for other nodes */}
          {!isRouter && Object.entries(schema).map(([fieldKey, fieldSchema]) => {
            const val = config[fieldKey] !== undefined ? config[fieldKey] : fieldSchema.default;

            return (
              <div key={fieldKey} className="space-y-1.5">
                <label className="block text-slate-300 font-medium">
                  {fieldSchema.label || fieldKey}
                </label>

                {fieldSchema.type === 'string' && (
                  <input
                    type="text"
                    value={val ?? ''}
                    onChange={(e) => handleChange(fieldKey, e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono text-[11px]"
                  />
                )}

                {fieldSchema.type === 'password' && (
                  <input
                    type="password"
                    value={val ?? ''}
                    placeholder="Enter API key or leave blank to use default/simulator"
                    onChange={(e) => handleChange(fieldKey, e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono text-[11px]"
                  />
                )}

                {fieldSchema.type === 'textarea' && (
                  <textarea
                    rows={6}
                    value={val ?? ''}
                    onChange={(e) => handleChange(fieldKey, e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono text-[11px] leading-relaxed resize-y"
                  />
                )}

                {fieldSchema.type === 'select' && (
                  <select
                    value={val ?? ''}
                    onChange={(e) => handleChange(fieldKey, e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    {fieldSchema.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                )}

                {fieldSchema.type === 'boolean' && (
                  <label className="relative inline-flex items-center cursor-pointer gap-2.5 py-1">
                    <input
                      type="checkbox"
                      checked={Boolean(val)}
                      onChange={(e) => handleChange(fieldKey, e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[6px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                    <span className="text-[11px] text-slate-300 font-mono select-none">
                      {Boolean(val) ? 'Bật (Enabled)' : 'Tắt (Disabled)'}
                    </span>
                  </label>
                )}

                {fieldSchema.type === 'number' && (
                  <div className="space-y-1">
                    {fieldSchema.min !== undefined && fieldSchema.max !== undefined && (
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={fieldSchema.min}
                          max={fieldSchema.max}
                          step={fieldSchema.step || 0.1}
                          value={val ?? 0}
                          onChange={(e) => handleChange(fieldKey, parseFloat(e.target.value))}
                          className="flex-1 accent-indigo-500"
                        />
                        <span className="w-12 text-center py-0.5 px-1 bg-slate-800 rounded font-mono text-indigo-300 font-semibold border border-slate-700">
                          {val}
                        </span>
                      </div>
                    )}
                    {!(fieldSchema.min !== undefined && fieldSchema.max !== undefined) && (
                      <input
                        type="number"
                        min={fieldSchema.min}
                        max={fieldSchema.max}
                        step={fieldSchema.step || 1}
                        value={val ?? 0}
                        onChange={(e) => handleChange(fieldKey, parseFloat(e.target.value))}
                        className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono text-[11px]"
                      />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-900/60 flex items-center justify-end gap-2.5">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-lg shadow-indigo-600/30 transition-all"
          >
            <Check size={14} />
            <span>Apply Changes</span>
          </button>
        </div>
      </div>
    </div>
  );
};
