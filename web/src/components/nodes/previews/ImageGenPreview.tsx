import React from 'react';
import { ExternalLink } from 'lucide-react';
import { CustomNodeData } from '../../../types/workflow';

interface Props {
  data: CustomNodeData;
}

export const ImageGenPreview: React.FC<Props> = ({ data }) => {
  const imageUrl = data.lastOutput?.image_url || data.config?.preview_url;
  const isComfy = data.config?.provider === 'comfyui_local';
  const steps = data.config?.steps || 25;
  const sampler = data.config?.sampler_name || 'euler';
  const baseUrl = data.config?.comfyui_base_url || 'http://192.168.10.7:8188';
  let hostDisplay = baseUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');

  return (
    <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 space-y-1.5 text-[10px]">
      <div className="flex justify-between items-center text-slate-400">
        <span>Engine:</span>
        <span className={`font-mono font-semibold px-1.5 py-0.5 rounded text-[9px] ${
          isComfy 
            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300' 
            : 'bg-pink-500/10 border border-pink-500/30 text-pink-300'
        }`}>
          {isComfy ? 'ComfyUI Local' : (data.config?.provider || 'simulator')}
        </span>
      </div>

      {isComfy && (
        <>
          <div className="flex justify-between text-slate-400">
            <span>Server:</span>
            <span className="font-mono text-slate-300 truncate max-w-[130px]" title={baseUrl}>
              {hostDisplay}
            </span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Speed:</span>
            <span className="font-mono text-cyan-300 font-medium">
              {data.config?.speed_preset === 'turbo_fast' ? '⚡ Turbo Fast' : (data.config?.speed_preset || 'Standard')}
            </span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Sampling:</span>
            <span className="font-mono text-amber-300 font-medium">
              {steps}st · {sampler}
            </span>
          </div>
        </>
      )}

      <div className="flex justify-between text-slate-400">
        <span>Ratio:</span>
        <span className="font-mono text-slate-300">{data.config?.aspect_ratio || '3:2'}</span>
      </div>

      {imageUrl && (
        <div className="mt-1.5 rounded-lg overflow-hidden border border-pink-500/40 relative group shadow-md">
          <img
            src={imageUrl}
            alt="AI Generated"
            className="w-full h-28 object-cover rounded-md hover:scale-105 transition-transform duration-200"
          />
          <a
            href={imageUrl}
            target="_blank"
            rel="noreferrer"
            className="absolute top-1 right-1 p-1 bg-black/80 hover:bg-black text-white rounded text-[10px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5 shadow"
            title="Mở ảnh kích thước đầy đủ"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink size={10} />
          </a>
        </div>
      )}
    </div>
  );
};
