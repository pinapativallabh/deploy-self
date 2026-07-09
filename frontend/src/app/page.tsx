import Link from "next/link";

export default function Home() {
  return (
    <div className="flex-1 flex flex-col justify-between bg-slate-950 text-slate-100 font-sans min-h-screen">
      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
            F
          </div>
          <span className="font-semibold text-lg tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
            ForgeDeploy
          </span>
        </div>
        <nav className="flex gap-6 text-sm text-slate-400 font-medium">
          <Link href="/dashboard" className="hover:text-indigo-400 transition-colors">
            Dashboard
          </Link>
          <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-indigo-400 transition-colors">
            GitHub
          </a>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20 max-w-6xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-xs font-semibold tracking-wide mb-6">
          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          Self-Hosted PaaS Platform
        </div>
        
        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white mb-6">
          Deploy Your Applications <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-500">
            Without the Markup
          </span>
        </h1>

        <p className="text-base md:text-xl text-slate-400 max-w-2xl mb-10 leading-relaxed">
          ForgeDeploy runs on your own hardware. Enjoy automated Git-triggered builds, environment variables management, and container metrics with zero configuration.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-16 justify-center">
          <Link
            href="/dashboard"
            className="px-8 py-3 rounded-lg font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 transition-all hover:-translate-y-0.5 duration-200"
          >
            Launch Dashboard
          </Link>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="px-8 py-3 rounded-lg font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-all hover:-translate-y-0.5 duration-200"
          >
            Documentation
          </a>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid md:grid-cols-3 gap-6 w-full text-left">
          <div className="p-6 rounded-xl border border-slate-900 bg-slate-900/40 backdrop-blur-sm hover:border-slate-800 transition-all duration-300">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4 font-bold">
              🚀
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Automated GitOps</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Push to main, and let our worker service handle checkout, Docker compilation, and deployment automatically.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-900 bg-slate-900/40 backdrop-blur-sm hover:border-slate-800 transition-all duration-300">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 mb-4 font-bold">
              📊
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Unified Control Plane</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Configure environments, inspect real-time logs, and monitor project services through a single central dashboard.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-900 bg-slate-900/40 backdrop-blur-sm hover:border-slate-800 transition-all duration-300">
            <div className="w-10 h-10 rounded-lg bg-pink-500/10 flex items-center justify-center text-pink-400 mb-4 font-bold">
              🛡️
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Resource Efficiency</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Lightweight control plane written in FastAPI and Redis. Save RAM and CPU cycles for your user apps.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-600 bg-slate-950/50">
        &copy; {new Date().getFullYear()} ForgeDeploy. All rights reserved.
      </footer>
    </div>
  );
}
