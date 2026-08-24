'use client';

import React from 'react';
import { useCivic } from '../context/CivicContext';

interface ThemeToggleProps {
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '' }) => {
  const { theme, toggleTheme } = useCivic();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`relative inline-flex items-center justify-between w-14 h-8 p-1 rounded-sm bg-slate-800/40 dark:bg-slate-700/50 backdrop-blur-md border border-white/20 dark:border-white/10 shadow-inner transition-colors duration-300 cursor-pointer focus:outline-none ${className}`}
      aria-label="Toggle Theme (Dark / Light)"
      title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
    >
      <span className="text-xs ml-1 select-none">🌙</span>
      <span className="text-xs mr-1 select-none">☀️</span>

      {/* Sliding Glass Knob */}
      <span
        className={`absolute top-0.5 w-7 h-7 rounded-sm bg-white/90 dark:bg-amber-400  backdrop-blur-sm transform transition-transform duration-300 flex items-center justify-center text-xs ${
          isDark ? 'left-0.5 text-slate-900 font-bold' : 'left-[1.65rem] text-amber-900 font-bold'
        }`}
      >
        {isDark ? '🌙' : '☀️'}
      </span>
    </button>
  );
};
