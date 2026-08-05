"use client";

import DashboardLayout from '@/components/layout/DashboardLayout';
import { ArrowLeft, RefreshCw, Terminal as TerminalIcon } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState, useRef, useCallback } from 'react';

export default function LogsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const deploymentId = params.deploymentId as string;
  
  const [logs, setLogs] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/projects/${projectId}/logs?deployment_id=${deploymentId}`;
      const res = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const data = await res.json();
          let combined = '';
          if (data.build_logs) combined += `=== BUILD LOGS ===\n${data.build_logs}\n`;
          if (data.runtime_logs) combined += `=== RUNTIME LOGS ===\n${data.runtime_logs}`;
          
          if (!data.build_logs && !data.runtime_logs) {
            setLogs('No logs available.');
          } else {
            setLogs(combined);
          }
        } else {
          const text = await res.text();
          setLogs(text);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [projectId, deploymentId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchLogs();
    
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(fetchLogs, 3000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [fetchLogs, autoRefresh]);

  useEffect(() => {
    if (autoRefresh && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoRefresh]);

  return (
    <DashboardLayout>
      <div className="mb-6">
        <Link href={`/projects/${projectId}`} className="inline-flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors mb-4">
          <ArrowLeft className="w-4 h-4" />
          Back to Project
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
              <TerminalIcon className="w-8 h-8 text-indigo-500" />
              Deployment Logs
            </h1>
            <p className="text-neutral-400 font-mono text-sm mt-1">Deployment ID: {deploymentId}</p>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
              <input 
                type="checkbox" 
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-neutral-700 bg-neutral-900 text-indigo-500 focus:ring-indigo-500"
              />
              Auto-refresh
            </label>
            <button 
              onClick={fetchLogs}
              className="bg-neutral-800 hover:bg-neutral-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="bg-[#0D0D0D] border border-neutral-800 rounded-xl overflow-hidden shadow-2xl h-[calc(100vh-250px)] flex flex-col">
        <div className="bg-neutral-900 px-4 py-2 border-b border-neutral-800 flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
          <div className="w-3 h-3 rounded-full bg-amber-500/20 border border-amber-500/50"></div>
          <div className="w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500/50"></div>
          <span className="ml-4 text-xs font-mono text-neutral-500">terminal</span>
        </div>
        <div className="flex-1 overflow-y-auto p-4 font-mono text-sm text-neutral-300">
          {loading && !logs ? (
            <div className="animate-pulse flex items-center gap-2 text-neutral-500">
              <div className="w-2 h-4 bg-neutral-600 animate-bounce"></div>
              Loading logs...
            </div>
          ) : logs ? (
            <pre className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed">
              {logs}
            </pre>
          ) : (
            <div className="text-neutral-500 italic">No logs available for this deployment yet.</div>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </DashboardLayout>
  );
}
