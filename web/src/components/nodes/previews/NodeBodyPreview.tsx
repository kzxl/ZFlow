import React from 'react';
import { CustomNodeData } from '../../../types/workflow';
import { LLMPreview } from './LLMPreview';
import { ImageGenPreview } from './ImageGenPreview';
import { PromptStylerPreview } from './PromptStylerPreview';
import { System1Preview } from './System1Preview';
import { PermissionGuardPreview } from './PermissionGuardPreview';
import { SemanticCachePreview } from './SemanticCachePreview';
import { RouterPreview } from './RouterPreview';
import { GatewayPreview } from './GatewayPreview';
import { AuthPreview } from './AuthPreview';

interface Props {
  type: string;
  data: CustomNodeData;
}

export const NodeBodyPreview: React.FC<Props> = ({ type, data }) => {
  switch (type) {
    case 'auth':
      return <AuthPreview data={data} />;
    case 'gateway':
      return <GatewayPreview data={data} />;
    case 'llm':
      return <LLMPreview data={data} />;
    case 'image_gen':
      return <ImageGenPreview data={data} />;
    case 'prompt_styler':
      return <PromptStylerPreview data={data} />;
    case 'system1_reflex':
      return <System1Preview data={data} />;
    case 'permission_guard':
      return <PermissionGuardPreview data={data} />;
    case 'semantic_cache':
      return <SemanticCachePreview data={data} />;
    case 'router':
      return <RouterPreview data={data} />;

    case 'prompt':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400 line-clamp-2 italic text-[10px] leading-relaxed">
          "{data.config?.system_template || 'System Instructions...'}"
        </div>
      );

    case 'tool':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
          <span>Tool:</span>
          <span className="font-mono text-blue-300 font-semibold">{data.config?.tool_name || 'datetime_now'}</span>
        </div>
      );

    case 'code':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 font-mono text-[10px] text-purple-300 truncate">
          def main(inputs, context): ...
        </div>
      );

    case 'http':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex flex-col gap-0.5 text-slate-400">
          <div className="flex justify-between">
            <span>Method:</span>
            <span className="font-mono text-cyan-300 font-semibold">{data.config?.method || 'POST'}</span>
          </div>
          <div className="text-[10px] text-slate-500 truncate">{data.config?.url || 'https://...'}</div>
        </div>
      );

    case 'vision':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex flex-col gap-1 text-slate-400">
          <div className="flex justify-between">
            <span>Task:</span>
            <span className="font-mono text-indigo-300 font-semibold text-[10px]">{data.config?.task_mode || 'general_description'}</span>
          </div>
        </div>
      );

    case 'rag':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
          <span>Top Chunks:</span>
          <span className="font-mono text-purple-300 font-semibold">{data.config?.top_k || 3}</span>
        </div>
      );

    case 'agent':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
          <span>Loops:</span>
          <span className="font-mono text-indigo-300 font-semibold">{data.config?.max_iterations || 4} iters</span>
        </div>
      );

    case 'human_input':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex justify-between text-slate-400">
          <span>Approval:</span>
          <span className="font-mono text-rose-300 font-semibold">{data.config?.action_type || 'approve_reject'}</span>
        </div>
      );

    case 'input':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400 line-clamp-2 text-[10px]">
          Query: <span className="text-emerald-300 italic">"{data.config?.default_query || 'Xin chào!'}"</span>
        </div>
      );

    case 'output':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 text-slate-400 flex justify-between">
          <span>API Output Key:</span>
          <span className="font-mono text-cyan-300 font-semibold">"{data.config?.output_key || 'reply'}"</span>
        </div>
      );

    case 'subflow':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex flex-col gap-1 text-slate-400 text-[10px]">
          <div className="flex justify-between items-center">
            <span>Subflow ID:</span>
            <span className="font-mono text-purple-300 font-semibold bg-purple-500/10 px-1.5 py-0.5 rounded border border-purple-500/20">
              {data.config?.subflow_id || 'default_flow'}
            </span>
          </div>
          <div className="flex justify-between text-slate-500">
            <span>Inherit Ctx:</span>
            <span className="font-mono text-slate-300">{data.config?.inherit_context !== false ? 'True' : 'False'}</span>
          </div>
        </div>
      );

    case 'webhook':
      return (
        <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 flex flex-col gap-1 text-slate-400 text-[10px]">
          <div className="flex justify-between items-center">
            <span>Hook ID:</span>
            <span className="font-mono text-emerald-300 font-semibold bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
              {data.config?.hook_id || 'github_hook'}
            </span>
          </div>
          <div className="flex justify-between text-slate-500">
            <span>Endpoint:</span>
            <span className="font-mono text-[9px] text-slate-400 truncate">/api/v1/webhook/...</span>
          </div>
        </div>
      );

    default:
      return null;
  }
};
