import Link from "next/link";
import { Card } from "@/components/ui/Card";

export default function Dashboard() {
  const mockServices = [
    { name: "api-gateway", type: "FastAPI Backend", status: "Running", url: "https://api.forge.local", commit: "a3f9c2d", updated: "2 mins ago" },
    { name: "web-frontend", type: "Next.js Web App", status: "Running", url: "https://forge.local", commit: "5b8d10e", updated: "10 mins ago" },
    { name: "background-worker", type: "Python Queue Daemon", status: "Running", url: "N/A", commit: "cd90e1f", updated: "1 hour ago" },
    { name: "auth-service", type: "Node.js Microservice", status: "Stopped", url: "https://auth.forge.local", commit: "ff29a12", updated: "Yesterday" }
  ];

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-900 bg-slate-950 flex flex-col justify-between p-6">
        <div className="flex flex-col gap-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              F
            </div>
            <span className="font-semibold text-lg tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              ForgeDeploy
            </span>
          </div>

          <nav className="flex flex-col gap-2">
            <Link
              href="/dashboard"
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium bg-indigo-600/10 text-indigo-400 border border-indigo-500/20"
            >
              <span>📁</span> Projects
            </Link>
            <a
              href="#"
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900/50 transition-all"
            >
              <span>⚙️</span> Infrastructure
            </a>
            <a
              href="#"
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900/50 transition-all"
            >
              <span>🔐</span> Secrets
            </a>
            <a
              href="#"
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900/50 transition-all"
            >
              <span>📈</span> Monitoring
            </a>
          </nav>
        </div>

        <div className="border-t border-slate-900 pt-6">
          <Link href="/" className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-2">
            <span>←</span> Back to Landing
          </Link>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-screen bg-slate-950">
        {/* Top Navbar */}
        <header className="border-b border-slate-900 px-8 py-5 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-white">Default Workspace</h1>
            <p className="text-xs text-slate-500">Local Docker Engine socket connection active</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5 text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Agent Connected
            </span>
          </div>
        </header>

        {/* Dashboard Grid */}
        <div className="flex-1 p-8 flex flex-col gap-8 max-w-7xl w-full mx-auto">
          {/* Header Stats */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card title="Active Services" description="Currently active container services.">
              <p className="text-3xl font-extrabold text-white">3 / 4</p>
            </Card>
            <Card title="Total Deployments" description="Lifetime builds processed.">
              <p className="text-3xl font-extrabold text-indigo-400">42</p>
            </Card>
            <Card title="CPU Load" description="Average system CPU usage.">
              <p className="text-3xl font-extrabold text-purple-400">12.4%</p>
            </Card>
            <Card title="RAM Usage" description="Control plane & host memory usage.">
              <p className="text-3xl font-extrabold text-pink-400">2.1 GB / 8.0 GB</p>
            </Card>
          </div>

          {/* Services List Table */}
          <div className="bg-slate-900/40 border border-slate-900 rounded-xl overflow-hidden backdrop-blur-sm">
            <div className="px-6 py-4 border-b border-slate-900 flex justify-between items-center">
              <h2 className="font-semibold text-white">Services</h2>
              <button className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all">
                + New Service
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/50 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-900">
                  <tr>
                    <th className="px-6 py-4">Service</th>
                    <th className="px-6 py-4">Type</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Source Commit</th>
                    <th className="px-6 py-4">Last Updated</th>
                    <th className="px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900">
                  {mockServices.map((service, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/20 transition-all">
                      <td className="px-6 py-4">
                        <div className="font-medium text-white">{service.name}</div>
                        {service.url !== "N/A" ? (
                          <a href={service.url} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline">
                            {service.url}
                          </a>
                        ) : (
                          <span className="text-xs text-slate-600">No public URL</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-400">{service.type}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border ${
                          service.status === "Running"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-slate-500/10 text-slate-400 border-slate-500/20"
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${service.status === "Running" ? "bg-emerald-400" : "bg-slate-500"}`} />
                          {service.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-400">{service.commit}</td>
                      <td className="px-6 py-4 text-slate-400 text-xs">{service.updated}</td>
                      <td className="px-6 py-4 text-xs font-semibold flex gap-3 text-slate-400">
                        <button className="hover:text-indigo-400 transition-colors">Configure</button>
                        <button className="hover:text-rose-400 transition-colors">Logs</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
