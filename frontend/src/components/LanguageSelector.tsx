'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useCivic } from '../context/CivicContext';
import { LanguageCode } from '../i18n/translations';

interface LanguageSelectorProps {
  className?: string;
  isCompact?: boolean;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({ className = '', isCompact = false }) => {
  const { selectedLanguage, setSelectedLanguage, supportedLanguages, t } = useCivic();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLangObj = supportedLanguages.find((l) => l.code === selectedLanguage) || supportedLanguages[0];

  const handleSelect = (code: LanguageCode) => {
    setSelectedLanguage(code);
    setIsOpen(false);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={dropdownRef} className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-sm bg-white/70 dark:bg-slate-800/60 hover:bg-white/90 dark:hover:bg-slate-700/80 backdrop-blur-md border border-slate-300/60 dark:border-white/15 text-white text-xs md:text-sm font-bold  transition-all cursor-pointer"
        aria-label="Select Language"
      >
        <span>{currentLangObj.flag}</span>
        <span>{currentLangObj.nativeName}</span>
        <span className="text-[10px] text-slate-400 dark:text-slate-300">▼</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-52 p-2 rounded-sm bg-white/90 dark:bg-slate-900/85 backdrop-blur-2xl border border-slate-200/80 dark:border-white/20 shadow-2xl z-50 animate-in fade-in zoom-in duration-150">
          <div className="text-[10px] font-mono font-bold uppercase px-2.5 py-1.5 text-slate-400 dark:text-slate-400 border-b border-slate-200/50 dark:border-white/10 mb-1">
            {t('nav.select_language')} / BHARAT
          </div>
          {supportedLanguages.map((lang) => {
            const isSelected = lang.code === selectedLanguage;
            return (
              <button
                key={lang.code}
                type="button"
                onClick={() => handleSelect(lang.code)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-sm text-xs font-semibold transition-all text-left mb-1 cursor-pointer ${
                  isSelected
                    ? 'bg-amber-500/20 text-white font-bold border border-amber-500/30'
                    : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100/80 dark:hover:bg-slate-800/70'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">{lang.flag}</span>
                  <span>{lang.nativeName}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400 dark:text-slate-400 uppercase">
                  {lang.code}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
