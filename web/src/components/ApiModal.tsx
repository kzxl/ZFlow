import React, { useState, useEffect } from 'react';
import { 
  X, 
  Copy, 
  Check, 
  Terminal, 
  Code2, 
  Globe, 
  Send, 
  Play, 
  Sparkles, 
  Radio, 
  Loader2, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';

interface ApiModalProps {
  isOpen: boolean;
  onClose: () => void;
  flowId: string;
  flowName: string;
}

export const ApiModal: React.FC<ApiModalProps> = ({ isOpen, onClose, flowId, flowName }) => {
  const [activeTab, setActiveTab] = useState<'curl_run' | 'curl_stream' | 'python' | 'javascript' | 'tester'>('tester');
  const [useActiveRoute, setUseActiveRoute] = useState(false);
  const [copied, setCopied] = useState(false);

  // Live Test Runner states
  const [testPayload, setTestPayload] = useState<string>(
    JSON.stringify(
      {
        inputs: {
          query: "Tôi là Nguyễn Văn An, số điện thoại 0912345678. Hãy kiểm tra chính sách bảo mật nội bộ cho tôi.",
          user_role: "staff"
        },
        session_id: "test_live_session"
      },
      null,
      2
    )
  );
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [testResponse, setTestResponse] = useState<Record<string, any> | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  if (!isOpen) return null;

  const currentHost = window.location.origin.includes('5173')
    ? 'http://127.0.0.1:8000'
    : window.location.origin;

  const targetId = useActiveRoute ? 'active' : flowId;
  const runUrl = `${currentHost}/api/v1/flows/${targetId}/run`;
  const streamUrl = `${currentHost}/api/v1/flows/${targetId}/stream`;

  const codeSnippets = {
    curl_run: `# Kích hoạt Workflow đồng bộ (${useActiveRoute ? 'ACTIVE ROUTE' : `#${flowId}`})
curl -X POST "${runUrl}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "inputs": {
      "query": "Xin chào! Bạn có thể tóm tắt tài liệu này giúp tôi được không?",
      "user_role": "staff"
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

# 1. Kích hoạt trực tiếp và nhận kết quả theo đúng cấu hình Workflow
response = httpx.post(
    "${runUrl}",
    json={
        "inputs": {
            "query": "Giải thích kiến trúc ZFlow",
            "user_role": "staff"
        },
        "session_id": "sess_456"
    },
    timeout=60.0
)
data = response.json()
print("Kích hoạt Flow:", data["flow_name"], f"(ID: {data['flow_id']})")
print("Bot Reply:", data["outputs"]["reply"])
print("Tất cả Outputs:", data["outputs"])
print("Độ trễ:", data["execution_time_ms"], "ms")

# 2. Hoặc gọi Streaming SSE theo thời gian thực (Token Streaming)
with httpx.stream("POST", "${streamUrl}", json={"inputs": {"query": "Hello"}}) as stream:
    for line in stream.iter_lines():
        if line.startswith("data: "):
            print(line[6:], end="", flush=True)`,

    javascript: `// Gọi kích hoạt Workflow từ Web App / Frontend của bạn
async function triggerWorkflow(userQuery, userRole = "staff") {
  const response = await fetch("${runUrl}", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      inputs: { 
        query: userQuery,
        user_role: userRole
      },
      session_id: "web_session_" + Date.now()
    })
  });

  const result = await response.json();
  console.log("Flow được thực thi:", result.flow_name);
  console.log("Outputs chuẩn nhận được:", result.outputs);
  return result.outputs.reply;
}

