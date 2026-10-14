
export default function LogStream({ logs }: { logs: string[] }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded p-4 font-mono text-sm h-64 overflow-y-auto">
      {logs.map((log, i) => (
        <div key={i} className="text-slate-300">{log}</div>
      ))}
    </div>
  );
}
