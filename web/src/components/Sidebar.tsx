import React, { useState, useEffect, useCallback } from 'react';
import { 
  MessageSquare, 
  FileText, 
  Sparkles, 
  GitBranch, 
  GitFork,
  BookOpen,
  BrainCircuit,
  UserCheck,
  Wrench, 
  Database, 
  Send, 
  Code2,
  Globe,
  Image,
  Palette,
  Eye,
  Search, 
  Plus, 
  Layers, 
  GripVertical,
  PanelLeftClose,
  PanelLeftOpen,
  HelpCircle,
  Cpu,
  Zap,
  Webhook,
  Workflow,
  Network
} from 'lucide-react';
import { NodeMetadata, NodeCategory } from '../types/workflow';

const ICONS: Record<string, React.ElementType> = {
  MessageSquare,
  FileText,
  Sparkles,
  GitBranch,
  GitFork,
  BookOpen,
  BrainCircuit,
  UserCheck,
  Image,
  Palette,
  Eye,
  Wrench,
  Database,
  Send,
  Code2,
  Globe,
  Zap,
  Webhook,
  Workflow,
  Network
};

const CATEGORY_COLORS: Record<string, { badge: string; text: string; dot: string }> = {
  input: { badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  prompt: { badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30', text: 'text-amber-400', dot: 'bg-amber-400' },
  llm: { badge: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30', text: 'text-indigo-400', dot: 'bg-indigo-400' },
  logic: { badge: 'bg-rose-500/15 text-rose-400 border-rose-500/30', text: 'text-rose-400', dot: 'bg-rose-400' },
  tool: { badge: 'bg-blue-500/15 text-blue-400 border-blue-500/30', text: 'text-blue-400', dot: 'bg-blue-400' },
  memory: { badge: 'bg-purple-500/15 text-purple-400 border-purple-500/30', text: 'text-purple-400', dot: 'bg-purple-400' },
  media: { badge: 'bg-pink-500/15 text-pink-400 border-pink-500/30', text: 'text-pink-400', dot: 'bg-pink-400' },
  output: { badge: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30', text: 'text-cyan-400', dot: 'bg-cyan-400' },
  general: { badge: 'bg-slate-700/30 text-slate-300 border-slate-700/50', text: 'text-slate-300', dot: 'bg-slate-400' }
};

interface SidebarProps {
  nodeDefs: NodeMetadata[];
  onAddNode: (type: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ nodeDefs, onAddNode }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
  const [width, setWidth] = useState<number>(() => {
    const saved = localStorage.getItem('zflow_sidebar_width');
    return saved ? Math.max(220, Math.min(600, parseInt(saved, 10))) : 288;
  });
  const [isResizing, setIsResizing] = useState<boolean>(false);

  // Drag-to-resize sidebar panel
  const startResizing = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const minWidth = 220;
      const maxWidth = Math.min(600, Math.floor(window.innerWidth * 0.45));

      // Dragging too far left collapses the panel
      if (e.clientX < 140) {
        setIsCollapsed(true);
        setIsResizing(false);
        return;
      }

      const newWidth = Math.max(minWidth, Math.min(maxWidth, e.clientX));
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      if (isResizing) {
        setIsResizing(false);
        localStorage.setItem('zflow_sidebar_width', width.toString());
      }
    };

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, width]);

  const categories = [
    { id: 'all', label: 'All' },
    { id: 'media', label: 'Image & Media' },
    { id: 'llm', label: 'AI & LLM' },
    { id: 'logic', label: 'Logic' },
    { id: 'tool', label: 'Tools' },
    { id: 'io', label: 'I/O & State' }
  ];

  const filteredNodes = nodeDefs.filter((node) => {
    const matchesSearch = 
      node.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      node.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
      node.description.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    if (selectedCategory === 'all') return true;
    if (selectedCategory === 'media') return node.category === 'media' || node.type === 'image_gen' || node.type === 'prompt_styler' || node.type === 'vision';
    if (selectedCategory === 'llm') return node.category === 'llm' || node.category === 'prompt';
    if (selectedCategory === 'logic') return node.category === 'logic';
    if (selectedCategory === 'tool') return node.category === 'tool';
    if (selectedCategory === 'io') return node.category === 'input' || node.category === 'output' || node.category === 'memory';
    return true;
  });

  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  // Collapsed Sidebar View
  if (isCollapsed) {
    return (
      <aside className="w-14 bg-[#0a0d14] border-r border-slate-800/80 flex flex-col items-center py-3 select-none z-10 transition-all duration-200 shrink-0">
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-colors mb-4"
          title="Expand Node Palette"
        >
          <PanelLeftOpen size={18} />
        </button>

        <div className="flex-1 flex flex-col gap-2 overflow-y-auto no-scrollbar px-1">
          {nodeDefs.map((node) => {
            const Icon = ICONS[node.icon] || Sparkles;
            const colors = CATEGORY_COLORS[node.category] || CATEGORY_COLORS.general;
            return (
              <button
                key={node.type}
                draggable
                onDragStart={(e) => onDragStart(e, node.type)}
                onClick={() => onAddNode(node.type)}
                className="w-10 h-10 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-indigo-500/50 flex items-center justify-center text-slate-400 hover:text-white transition-all group relative"
                title={`${node.name} (Click to add or drag)`}
              >
                <div className={`p-1.5 rounded-lg ${colors.badge}`}>
                  <Icon size={16} />
                </div>
                <div className="hidden group-hover:block absolute left-12 bg-slate-900 border border-slate-700 text-slate-200 text-xs px-2.5 py-1 rounded-md shadow-xl whitespace-nowrap z-50">
                  {node.name}
                </div>
              </button>
            );
          })}
        </div>
      </aside>
    );
  }

  // Expanded Professional Sidebar View
  return (
    <aside
      style={{ width: `${width}px` }}
      className={`relative bg-[#0a0d14] border-r border-slate-800/80 flex flex-col h-full select-none z-10 shrink-0 ${
        isResizing ? '' : 'transition-[width] duration-150'
      }`}
    >
      {/* Brand & Header */}
      <div className="p-3.5 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/40">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 rounded-lg shadow-md shadow-indigo-600/25">
            <Cpu size={16} className="text-white" />
          </div>
          <div>
            <h1 className="font-bold text-xs tracking-wider text-slate-100 uppercase flex items-center gap-1.5">
              Node Library
              <span className="text-[9px] font-mono font-normal normal-case bg-indigo-500/10 text-indigo-400 px-1 py-0.2 rounded border border-indigo-500/20">
                {filteredNodes.length}
              </span>
            </h1>
          </div>
        </div>

        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800/80 rounded-lg transition-colors"
          title="Collapse Panel"
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      {/* Search Input */}
      <div className="px-3 pt-3 pb-2">
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search nodes or tools..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-slate-900/90 border border-slate-800/90 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
          />
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="px-3 pb-2.5 flex items-center gap-1 overflow-x-auto no-scrollbar border-b border-slate-800/60">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-2 py-1 rounded-md text-[10px] font-medium whitespace-nowrap transition-colors ${
              selectedCategory === cat.id
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Draggable Node Cards List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredNodes.map((node) => {
          const Icon = ICONS[node.icon] || Sparkles;
          const colors = CATEGORY_COLORS[node.category] || CATEGORY_COLORS.general;

          return (
            <div
              key={node.type}
              draggable
              onDragStart={(e) => onDragStart(e, node.type)}
              onClick={() => onAddNode(node.type)}
              className="group relative p-2.5 bg-[#0f131f]/80 hover:bg-[#141929] border border-slate-800/80 hover:border-indigo-500/50 rounded-xl cursor-grab active:cursor-grabbing transition-all duration-150 shadow-sm hover:shadow-lg hover:shadow-indigo-500/5"
            >
              <div className="flex items-start gap-2.5">
                {/* Drag Grip Indicator */}
                <div className="mt-1 text-slate-600 group-hover:text-slate-400 opacity-40 group-hover:opacity-100 transition-opacity">
                  <GripVertical size={13} />
                </div>

                {/* Node Icon */}
                <div className={`p-1.5 rounded-lg border shadow-sm shrink-0 ${colors.badge}`}>
                  <Icon size={15} />
                </div>

                {/* Node Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200 group-hover:text-white truncate">
                      {node.name}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddNode(node.type);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-0.5 rounded bg-indigo-600/30 hover:bg-indigo-600 text-indigo-300 hover:text-white transition-all"
                      title="Add to canvas"
                    >
                      <Plus size={13} />
                    </button>
                  </div>

                  <p className="text-[10px] text-slate-400 line-clamp-1 mt-0.5 leading-snug">
                    {node.description}
                  </p>

                  <div className="mt-2 flex items-center justify-between text-[9px] text-slate-500 font-mono">
                    <div className="flex items-center gap-1.5">
                      <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                        <span className="w-1 h-1 rounded-full bg-indigo-400"></span>
                        {node.inputs.length} In
                      </span>
                      <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                        <span className="w-1 h-1 rounded-full bg-emerald-400"></span>
                        {node.outputs.length} Out
                      </span>
                    </div>

                    <span className="capitalize text-slate-500 text-[10px]">
                      {node.category}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {filteredNodes.length === 0 && (
          <div className="text-center py-8 text-xs text-slate-500">
            No matching nodes found.
          </div>
        )}
      </div>

      {/* Footer Info & Shortcuts */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60 text-[10px] text-slate-500 space-y-1">
        <div className="flex items-center justify-between">
          <span>Add Node:</span>
          <span className="font-mono text-slate-400">Drag or Click</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Edit Config:</span>
          <span className="font-mono text-slate-400">Double-Click</span>
        </div>
      </div>
      {/* Draggable Resize Handle on right border */}
      <div
        onMouseDown={startResizing}
        onDoubleClick={() => setWidth(288)}
        title="Drag to resize sidebar (Double-click to reset default width)"
        className={`absolute -right-1.5 top-0 bottom-0 w-3 cursor-col-resize z-20 group flex items-center justify-center transition-colors ${
          isResizing ? 'bg-indigo-500/20' : 'hover:bg-indigo-500/10'
        }`}
      >
        <div
          className={`w-0.5 h-12 rounded-full transition-colors ${
            isResizing ? 'bg-indigo-400' : 'group-hover:bg-indigo-400/80 bg-transparent'
          }`}
        />
      </div>
    </aside>
  );
};
