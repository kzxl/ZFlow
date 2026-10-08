import React, { useState, useRef, useEffect, useCallback } from 'react';
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
  Clock,
  Database,
  History,
  Plus,
  Copy,
  Check,
  ChevronDown
} from 'lucide-react';
import { ChatMessage, WorkflowDefinition } from '../types/workflow';
import { 
  streamChatWorkflow, 
  fetchMemorySessions, 
  fetchSessionHistory, 
  clearSessionMemory, 
  SessionSummary 
} from '../api/client';

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
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => `sess_${Date.now().toString().slice(-6)}`);
  const [turnCount, setTurnCount] = useState<number>(0);
  const [showSessions, setShowSessions] = useState<boolean>(false);
  const [sessionsList, setSessionsList] = useState<SessionSummary[]>([]);
  const [copiedSession, setCopiedSession] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await fetchMemorySessions();
      setSessionsList(data);
      const active = data.find((s) => s.session_id === currentSessionId);
      if (active) {
        setTurnCount(active.turn_count);
      }
    } catch (err) {
      console.error('Failed to load memory sessions:', err);
    }
  }, [currentSessionId]);

  useEffect(() => {
    if (isOpen) {
      refreshSessions();
    }
  }, [isOpen, refreshSessions]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [isOpen, messages, activeSteps]);

  const handleSelectSession = async (sessId: string) => {
    setCurrentSessionId(sessId);
    setShowSessions(false);
    try {
      const data = await fetchSessionHistory(sessId);
      if (data.history && data.history.length > 0) {
        const loadedMsgs: ChatMessage[] = data.history.map((h, i) => ({
          id: `hist_${i}_${h.timestamp || Date.now()}`,
          role: h.role === 'assistant' ? 'assistant' : 'user',
          content: h.content,
          timestamp: h.timestamp ? h.timestamp * 1000 : Date.now()
        }));
        setMessages(loadedMsgs);
        setTurnCount(data.stats?.turn_count || data.history.length);
      } else {
        setMessages([
          {
            id: 'msg_empty',
            role: 'assistant',
            content: `Cuộc hội thoại '${sessId}' chưa có tin nhắn nào. Hãy gửi câu hỏi đầu tiên!`,
            timestamp: Date.now()
          }
        ]);
        setTurnCount(0);
      }
    } catch (err) {
      console.error('Failed to fetch session history:', err);
    }
  };

  const handleNewSession = () => {
    const newId = `sess_${Date.now().toString().slice(-6)}`;
    setCurrentSessionId(newId);
    setMessages([
      {
        id: `welcome_${Date.now()}`,
        role: 'assistant',
        content: `Đã khởi tạo phiên trò chuyện mới: #${newId}. Ngữ cảnh bộ nhớ độc lập sẵn sàng!`,
        timestamp: Date.now()
      }
    ]);
    setTurnCount(0);
    setShowSessions(false);
    setActiveSteps([]);
  };

  const handleClearCurrentSession = async () => {
    try {
      await clearSessionMemory(currentSessionId);
      setMessages([
        {
          id: `cleared_${Date.now()}`,
          role: 'assistant',
          content: `Đã xóa sạch bộ nhớ SQLite của phiên #${currentSessionId}.`,
          timestamp: Date.now()
        }
      ]);
      setTurnCount(0);
      refreshSessions();
    } catch (err) {
      console.error('Failed to clear session:', err);
    }
  };

  const handleCopySessionId = () => {
    navigator.clipboard.writeText(currentSessionId);
    setCopiedSession(true);
    setTimeout(() => setCopiedSession(false), 1500);
  };

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

    await streamChatWorkflow(workflow, userQuery, currentSessionId, {
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
        // Auto-refresh memory stats
        setTimeout(() => refreshSessions(), 300);
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

  if (!isOpen) return null;

  return (
    <aside className="w-[440px] bg-[#0c0f17] border-l border-slate-800/80 flex flex-col h-full select-none z-30 shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Drawer Header */}
      <div className="p-3.5 border-b border-slate-800/80 bg-slate-950/70 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
              <Sparkles size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
                Chat Playground
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              </h2>
              <p className="text-[11px] text-slate-400">Live multi-turn conversation simulator</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={handleNewSession}
              className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-1 text-[11px]"
              title="Khởi tạo phiên hội thoại mới"
            >
              <Plus size={15} />
            </button>
            <button
              onClick={handleClearCurrentSession}
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
              title="Xóa bộ nhớ phiên này"
            >
              <Trash2 size={15} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X size={17} />
            </button>
          </div>
        </div>

        {/* Conversation Session Memory Bar */}
        <div className="flex items-center justify-between px-2.5 py-1.5 bg-slate-900/80 border border-slate-800 rounded-xl text-[11px]">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSessions(!showSessions)}
              className="flex items-center gap-1.5 text-slate-300 hover:text-white font-mono bg-slate-800/70 hover:bg-slate-800 px-2 py-0.5 rounded-md border border-slate-700/60 transition-colors"
              title="Danh sách phiên hội thoại"
            >
              <History size={12} className="text-purple-400" />
              <span>#{currentSessionId}</span>
              <ChevronDown size={11} className={`text-slate-400 transition-transform ${showSessions ? 'rotate-180' : ''}`} />
            </button>

            <button
              onClick={handleCopySessionId}
              className="text-slate-500 hover:text-slate-300 p-0.5"
              title="Sao chép Session ID"
            >
              {copiedSession ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            </button>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] font-medium">
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 font-mono">
              <Database size={10} className="text-purple-400" />
              {turnCount} lượt nhớ
            </span>
          </div>
        </div>

        {/* Sessions Dropdown Modal / List */}
        {showSessions && (
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-2.5 shadow-2xl space-y-1.5 max-h-[220px] overflow-y-auto animate-in fade-in duration-100">
            <div className="flex items-center justify-between pb-1 border-b border-slate-800/80 text-[10px] text-slate-400 font-medium">
              <span>CÁC PHIÊN HỘI THOẠI TRONG SQLITE</span>
              <button
                onClick={handleNewSession}
                className="text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5"
              >
                <Plus size={10} /> Tạo mới
              </button>
            </div>
            {sessionsList.length === 0 ? (
              <p className="text-[11px] text-slate-500 py-2 text-center">Chưa có phiên lưu trữ nào.</p>
            ) : (
              sessionsList.map((s) => (
                <div
                  key={s.session_id}
                  onClick={() => handleSelectSession(s.session_id)}
                  className={`p-2 rounded-lg cursor-pointer border text-left transition-colors flex items-center justify-between ${
                    s.session_id === currentSessionId
                      ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-200'
                      : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/60 text-slate-300'
                  }`}
                >
                  <div className="overflow-hidden pr-2">
                    <div className="flex items-center gap-1.5 font-mono text-[11px]">
                      <span className="font-semibold text-slate-100">#{s.session_id}</span>
                      <span className="text-[10px] text-purple-400">({s.turn_count} turns)</span>
                    </div>
                    {s.last_message && (
                      <p className="text-[10px] text-slate-400 truncate mt-0.5">
                        {s.last_role === 'assistant' ? '🤖 ' : '👤 '}
                        {s.last_message}
                      </p>
                    )}
                  </div>
                  <span className="text-[9px] text-slate-500 shrink-0 font-mono">
                    {new Date(s.last_updated * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))
            )}
          </div>
        )}
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