triggerWorkflow("Xin chào từ ứng dụng của tôi!");`
  };

  const handleCopy = () => {
    const textToCopy = activeTab === 'tester' ? testPayload : codeSnippets[activeTab];
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRunLiveTest = async () => {
    setIsRunningTest(true);
    setTestError(null);
    setTestResponse(null);
    try {
      let parsedBody = {};
      try {
        parsedBody = JSON.parse(testPayload);
      } catch (err) {
        setTestError("JSON không hợp lệ! Vui lòng kiểm tra cú pháp.");
        setIsRunningTest(false);
        return;
      }

      const res = await fetch(runUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsedBody)
      });

      const data = await res.json();
      setTestResponse(data);
    } catch (err: any) {
      setTestError(err.message || "Lỗi khi gọi API.");
    } finally {
      setIsRunningTest(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-3xl bg-[#0c0f17] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 text-white shadow-lg shadow-blue-500/20">
              <Terminal size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-100">
                  Kích Hoạt Workflow Qua Public API
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                  {useActiveRoute ? 'Route: ACTIVE FLOW' : `ID: #${flowId}`}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Gửi input thực tế từ ứng dụng ngoài và nhận output theo đúng cấu hình của workflow
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

        {/* Route Target Selector */}
        <div className="px-6 py-2.5 bg-slate-900/40 border-b border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-[11px]">Đích định tuyến:</span>
            <button
              onClick={() => setUseActiveRoute(false)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                !useActiveRoute
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-800/60'
              }`}
            >
              Workflow Này (#{flowId})
            </button>
            <button
              onClick={() => setUseActiveRoute(true)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                useActiveRoute
                  ? 'bg-cyan-600 text-white shadow-sm ring-1 ring-cyan-400'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-800/60'
              }`}
              title="Định tuyến động vào bất kỳ workflow nào đang được kích hoạt làm Active Flow"
            >
              <Radio size={11} className={useActiveRoute ? 'animate-pulse' : ''} />
              <span>Active Workflow Route (/flows/active/run)</span>
            </button>
          </div>

          <div className="text-[10px] font-mono text-slate-500 truncate max-w-[240px]">
            POST {runUrl.replace(currentHost, '')}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-6 gap-2 pt-2">
          <button
            onClick={() => setActiveTab('tester')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === 'tester'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Play size={13} />
            <span>Interactive Test Runner</span>
          </button>

          <button
            onClick={() => setActiveTab('curl_run')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'curl_run'
                ? 'border-cyan-500 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>cURL (Sync)</span>
          </button>

          <button
            onClick={() => setActiveTab('curl_stream')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'curl_stream'
                ? 'border-cyan-500 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>cURL (Stream SSE)</span>
          </button>

          <button
            onClick={() => setActiveTab('python')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'python'
                ? 'border-cyan-500 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>Python (httpx)</span>
          </button>

          <button
            onClick={() => setActiveTab('javascript')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === 'javascript'
                ? 'border-cyan-500 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>Node / JS (Fetch)</span>
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 text-xs">
          {activeTab === 'tester' ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-300">
                  Request Payload JSON (Input thực tế gửi vào workflow):
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  Target: {useActiveRoute ? 'Active Flow Engine' : `#${flowId}`}
                </span>
              </div>

              <textarea
                rows={6}
                value={testPayload}
                onChange={(e) => setTestPayload(e.target.value)}
                className="w-full bg-slate-950 font-mono text-[11px] p-3 rounded-xl border border-slate-800 focus:border-indigo-500 text-slate-200 focus:outline-none resize-none leading-relaxed"
                placeholder='{ "inputs": { "query": "..." } }'
              />

              <div className="flex items-center justify-between">
                <button
                  onClick={handleRunLiveTest}
                  disabled={isRunningTest}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-lg transition-all ${
                    isRunningTest
                      ? 'bg-slate-800 text-slate-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-emerald-600/20'
                  }`}
                >
                  {isRunningTest ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>Đang thực thi Workflow...</span>
                    </>
                  ) : (
                    <>
                      <Send size={14} />
                      <span>Gửi Request Kiểm Thử Ngay</span>
                    </>
                  )}
                </button>

                {testResponse?.execution_time_ms && (
                  <span className="text-emerald-400 font-mono text-[11px] bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded">
                    ⚡ Phản hồi trong {testResponse.execution_time_ms} ms
                  </span>
                )}
              </div>

              {testError && (
                <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle size={15} />
                  <span>{testError}</span>
                </div>
              )}

              {/* Response Inspector */}
              {testResponse && (
                <div className="space-y-2 pt-2 animate-in fade-in">
                  <div className="flex items-center justify-between text-[11px] font-semibold text-slate-300">
                    <span className="flex items-center gap-1.5 text-emerald-400">
                      <CheckCircle2 size={13} />
                      Kết quả Output thực tế nhận được từ Workflow:
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      Status: {testResponse.status} | Flow: {testResponse.flow_name}
                    </span>
                  </div>

                  <pre className="w-full bg-slate-950 font-mono text-[10px] p-3 rounded-xl border border-emerald-900/40 text-emerald-300 max-h-56 overflow-y-auto leading-relaxed">
                    {JSON.stringify(testResponse, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-slate-400 text-[11px]">
                <span>Đoạn mã mẫu sẵn sàng sao chép và tích hợp:</span>
                <span className="text-[10px] text-slate-500 font-mono">Endpoint: {runUrl}</span>
              </div>
              <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-slate-200 font-mono text-[11px] overflow-x-auto leading-relaxed max-h-80">
                {codeSnippets[activeTab]}
              </pre>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-950 flex items-center justify-between">
          <div className="text-[11px] text-slate-500">
            ZFlow Sovereign Engine • Định tuyến động &amp; Trích xuất Output tự động
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-colors"
            >
              {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
              <span>{copied ? 'Đã sao chép!' : 'Sao chép Code'}</span>
            </button>

            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
            >
              Đóng
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
