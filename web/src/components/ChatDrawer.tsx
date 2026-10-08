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
  ChevronDown,
  Download,
  Zap,
  Gauge,
  BarChart2,
  FileText,
  FileJson,
  ExternalLink,
  Image as ImageIcon
} from 'lucide-react';
import { ChatMessage, WorkflowDefinition, ExecutionBenchmark } from '../types/workflow';
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
  const [currentSessionId, setCurrentSessionId] = useState<string>(
    () => localStorage.getItem('zflow_active_chat_session') || `sess_${Date.now().toString().slice(-6)}`
  );
  const [turnCount, setTurnCount] = useState<number>(0);
  const [showSessions, setShowSessions] = useState<boolean>(false);
  const [showExportMenu, setShowExportMenu] = useState<boolean>(false);
  const [sessionsList, setSessionsList] = useState<SessionSummary[]>([]);
  const [copiedSession, setCopiedSession] = useState<boolean>(false);
  const [expandedTraceMsgId, setExpandedTraceMsgId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync session ID to localStorage
  useEffect(() => {
    localStorage.setItem('zflow_active_chat_session', currentSessionId);
  }, [currentSessionId]);

  // Load active session history from SQLite on initial load or session switch
  const loadHistoryForSession = useCallback(async (sessId: string) => {
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
      }
    } catch (err) {
      console.error('Failed to load session history from SQLite:', err);
    }
  }, []);

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
    refreshSessions();
    loadHistoryForSession(currentSessionId);
  }, [currentSessionId, loadHistoryForSession, refreshSessions]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [isOpen, messages, activeSteps]);

  const handleSelectSession = async (sessId: string) => {
    setCurrentSessionId(sessId);
    setShowSessions(false);
    setShowExportMenu(false);
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
    setShowExportMenu(false);
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

  // Export Chat to Markdown (.md)
  const handleExportMarkdown = () => {
    let md = `# ZFlow Conversation Transcript\n\n`;
    md += `- **Session ID:** \`${currentSessionId}\`\n`;
    md += `- **Exported At:** ${new Date().toLocaleString()}\n`;
    md += `- **Total Turns:** ${messages.filter((m) => m.role !== 'system').length}\n\n`;
    md += `---\n\n`;

    messages.forEach((msg) => {
      const time = new Date(msg.timestamp).toLocaleTimeString();
      if (msg.role === 'user') {
        md += `### 👤 User (${time})\n\n${msg.content}\n\n`;
      } else if (msg.role === 'assistant') {
        md += `### 🤖 Assistant (${time})\n\n`;
        if (msg.benchmark) {
          md += `> ⚡ **TTFT:** ${msg.benchmark.ttftMs ?? 0}ms | ⏱️ **Total:** ${msg.benchmark.totalTimeMs ?? 0}ms`;
          if (msg.benchmark.tokensPerSec) {
            md += ` | 🚀 **Speed:** ${msg.benchmark.tokensPerSec} tok/s`;
          }
          md += `\n\n`;
        }
        md += `${msg.content}\n\n`;
      }
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `zflow_chat_${currentSessionId}.md`;
    link.click();
    URL.revokeObjectURL(url);
    setShowExportMenu(false);
  };

  // Export Chat to JSON (.json)
  const handleExportJson = () => {
    const exportData = {
      session_id: currentSessionId,
      exported_at: new Date().toISOString(),
      turn_count: turnCount,
      messages: messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
        benchmark: m.benchmark
      }))
    };
    const jsonStr = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `zflow_chat_${currentSessionId}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setShowExportMenu(false);
  };

  // Helper to render message content with rich markdown image preview
  const renderMessageContent = (content: string) => {
    if (!content) return null;

    // 1. Check if string contains markdown image syntax: ![alt](url)
    const mdImageRegex = /!\[(.*?)\]\((https?:\/\/[^\s)]+)\)/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = mdImageRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(
          <span key={`txt_${lastIndex}`} className="whitespace-pre-wrap">
            {content.substring(lastIndex, match.index)}
          </span>
        );
      }
      const altText = match[1] || 'AI Generated Image';
      const imgUrl = match[2];
      parts.push(
        <div key={`img_${match.index}`} className="my-2.5 rounded-xl overflow-hidden border border-slate-700/80 bg-slate-950/80 shadow-xl group">
          <div className="relative">
            <img
              src={imgUrl}
              alt={altText}
              loading="lazy"
              className="w-full max-h-72 object-contain bg-black/50"
            />
            <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/70 backdrop-blur-md text-[10px] font-mono text-pink-300 border border-pink-500/30 flex items-center gap-1">
              <ImageIcon size={11} className="text-pink-400" />
              <span>AI Image</span>
            </div>
          </div>
          <div className="p-2 bg-slate-900/90 border-t border-slate-800 flex items-center justify-between text-[11px]">
            <span className="text-slate-300 truncate max-w-[210px] font-mono text-[10px]" title={altText}>
              {altText}
            </span>
            <div className="flex items-center gap-1.5">
              <a
                href={imgUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors flex items-center gap-1 text-[10px]"
                title="Mở ảnh kích thước đầy đủ"
              >
                <ExternalLink size={12} />
              </a>
              <a
                href={imgUrl}
                download="zflow_generated.png"
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 text-slate-400 hover:text-pink-300 hover:bg-slate-800 rounded transition-colors flex items-center gap-1 text-[10px]"
                title="Tải ảnh về máy"
              >
                <Download size={12} />
              </a>
            </div>
          </div>
        </div>
      );
      lastIndex = match.index + match[0].length;
    }

    if (parts.length > 0) {
      if (lastIndex < content.length) {
        parts.push(
          <span key={`txt_end_${lastIndex}`} className="whitespace-pre-wrap">
            {content.substring(lastIndex)}
          </span>
        );
      }
      return <div>{parts}</div>;
    }

    // 2. Direct single image URL detection (e.g. pollinations.ai, unsplash or raw image url)
    const directUrlRegex = /^(https?:\/\/[^\s]+?\.(png|jpg|jpeg|webp|gif)(\?[^\s]*)?|https?:\/\/image\.pollinations\.ai\/[^\s]+)$/i;
    const trimmed = content.trim();
    if (directUrlRegex.test(trimmed)) {
      return (
        <div>
          <div className="my-2 rounded-xl overflow-hidden border border-slate-700/80 bg-slate-950/80 shadow-xl">
            <img
              src={trimmed}
              alt="Generated output"
              loading="lazy"
              className="w-full max-h-72 object-contain bg-black/50"
            />
            <div className="p-2 bg-slate-900/90 border-t border-slate-800 flex items-center justify-between text-[11px]">
              <span className="text-slate-400 truncate max-w-[210px] font-mono text-[10px]">
                {trimmed}
              </span>
              <div className="flex items-center gap-1.5">
                <a
                  href={trimmed}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded"
                  title="Mở tab mới"
                >
                  <ExternalLink size={12} />
                </a>
                <a
                  href={trimmed}
                  download="zflow_output.png"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1 text-slate-400 hover:text-pink-300 hover:bg-slate-800 rounded"
                  title="Tải ảnh về máy"
                >
                  <Download size={12} />
                </a>
              </div>
            </div>
          </div>
        </div>
      );
    }

    // Default regular text
    return <div className="whitespace-pre-wrap">{content}</div>;
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
    const startTime = performance.now();
    let firstTokenTime: number | null = null;
    let tokenCount = 0;
    const nodeLatencies: { nodeId: string; title?: string; type?: string; durationMs: number }[] = [];

    await streamChatWorkflow(workflow, userQuery, currentSessionId, {
      onNodeStart: (data) => {
        onNodeStatusChange(data.node_id, 'running');
        setActiveSteps((prev) => {
          const filtered = prev.filter((s) => s.id !== data.node_id);
          return [...filtered, { id: data.node_id, title: data.title, status: 'running' }];
        });
      },

      onToken: (data) => {
        if (firstTokenTime === null) {
          firstTokenTime = performance.now();
        }
        tokenCount++;
        assistantContent += data.token;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId ? { ...msg, content: assistantContent } : msg
          )
        );
      },

      onNodeComplete: (data) => {
        onNodeStatusChange(data.node_id, 'completed', data.duration_ms);
        nodeLatencies.push({
          nodeId: data.node_id,
          type: data.type,
          durationMs: data.duration_ms
        });
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
        const totalTimeMs = Math.round(performance.now() - startTime);
        const ttftMs = firstTokenTime ? Math.round(firstTokenTime - startTime) : undefined;
        const durationSec = firstTokenTime ? (performance.now() - firstTokenTime) / 1000 : totalTimeMs / 1000;
        const tokensPerSec = durationSec > 0 && tokenCount > 0 ? Number((tokenCount / durationSec).toFixed(1)) : undefined;

        const benchmark: ExecutionBenchmark = {
          ttftMs,
          totalTimeMs,
          tokenCount,
          tokensPerSec,
          nodeLatencies: [...nodeLatencies]
        };

        const finalContent = (data.final_output && !assistantContent) ? data.final_output : assistantContent;

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  content: finalContent || msg.content,
                  benchmark
                }
              : msg
          )
        );

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

  return (
    <aside
      className={`bg-[#0c0f17] border-l border-slate-800/80 flex flex-col h-full select-none z-30 shadow-2xl transition-all duration-200 ease-in-out ${
        isOpen ? 'w-[450px] opacity-100' : 'w-0 border-l-0 opacity-0 overflow-hidden pointer-events-none'
      }`}
    >
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

          <div className="flex items-center gap-1 relative">
            {/* Export Chat Button & Dropdown */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowExportMenu(!showExportMenu);
                  setShowSessions(false);
                }}
                className={`p-1.5 rounded-lg transition-colors flex items-center gap-1 text-[11px] ${
                  showExportMenu ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-indigo-400 hover:bg-slate-800'
                }`}
                title="Tải xuống / Xuất lịch sử chat"
              >
                <Download size={15} />
              </button>

              {showExportMenu && (
                <div className="absolute right-0 top-full mt-1.5 w-44 bg-slate-950 border border-slate-800 rounded-xl p-1.5 shadow-2xl z-50 space-y-1 animate-in fade-in duration-100">
                  <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800/80">
                    Xuất lịch sử chat
                  </div>
                  <button
                    onClick={handleExportMarkdown}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 text-[11px] text-slate-300 hover:text-white hover:bg-indigo-600/20 rounded-lg text-left transition-colors"
                  >
                    <FileText size={13} className="text-indigo-400" />
                    <span>Xuất Markdown (.md)</span>
                  </button>
                  <button
                    onClick={handleExportJson}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 text-[11px] text-slate-300 hover:text-white hover:bg-emerald-600/20 rounded-lg text-left transition-colors"
                  >
                    <FileJson size={13} className="text-emerald-400" />
                    <span>Xuất JSON (.json)</span>
                  </button>
                </div>
              )}
            </div>

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
              onClick={() => {
                setShowSessions(!showSessions);
                setShowExportMenu(false);
              }}
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
                className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 shadow-md leading-relaxed select-text ${
                  isUser
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none'
                }`}
              >
                {msg.content ? (
                  renderMessageContent(msg.content)
                ) : (
                  <span className="flex items-center gap-1.5 text-slate-400 italic">
                    <Loader2 size={12} className="animate-spin text-indigo-400" />
                    Đang xử lý qua các node...
                  </span>
                )}

                {/* Speed Benchmark Metric Badge on Assistant Replies */}
                {!isUser && msg.benchmark && (
                  <div className="mt-2.5 pt-2 border-t border-slate-800/80 text-[11px] font-mono">
                    <div className="flex items-center justify-between flex-wrap gap-2 text-slate-400">
                      <div className="flex items-center gap-2.5">
                        {msg.benchmark.ttftMs !== undefined && (
                          <span className="flex items-center gap-1 text-amber-400" title="Time To First Token">
                            <Zap size={11} className="text-amber-400" />
                            TTFT: {msg.benchmark.ttftMs}ms
                          </span>
                        )}
                        {msg.benchmark.totalTimeMs !== undefined && (
                          <span className="flex items-center gap-1 text-sky-400" title="Tổng độ trễ Workflow">
                            <Clock size={11} className="text-sky-400" />
                            {msg.benchmark.totalTimeMs}ms
                          </span>
                        )}
                        {msg.benchmark.tokensPerSec !== undefined && (
                          <span className="flex items-center gap-1 text-emerald-400" title="Tốc độ sinh token">
                            <Gauge size={11} className="text-emerald-400" />
                            {msg.benchmark.tokensPerSec} tok/s
                          </span>
                        )}
                      </div>

                      {msg.benchmark.nodeLatencies && msg.benchmark.nodeLatencies.length > 0 && (
                        <button
                          onClick={() => setExpandedTraceMsgId(expandedTraceMsgId === msg.id ? null : msg.id)}
                          className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-indigo-300 transition-colors bg-slate-800/60 hover:bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700/50"
                          title="Xem chi tiết độ trễ từng node"
                        >
                          <BarChart2 size={10} />
                          <span>{expandedTraceMsgId === msg.id ? 'Ẩn trace' : 'Trace nodes'}</span>
                          <ChevronDown size={10} className={`transition-transform ${expandedTraceMsgId === msg.id ? 'rotate-180' : ''}`} />
                        </button>
                      )}
                    </div>

                    {/* Expandable Waterfall Nodes Breakdown */}
                    {expandedTraceMsgId === msg.id && msg.benchmark.nodeLatencies && (
                      <div className="mt-2 p-2 bg-slate-950 border border-slate-800 rounded-lg space-y-1 animate-in fade-in duration-150">
                        <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1 flex justify-between border-b border-slate-800/80 pb-1">
                          <span>Node Execution Waterfall</span>
                          <span>Latency (ms)</span>
                        </div>
                        {msg.benchmark.nodeLatencies.map((nl, idx) => (
                          <div key={nl.nodeId + idx} className="flex items-center justify-between text-[10px] py-0.5 border-b border-slate-900/80 last:border-none">
                            <div className="flex items-center gap-1.5 truncate max-w-[200px]">
                              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0"></span>
                              <span className="text-slate-300 font-mono truncate">{nl.nodeId}</span>
                              {nl.type && <span className="text-slate-500 text-[9px]">({nl.type})</span>}
                            </div>
                            <span className="font-semibold text-amber-300 font-mono shrink-0">{nl.durationMs}ms</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
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
