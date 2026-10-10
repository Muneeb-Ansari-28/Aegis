import React from 'react';

export default function EvidencePair({ prompt, response }: { prompt: string; response: string }) {
  return (
    <div className="border border-slate-800 rounded p-4 flex flex-col gap-3">
      <div className="bg-slate-900 p-3 rounded">
        <span className="text-xs text-cyan-400 font-bold block mb-1">PROMPT</span>
        <p className="text-sm">{prompt}</p>
      </div>
      <div className="bg-slate-900 p-3 rounded">
        <span className="text-xs text-rose-400 font-bold block mb-1">TARGET RESPONSE</span>
        <p className="text-sm text-slate-300">{response}</p>
      </div>
    </div>
  );
}
