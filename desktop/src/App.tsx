import React, { useState } from 'react';
import Dashboard from './views/Dashboard';
import TargetConfig from './views/TargetConfig';
import LiveTelemetry from './views/LiveTelemetry';
import FindingsInspector from './views/FindingsInspector';
import ReportViewer from './views/ReportViewer';

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'config' | 'live' | 'findings' | 'reports'>('dashboard');

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      <nav className="w-64 border-r border-slate-800 p-4 flex flex-col gap-2">
        <h1 className="text-xl font-bold tracking-wider text-cyan-400 mb-6">AEGIS</h1>
        <button onClick={() => setActiveTab('dashboard')} className="text-left px-3 py-2 rounded hover:bg-slate-800">Dashboard</button>
        <button onClick={() => setActiveTab('config')} className="text-left px-3 py-2 rounded hover:bg-slate-800">Target Config</button>
        <button onClick={() => setActiveTab('live')} className="text-left px-3 py-2 rounded hover:bg-slate-800">Live Telemetry</button>
        <button onClick={() => setActiveTab('findings')} className="text-left px-3 py-2 rounded hover:bg-slate-800">Findings Inspector</button>
        <button onClick={() => setActiveTab('reports')} className="text-left px-3 py-2 rounded hover:bg-slate-800">Report Viewer</button>
      </nav>
      <main className="flex-1 overflow-auto p-6">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'config' && <TargetConfig />}
        {activeTab === 'live' && <LiveTelemetry />}
        {activeTab === 'findings' && <FindingsInspector />}
        {activeTab === 'reports' && <ReportViewer />}
      </main>
    </div>
  );
}
