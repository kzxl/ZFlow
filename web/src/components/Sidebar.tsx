import React, { useState } from 'react';
import { 
  MessageSquare, 
  FileText, 
  Sparkles, 
  GitBranch, 
  Wrench, 
  Database, 
  Send, 
  Code2,
  Globe,
  Search, 
  PlusCircle, 
  Layers 
} from 'lucide-react';
import { NodeMetadata } from '../types/workflow';

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

interface SidebarProps {
  nodeDefs: NodeMetadata[];
  onAddNode: (type: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ nodeDefs, onAddNode }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredNodes = nodeDefs.filter((node) =>
    node.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    node.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
    node.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside className="w-72 bg-[#0c0f17] border-r border-slate-800/80 flex flex-col h-full select-none z-10">
      {/* Brand & Title */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-gradient-to-tr from-indigo-600 to-purple-600 rounded-xl shadow-lg shadow-indigo-600/30">
            <Layers size={18} className="text-white" />
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-wide text-slate-100 flex items-center gap-1.5">
              ZFlow Studio
              <span className="text-[10px] font-normal uppercase bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded border border-indigo-500/30">
                AI Node
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">Node-Based Chatbot Pipeline</p>
          </div>
        </div>
      </div>

      {/* Search Input */}
      <div className="p-3 border-b border-slate-800/60">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search nodes & options..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-900/80 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Node Palette List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-1">
          Available Modules ({filteredNodes.length})
        </div>

        {filteredNodes.map((node) => {
          const Icon = ICONS[node.icon] || Sparkles;
          return (
            <div
              key={node.type}
              draggable
              onDragStart={(e) => onDragStart(e, node.type)}
              onClick={() => onAddNode(node.type)}
              className="group p-3 bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl cursor-grab active:cursor-grabbing transition-all duration-150 flex items-start gap-3 shadow-sm hover:shadow-md"
            >
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <Icon size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-200 group-hover:text-white">
                    {node.name}
                  </span>
                  <PlusCircle size={14} className="text-slate-500 group-hover:text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5 leading-snug">
                  {node.description}
                </p>
                <div className="mt-2 flex gap-1.5 flex-wrap">
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                    {node.inputs.length} In
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                    {node.outputs.length} Out
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40 text-[10px] text-slate-500 text-center">
        Drag nodes onto canvas or click to add
      </div>
    </aside>
  );
};
