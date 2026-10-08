import React from 'react';
import { Sparkles } from 'lucide-react';
import { CustomNodeData } from '../../../types/workflow';

interface Props {
  data: CustomNodeData;
}

export const PromptStylerPreview: React.FC<Props> = ({ data }) => {
  return (
    <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 flex flex-col gap-1.5 text-slate-400">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-400">Enchant Level:</span>
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold flex items-center gap-1 ${
          data.config?.enchant_level === 'masterpiece_epic' 
            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' 
            : data.config?.enchant_level === 'cinematic_photoreal'
            ? 'bg-pink-500/20 text-pink-300 border border-pink-500/40'
            : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
        }`}>
          <Sparkles size={10} />
          {data.config?.enchant_level || 'vivid'}
        </span>
      </div>
      <div className="flex justify-between text-[10px] text-slate-400">
        <span>Style Preset:</span>
        <span className="font-mono text-purple-300 font-semibold">{data.config?.style || 'cinematic'}</span>
      </div>
      <div className="flex justify-between text-[10px] text-slate-400">
        <span>Lighting / Mood:</span>
        <span className="font-mono text-slate-300 truncate max-w-[120px]">{data.config?.lighting || 'dramatic'}</span>
      </div>
      {data.lastOutput?.enchanted_prompt && (
        <p className="text-[10px] text-slate-300 italic line-clamp-2 leading-tight bg-black/40 p-1.5 rounded border border-slate-800/60 font-mono mt-0.5">
          "{data.lastOutput.enchanted_prompt}"
        </p>
      )}
    </div>
  );
};
