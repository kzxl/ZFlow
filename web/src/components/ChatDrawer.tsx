import React, { useState, useRef, useEffect } from 'react';
import { 
  X, 
  Send, 
  Bot, 
  User, 
  Trash2, 
  Loader2, 
  CheckCircle2, 
  AlertCircle, 
  Cpu, 
  Sparkles, 
  Clock 
} from 'lucide-react';
import { ChatMessage, WorkflowDefinition } from '../types/workflow';
import { streamChatWorkflow } from '../api/client';

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  workflow: WorkflowDefinition;
  onNodeStatusChange: (nodeId: string, status: 'idle' | 'running' | 'completed' | 'error', durationMs?: number) => void;
}

export const ChatDrawer: React.FC<ChatDrawerProps> = ({
  isOpen,
  onClose,
  workflow,
  onNodeStatusChange
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg_welcome',
      role: 'assistant',
      content: 'Chào bạn! Tôi là trợ lý ảo được điều phối bởi ZFlow Engine. Bạn có thể trò chuyện để kiểm tra luồng workflow trực tiếp!',
      timestamp: Date.now()
    }
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeSteps, setActiveSteps] = useState<{ id: string; title: string; status: 'running' | 'completed' | 'error' }[]>([]);
  const sessionIdRef = useRef<string>(`session_${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [isOpen, messages, activeSteps]);

  const handleSendMessage = async () => {
    if (!input.trim() || isStreaming) return;

    const userQuery = input.trim();
    setInput('');

    // Add user message
    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: userQuery,
      timestamp: Date.now()
    };

    // Prepare assistant message
    const assistantMsgId = `asst_${Date.now()}`;
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      nodeSteps: []
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);
    setActiveSteps([]);

    let assistantContent = '';

    await streamChatWorkflow(workflow, userQuery, sessionIdRef.current, {
      onNodeStart: (data) => {
        onNodeStatusChange(data.node_id, 'running');
        setActiveSteps((prev) => {
          const filtered = prev.filter((s) => s.id !== data.node_id);
          return [...filtered, { id: data.node_id, title: data.title, status: 'running' }];
        });
      },

      onToken: (data) => {
        assistantContent += data.token;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId ? { ...msg, content: assistantContent } : msg
          )
        );
      },

      onNodeComplete: (data) => {
        onNodeStatusChange(data.node_id, 'completed', data.duration_ms);
        setActiveSteps((prev) =>
          prev.map((s) =>
            s.id === data.node_id ? { ...s, status: 'completed' } : s
          )
        );
      },

      onNodeError: (data) => {
        onNodeStatusChange(data.node_id, 'error');
        setActiveSteps((prev) =>
          prev.map((s) =>
            s.id === data.node_id ? { ...s, status: 'error' } : s
          )
        );
      },

      onWorkflowComplete: (data) => {
        setIsStreaming(false);
        if (data.final_output && !assistantContent) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, content: data.final_output } : msg
            )
          );
        }
      },

      onError: (err) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, content: `⚠️ Lỗi thực thi Workflow: ${err.message || String(err)}` }
              : msg
          )
        );
      }
    });
  };

  const clearChat = () => {
    setMessages([]);
    sessionIdRef.current = `session_${Date.now()}`;
    setActiveSteps([]);
  };

  if (!isOpen) return null;

  return (
    <aside className="w-[420px] bg-[#0c0f17] border-l border-slate-800/80 flex flex-col h-full select-none z-30 shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
            <Sparkles size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
              Live Chat Simulator
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            </h2>
            <p className="text-[11px] text-slate-400">Testing active node graph in real-time</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={clearChat}
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
            title="Reset conversation"
          >
            <Trash2 size={16} />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Realtime Graph Execution Progress Bar */}
      {activeSteps.length > 0 && (
        <div className="px-4 py-2 bg-slate-900/90 border-b border-slate-800 flex items-center gap-1.5 overflow-x-auto text-[10px]">
          <span className="text-slate-500 font-mono">Trace:</span>
          {activeSteps.map((step, idx) => (
            <div
              key={step.id + idx}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-full border whitespace-nowrap ${
                step.status === 'running'
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                  : step.status === 'completed'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              }`}
            >
              {step.status === 'running' && <Loader2 size={10} className="animate-spin text-amber-400" />}
              {step.status === 'completed' && <CheckCircle2 size={10} className="text-emerald-400" />}
              {step.status === 'error' && <AlertCircle size={10} className="text-rose-400" />}
              <span>{step.title}</span>
            </div>
          ))}
        </div>
      )}

      {/* Messages List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-7 h-7 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-300 shrink-0">
                  <Bot size={15} />
                </div>
              )}

              <div
                className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 shadow-md leading-relaxed select-text ${
                  isUser
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none whitespace-pre-wrap'
                }`}
              >
                {msg.content || (
                  <span className="flex items-center gap-1.5 text-slate-400 italic">
                    <Loader2 size={12} className="animate-spin text-indigo-400" />
                    Đang xử lý qua các node...
                  </span>
                )}
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0">
                  <User size={15} />
                </div>
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            placeholder="Type query to test workflow..."
            value={input}
            disabled={isStreaming}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 px-3.5 py-2 bg-slate-900 border border-slate-700/80 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:hover:bg-indigo-600 text-white rounded-xl shadow-lg shadow-indigo-600/30 transition-all shrink-0"
          >
            {isStreaming ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </form>
      </div>
    </aside>
  );
};
