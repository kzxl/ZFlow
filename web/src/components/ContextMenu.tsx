import React, { useState, useEffect, useRef } from 'react';
import {
  Plus,
  Settings2,
  Copy,
  ClipboardCopy,
  Clipboard,
  Trash2,
  Maximize2,
  CheckSquare,
  ChevronRight,
  Search,
  MessageSquare,
  FileText,
  Sparkles,
  GitBranch,
  Wrench,
  Database,
  Send,
  Code2,
  Globe,
  CornerDownRight,
  Layers
} from 'lucide-react';
import { ContextMenuState, NodeMetadata } from '../types/workflow';

const ICONS: Record<string, React.ElementType> = {
  MessageSquare,
  FileText,
  Sparkles,
  GitBranch,
  Wrench,
  Database,
  Send,
  Code2,
  Globe
};

const CATEGORY_COLORS: Record<string, { badge: string; text: string; dot: string }> = {
  input: { badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  prompt: { badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30', text: 'text-amber-400', dot: 'bg-amber-400' },
  llm: { badge: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30', text: 'text-indigo-400', dot: 'bg-indigo-400' },
  logic: { badge: 'bg-rose-500/15 text-rose-400 border-rose-500/30', text: 'text-rose-400', dot: 'bg-rose-400' },
  tool: { badge: 'bg-blue-500/15 text-blue-400 border-blue-500/30', text: 'text-blue-400', dot: 'bg-blue-400' },
  memory: { badge: 'bg-purple-500/15 text-purple-400 border-purple-500/30', text: 'text-purple-400', dot: 'bg-purple-400' },
  output: { badge: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30', text: 'text-cyan-400', dot: 'bg-cyan-400' },
  general: { badge: 'bg-slate-700/30 text-slate-300 border-slate-700/50', text: 'text-slate-300', dot: 'bg-slate-400' }
};

interface ContextMenuProps {
  state: ContextMenuState;
  nodeDefs: NodeMetadata[];
  onClose: () => void;
  onAddNode: (type: string, position?: { x: number; y: number }) => void;
  onConfigureNode: (nodeId: string, title: string, type: string, config: any) => void;
  onDuplicateNode: (nodeId: string) => void;
  onDeleteNode: (nodeId: string) => void;
  onDeleteEdge: (edgeId: string) => void;
  onFitView: () => void;
  onSelectAll: () => void;
  onClearCanvas: () => void;
  onCopyNode: (nodeId: string) => void;
  onPasteNode: (position?: { x: number; y: number }) => void;
  hasClipboard: boolean;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({
  state,
  nodeDefs,
  onClose,
  onAddNode,
  onConfigureNode,
  onDuplicateNode,
  onDeleteNode,
  onDeleteEdge,
  onFitView,
  onSelectAll,
  onClearCanvas,
  onCopyNode,
  onPasteNode,
  hasClipboard
}) => {
  const [isAddSubmenuOpen, setIsAddSubmenuOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close when clicking outside or pressing Escape
  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  // Focus search input when submenu opens
  useEffect(() => {
    if (isAddSubmenuOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isAddSubmenuOpen]);

  if (!state.isOpen) return null;

  // Viewport bounds clamping
  const menuWidth = 220;
  const menuHeight = state.type === 'node' ? 240 : state.type === 'edge' ? 120 : 260;
  const clampedX = Math.max(10, Math.min(state.x, window.innerWidth - menuWidth - 15));
  const clampedY = Math.max(10, Math.min(state.y, window.innerHeight - menuHeight - 15));

  // Determine if submenu should open to left or right
  const openSubmenuToLeft = clampedX + menuWidth + 260 > window.innerWidth;

  const filteredNodes = nodeDefs.filter((n) =>
    n.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    n.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
    n.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div
      ref={menuRef}
      style={{ top: `${clampedY}px`, left: `${clampedX}px` }}
      className="fixed z-50 min-w-[210px] rounded-xl border border-slate-800/90 bg-[#0d111c]/95 p-1.5 shadow-[0_12px_40px_rgba(0,0,0,0.65)] backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100 select-none text-xs text-slate-200"
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* Node Context Menu */}
      {state.type === 'node' && state.nodeData && (
        <div className="flex flex-col gap-0.5">
          {/* Header Info */}
          <div className="px-2.5 py-1.5 mb-1 rounded-lg bg-slate-900/80 border border-slate-800/80 flex items-center justify-between">
            <span className="font-semibold text-slate-200 truncate max-w-[130px]">
              {state.nodeData.title}
            </span>
            <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
              {state.nodeData.type}
            </span>
          </div>

          <button
            onClick={() => {
              if (state.nodeData) {
                onConfigureNode(
                  state.nodeData.id,
                  state.nodeData.title,
                  state.nodeData.type,
                  state.nodeData.config
                );
              }
              onClose();
            }}
            className="flex items-center justify-between w-full px-2.5 py-2 rounded-lg hover:bg-indigo-600/20 hover:text-indigo-300 transition-colors text-slate-300 text-left"
          >
            <div className="flex items-center gap-2">
              <Settings2 size={14} className="text-indigo-400" />
              <span>Configure Node</span>
            </div>
            <span className="text-[10px] text-slate-500">2x Click</span>
          </button>

          <button
            onClick={() => {
              if (state.nodeData) {
                onDuplicateNode(state.nodeData.id);
              }
              onClose();
            }}
            className="flex items-center justify-between w-full px-2.5 py-2 rounded-lg hover:bg-slate-800 hover:text-white transition-colors text-slate-300 text-left"
          >
            <div className="flex items-center gap-2">
              <Copy size={14} className="text-slate-400" />
              <span>Duplicate</span>
            </div>
            <span className="text-[10px] text-slate-500">Ctrl+D</span>
          </button>

          <button
            onClick={() => {
              if (state.nodeData) {
                onCopyNode(state.nodeData.id);
              }
              onClose();
            }}
            className="flex items-center justify-between w-full px-2.5 py-2 rounded-lg hover:bg-slate-800 hover:text-white transition-colors text-slate-300 text-left"
          >
            <div className="flex items-center gap-2">
              <ClipboardCopy size={14} className="text-slate-400" />
              <span>Copy</span>
            </div>
            <span className="text-[10px] text-slate-500">Ctrl+C</span>
          </button>

          <div className="my-1 border-t border-slate-800/80" />

          <button
            onClick={() => {
              if (state.nodeData) {
                onDeleteNode(state.nodeData.id);
              }
              onClose();
            }}
            className="flex items-center justify-between w-full px-2.5 py-2 rounded-lg hover:bg-rose-950/40 hover:text-rose-300 transition-colors text-rose-400 text-left"
          >
            <div className="flex items-center gap-2">
              <Trash2 size={14} />
              <span>Delete Node</span>
            </div>
            <span className="text-[10px] text-rose-500/70">Del</span>
          </button>
        </div>
      )}

      {/* Edge Context Menu */}
      {state.type === 'edge' && state.edgeData && (
        <div className="flex flex-col gap-0.5">
          <div className="px-2.5 py-1.5 mb-1 rounded-lg bg-slate-900/80 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Connection</span>
            <div className="flex items-center gap-1 font-mono text-[10px] text-slate-300 truncate">
              <span>{state.edgeData.source}</span>
              <CornerDownRight size={10} className="text-indigo-400 shrink-0" />
              <span>{state.edgeData.target}</span>
            </div>
          </div>

          <button
            onClick={() => {
              if (state.edgeData) {
                onDeleteEdge(state.edgeData.id);
              }
              onClose();
            }}
            className="flex items-center gap-2 w-full px-2.5 py-2 rounded-lg hover:bg-rose-950/40 hover:text-rose-300 transition-colors text-rose-400 text-left"
          >
            <Trash2 size={14} />
            <span>Delete Connection</span>
          </button>
        </div>
      )}

      {/* Canvas Pane Context Menu */}
      {state.type === 'pane' && (
        <div className="flex flex-col gap-0.5 relative">
          {/* Add Node Submenu Trigger */}
          <div
            className="relative"
            onMouseEnter={() => setIsAddSubmenuOpen(true)}
            onMouseLeave={() => setIsAddSubmenuOpen(false)}
          >
            <button
              onClick={() => setIsAddSubmenuOpen(!isAddSubmenuOpen)}
              className="flex items-center justify-between w-full px-2.5 py-2 rounded-lg hover:bg-indigo-600/20 hover:text-indigo-300 transition-colors text-slate-300 text-left group"
            >
              <div className="flex items-center gap-2">
                <Plus size={14} className="text-indigo-400" />
                <span className="font-medium">Add Node</span>
              </div>
              <ChevronRight size={13} className="text-slate-500 group-hover:text-indigo-300 transition-transform" />
            </button>

            {/* Nested Add Node Flyout */}
            {isAddSubmenuOpen && (
              <div
                className={`absolute top-0 ${
                  openSubmenuToLeft ? 'right-full mr-1.5' : 'left-full ml-1.5'
                } w-64 rounded-xl border border-slate-800/90 bg-[#0d111c]/95 p-2 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100 flex flex-col gap-2 max-h-[360px]`}
              >
                {/* Search Box */}
                <div className="relative">
                  <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    placeholder="Search node to add..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-7 pr-2.5 py-1.5 bg-slate-900/90 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>

                {/* Node List */}
                <div className="overflow-y-auto max-h-[280px] flex flex-col gap-1 pr-1 custom-scrollbar">
                  {filteredNodes.length === 0 ? (
                    <div className="p-3 text-center text-slate-500 text-[11px]">
                      No matching nodes found
                    </div>
                  ) : (
                    filteredNodes.map((def) => {
                      const Icon = ICONS[def.icon] || Sparkles;
                      const colors = CATEGORY_COLORS[def.category] || CATEGORY_COLORS.general;
                      return (
                        <button
                          key={def.type}
                          onClick={() => {
                            onAddNode(def.type, state.flowPosition);
                            onClose();
                          }}
                          className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-slate-800/90 border border-transparent hover:border-slate-700/60 transition-all text-left group"
                        >
                          <div className={`p-1.5 rounded-md border ${colors.badge} shrink-0`}>
                            <Icon size={14} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-slate-200 group-hover:text-indigo-300 text-xs truncate">
                                {def.name}
                              </span>
                              <span className="text-[9px] uppercase font-mono px-1 py-0.2 rounded bg-slate-800 text-slate-400">
                                {def.category}
                              </span>
                            </div>
                            <p className="text-[10px] text-slate-400 truncate">
                              {def.description}
                            </p>
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Paste Node (Enabled if clipboard has copied node) */}
          <button
            disabled={!hasClipboard}
            onClick={() => {
              if (hasClipboard) {
                onPasteNode(state.flowPosition);
              }
              onClose();
            }}
            className={`flex items-center justify-between w-full px-2.5 py-2 rounded-lg transition-colors text-left ${
              hasClipboard
                ? 'hover:bg-slate-800 text-slate-300 hover:text-white'
                : 'text-slate-600 cursor-not-allowed'
            }`}
          >
            <div className="flex items-center gap-2">
              <Clipboard size={14} className={hasClipboard ? 'text-indigo-400' : 'text-slate-600'} />
              <span>Paste Node</span>
            </div>
            <span className="text-[10px] text-slate-500">Ctrl+V</span>
          </button>

          <div className="my-1 border-t border-slate-800/80" />

          {/* Fit View */}
          <button
            onClick={() => {
              onFitView();
              onClose();
            }}
            className="flex items-center justify-between w-full px-2.5 py-2 rounded-lg hover:bg-slate-800 hover:text-white transition-colors text-slate-300 text-left"
          >
            <div className="flex items-center gap-2">
              <Maximize2 size={14} className="text-slate-400" />
              <span>Fit View</span>
            </div>
            <span className="text-[10px] text-slate-500">F</span>
          </button>

          {/* Select All */}
          <button
            onClick={() => {
              onSelectAll();
              onClose();
            }}
            className="flex items-center justify-between w-full px-2.5 py-2 rounded-lg hover:bg-slate-800 hover:text-white transition-colors text-slate-300 text-left"
          >
            <div className="flex items-center gap-2">
              <CheckSquare size={14} className="text-slate-400" />
              <span>Select All</span>
            </div>
            <span className="text-[10px] text-slate-500">Ctrl+A</span>
          </button>

          <div className="my-1 border-t border-slate-800/80" />

          {/* Clear Canvas */}
          <button
            onClick={() => {
              onClearCanvas();
              onClose();
            }}
            className="flex items-center gap-2 w-full px-2.5 py-2 rounded-lg hover:bg-rose-950/40 hover:text-rose-300 transition-colors text-rose-400 text-left"
          >
            <Trash2 size={14} />
            <span>Clear Canvas</span>
          </button>
        </div>
      )}
    </div>
  );
};
