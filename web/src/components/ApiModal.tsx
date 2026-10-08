import React, { useState } from 'react';
import { X, Copy, Check, Terminal, Code2, Globe, Send, Play, Sparkles } from 'lucide-react';

interface ApiModalProps {
  isOpen: boolean;
  onClose: () => void;
  flowId: string;
  flowName: string;
}

export const ApiModal: React.FC<ApiModalProps> = ({ isOpen, onClose, flowId, flowName }) => {
  const [activeTab, setActiveTab] = useState<'curl_run' | 'curl_stream' | 'python' | 'javascript'>('curl_run');
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const currentHost = window.location.origin.includes('5173')
    ? 'http://127.0.0.1:8000'
    : window.location.origin;

  const runUrl = `${currentHost}/api/v1/flows/${flowId}/run`;
  const streamUrl = `${currentHost}/api/v1/flows/${flowId}/stream`;

  const codeSnippets = {
    curl_run: `# Kích hoạt Workflow đồng bộ (Sync API Trigger)
curl -X POST "${runUrl}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "inputs": {
      "query": "Xin chào! Bạn có thể tóm tắt tài liệu này giúp tôi được không?"
    },
    "session_id": "user_session_123"
  }'`,

    curl_stream: `# Kích hoạt Workflow kèm Streaming Token (Server-Sent Events)
curl -N -X POST "${streamUrl}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "inputs": {
      "query": "Hãy viết một bài giới thiệu về ZFlow Studio."
    }
  }'`,

    python: `import httpx

# 1. Gọi thực thi trực tiếp (Sync Batch Execution)
response = httpx.post(
    "${runUrl}",
    json={
        "inputs": {"query": "Giải thích kiến trúc ZFlow"},
        "session_id": "sess_456"
    },
    timeout=60.0
)
data = response.json()
print("Status:", data["status"])
print("Bot Reply:", data["outputs"]["reply"])
print("Latency:", data["execution_time_ms"], "ms")

# 2. Hoặc gọi Streaming SSE theo thời gian thực (Token Streaming)
with httpx.stream("POST", "${streamUrl}", json={"inputs": {"query": "Hello"}}) as stream:
    for line in stream.iter_lines():
        if line.startswith("data: "):
            print(line[6:], end="", flush=True)`,

    javascript: `// Gọi kích hoạt Workflow từ Web App / Frontend của bạn
async function triggerWorkflow(userMessage) {
  const response = await fetch("${runUrl}", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      inputs: { query: userMessage },
      session_id: "web_session_" + Date.now()
    })
  });

  const result = await response.json();
  console.log("Chatbot Output:", result.outputs.reply);
  return result.outputs.reply;
}

triggerWorkflow("Xin chào từ client web!");`
  };

  const activeCode = codeSnippets[activeTab];

  const handleCopy = () => {
    navigator.clipboard.writeText(activeCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-[#0c0f17] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 text-white shadow-lg shadow-blue-500/20">
              <Terminal size={18} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                Flow API Trigger & Webhook
                <span className="text-[10px] font-mono font-normal uppercase bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/30">
                  Ready to Call
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Tự động kích hoạt luồng <strong>"{flowName}"</strong> từ bất kỳ ứng dụng bên ngoài nào qua REST/SSE.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* API Info Strip */}
        <div className="px-5 py-2.5 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 font-mono">Flow ID:</span>
            <code className="text-indigo-400 bg-indigo-950/40 px-2 py-0.5 rounded font-mono font-semibold border border-indigo-900/50">
              {flowId}
            </code>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Auto-Trigger on POST
            </span>
          </div>
        </div>

        {/* Code Snippet Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-950 px-4 pt-2 gap-1 text-xs">
          <button
            onClick={() => setActiveTab('curl_run')}
            className={`px-3 py-2 rounded-t-lg font-medium transition-all ${
              activeTab === 'curl_run'
                ? 'bg-[#131722] text-indigo-400 border-t-2 border-indigo-500'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            cURL (Sync Run)
          </button>
          <button
            onClick={() => setActiveTab('curl_stream')}
            className={`px-3 py-2 rounded-t-lg font-medium transition-all ${
              activeTab === 'curl_stream'
                ? 'bg-[#131722] text-indigo-400 border-t-2 border-indigo-500'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            cURL (SSE Stream)
          </button>
          <button
            onClick={() => setActiveTab('python')}
            className={`px-3 py-2 rounded-t-lg font-medium transition-all ${
              activeTab === 'python'
                ? 'bg-[#131722] text-indigo-400 border-t-2 border-indigo-500'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            Python (httpx)
          </button>
          <button
            onClick={() => setActiveTab('javascript')}
            className={`px-3 py-2 rounded-t-lg font-medium transition-all ${
              activeTab === 'javascript'
                ? 'bg-[#131722] text-indigo-400 border-t-2 border-indigo-500'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            JavaScript (Fetch)
          </button>
        </div>

        {/* Code Block */}
        <div className="relative flex-1 bg-[#131722] p-4 overflow-y-auto">
          <button
            onClick={handleCopy}
            className="absolute top-3 right-3 flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white text-xs border border-slate-700 transition-colors shadow"
          >
            {copied ? (
              <>
                <Check size={13} className="text-emerald-400" />
                <span className="text-emerald-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy size={13} />
                <span>Copy Code</span>
              </>
            )}
          </button>

          <pre className="font-mono text-[11px] text-slate-200 leading-relaxed pr-24 whitespace-pre overflow-x-auto select-text">
            {activeCode}
          </pre>
        </div>

        {/* Response Contract Preview */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/60 text-xs text-slate-400 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={14} className="text-indigo-400" />
            <span>Đầu vào: <code className="text-slate-200 font-mono">{"inputs: { query: '...' }"}</code></span>
            <span>→ Đầu ra: <code className="text-emerald-400 font-mono">{"outputs.reply"}</code></span>
          </div>

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
