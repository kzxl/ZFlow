import React, { useState, useEffect } from 'react';
import { X, Check, Sliders } from 'lucide-react';
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

          {/* Dynamic Configuration Schema Fields */}
          {Object.entries(schema).map(([fieldKey, fieldSchema]) => {
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
                    rows={4}
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

                {fieldSchema.type === 'number' && (
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
