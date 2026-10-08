import React from 'react';
import { ExternalLink } from 'lucide-react';
import { CustomNodeData } from '../../../types/workflow';

interface Props {
  data: CustomNodeData;
}

export const ImageGenPreview: React.FC<Props> = ({ data }) => {
  const imageUrl = data.lastOutput?.image_url || data.config?.preview_url;

  return (
    <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 space-y-1.5">
      <div className="flex justify-between text-slate-400">
        <span>Provider:</span>
        <span className="font-mono text-pink-300 font-semibold uppercase text-[10px]">
          {data.config?.provider || 'simulator'}
        </span>
      </div>
      <div className="flex justify-between text-slate-400">
        <span>Ratio:</span>
        <span className="font-mono text-slate-300">{data.config?.aspect_ratio || '1:1'}</span>
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
