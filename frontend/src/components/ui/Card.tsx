import React from 'react';

interface CardProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function Card({ title, description, children }: CardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-md hover:border-indigo-500/30 transition-all duration-300">
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      {description && <p className="text-slate-400 text-sm mb-4">{description}</p>}
      {children}
    </div>
  );
}
