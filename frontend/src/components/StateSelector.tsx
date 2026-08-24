'use client';

import React, { useState, useMemo } from 'react';
import { useCivic } from '../context/CivicContext';

interface StateSelectorProps {
  onLocationDetected?: (lat: number, lon: number, address: string) => void;
  className?: string;
}

export const StateSelector: React.FC<StateSelectorProps> = ({ onLocationDetected, className = '' }) => {
  const { selectedState, setSelectedState, states, t, selectedLanguage } = useCivic();
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [detectingGps, setDetectingGps] = useState(false);
  const [gpsMessage, setGpsMessage] = useState<string | null>(null);

  // Filtered states based on search query
  const filteredStates = useMemo(() => {
    if (!searchQuery.trim()) return states;
    const q = searchQuery.toLowerCase();
    return states.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.code.toLowerCase().includes(q) ||
        (s.local_name && s.local_name.toLowerCase().includes(q)) ||
        (s.capital && s.capital.toLowerCase().includes(q))
    );
  }, [states, searchQuery]);

  // Selected State object
  const currentStateObj = states.find((s) => s.code === selectedState);

  // Quick State Chips
  const popularStateCodes = ['KA', 'MH', 'TN', 'DL', 'UP', 'TG', 'KL', 'GJ', 'WB', 'RJ'];

  // GPS Geolocation Handler
  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      setGpsMessage('Geolocation is not supported by your browser.');
      return;
    }

    setDetectingGps(true);
    setGpsMessage(t('form.detecting_location'));

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;

        try {
          const res = await fetch(`/api/v1/location/reverse-geocode?latitude=${lat}&longitude=${lon}`);
          const data = await res.json();

          if (data && data.state_code) {
            setSelectedState(data.state_code);
            setGpsMessage(`📍 Detected: ${data.state_name || data.state_code} (${data.district_name || 'India'})`);
          } else {
            setGpsMessage(`📍 Coordinates: ${lat.toFixed(4)}, ${lon.toFixed(4)}`);
          }

          if (onLocationDetected) {
            onLocationDetected(lat, lon, data.address || `${lat.toFixed(4)}, ${lon.toFixed(4)}`);
          }
        } catch (err) {
          console.warn('Geocoding error:', err);
          setGpsMessage(`📍 GPS fixed: ${lat.toFixed(4)}, ${lon.toFixed(4)}`);
          if (onLocationDetected) {
            onLocationDetected(lat, lon, `${lat.toFixed(4)}, ${lon.toFixed(4)}`);
          }
        } finally {
          setDetectingGps(false);
        }
      },
      (err) => {
        console.warn('Geolocation denied or failed:', err);
        setDetectingGps(false);
        setGpsMessage('Location access denied. Please select your state manually below.');
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  return (
    <div className={`luxury-panel p-5 md:p-7 ${className}`}>
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5 pb-4 border-b border-slate-200/60 dark:border-white/10">
        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono font-bold tracking-wide bg-white/10 text-white border border-amber-500/25">
            <span className="w-2 h-2 rounded-sm bg-amber-500 animate-pulse"></span>
            PAN-BHARAT LGD DIRECTORY
          </span>
          <h3 className="text-xl md:text-2xl font-extrabold tracking-tight mt-1.5 text-white">
            {t('hero.where_reporting')}
          </h3>
        </div>

        {/* Currently Selected Glass Badge */}
        <div className="flex items-center gap-2 px-3.5 py-2 luxury-card ">
          <span className="text-xs font-semibold text-[#a1a1aa]">{t('hero.state_selected')}:</span>
          <span className="text-sm font-black text-white">
            {currentStateObj ? `${currentStateObj.name}` : selectedState}
          </span>
          <span className="text-xs font-mono px-1.5 py-0.5 rounded-md bg-slate-200/70 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold">
            {selectedState}
          </span>
          {currentStateObj?.local_name && (
            <span className="text-xs font-medium text-[#a1a1aa] hidden sm:inline">
              ({currentStateObj.local_name})
            </span>
          )}
        </div>
      </div>

      {/* Action Row: Use Location OR Manual Selection */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 mb-5">
        {/* Option A: Use GPS Location */}
        <button
          type="button"
          onClick={handleUseMyLocation}
          disabled={detectingGps}
          className="flex items-center justify-center gap-2.5 px-5 py-3.5 rounded-sm bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-sm md:text-base  shadow-emerald-500/20 border border-white/20 transition-all transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 cursor-pointer"
        >
          {detectingGps ? (
            <>
              <span className="animate-spin text-lg">⏳</span>
              <span>{t('form.detecting_location')}</span>
            </>
          ) : (
            <>
              <span className="text-lg">📍</span>
              <span>{t('hero.use_location')}</span>
            </>
          )}
        </button>

        {/* Option B: Open Manual State Picker */}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center justify-between px-5 py-3.5 rounded-sm bg-[#1a1a1a] hover:bg-white dark:hover:bg-slate-700/90 text-slate-800 dark:text-white font-bold text-sm md:text-base border border-slate-200/80 dark:border-white/10  transition-all transform hover:-translate-y-0.5 cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <span className="text-lg">🏛</span>
            <span>{currentStateObj ? currentStateObj.name : t('hero.select_state_manual')}</span>
          </span>
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-sm bg-amber-500/20 text-amber-700 dark:text-amber-300">
            {isOpen ? '▲ CLOSE' : '▼ 36 STATES / UTS'}
          </span>
        </button>
      </div>

      {/* GPS Status Message */}
      {gpsMessage && (
        <div className="mb-4 p-3 luxury-card text-xs md:text-sm font-semibold text-slate-700 dark:text-slate-200 flex items-center justify-between">
          <span>{gpsMessage}</span>
          <button
            type="button"
            onClick={() => setGpsMessage(null)}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white font-bold ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Quick Chips for Popular States */}
      <div>
        <span className="text-xs font-mono font-bold uppercase text-[#a1a1aa] block mb-2">
          {t('hero.popular_states')}
        </span>
        <div className="flex flex-wrap gap-2">
          {popularStateCodes.map((code) => {
            const s = states.find((st) => st.code === code);
            if (!s) return null;
            const isSelected = s.code === selectedState;
            return (
              <button
                key={s.code}
                type="button"
                onClick={() => setSelectedState(s.code)}
                className={`px-3 py-1.5 rounded-sm text-xs font-bold transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-amber-500 text-slate-950  shadow-amber-500/30 scale-105'
                    : 'bg-white/80 dark:bg-slate-800/70 text-slate-700 dark:text-slate-300 hover:bg-amber-50 dark:hover:bg-slate-700/80 border border-slate-200/70 dark:border-white/10'
                }`}
              >
                {s.name} {s.local_name ? `(${s.local_name})` : ''}
              </button>
            );
          })}
        </div>
      </div>

      {/* Expanded State Search & Full List Grid */}
      {isOpen && (
        <div className="mt-5 p-4 luxury-panel shadow-2xl">
          {/* Search Bar */}
          <div className="relative mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('hero.search_state_placeholder')}
              className="w-full px-4 py-3 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-slate-300/60 dark:border-white/15 text-sm font-semibold text-white placeholder-slate-400 focus:ring-2 focus:ring-amber-500/50"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-3 text-xs font-mono font-bold px-2 py-1 rounded-md bg-slate-300/80 dark:bg-slate-700 text-slate-700 dark:text-slate-200"
              >
                CLEAR
              </button>
            )}
          </div>

          <div className="text-xs font-mono font-bold uppercase text-[#a1a1aa] mb-3">
            {t('hero.all_states')} ({filteredStates.length})
          </div>

          {/* Grid of all 36 States & UTs */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5 max-h-64 overflow-y-auto p-1">
            {filteredStates.map((s) => {
              const isSelected = s.code === selectedState;
              return (
                <button
                  key={s.code}
                  type="button"
                  onClick={() => {
                    setSelectedState(s.code);
                    setIsOpen(false);
                  }}
                  className={`flex flex-col text-left p-2.5 rounded-sm border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-amber-500/20 dark:bg-amber-500/30 border-amber-500 text-amber-900 dark:text-amber-300 font-bold '
                      : 'bg-white/60 dark:bg-slate-800/50 border-slate-200/70 dark:border-white/5 text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/60'
                  }`}
                >
                  <span className="font-bold text-xs md:text-sm">
                    {s.name} <span className="text-[10px] font-mono text-slate-400">[{s.code}]</span>
                  </span>
                  {s.local_name && (
                    <span className="text-[11px] text-[#a1a1aa] font-normal truncate mt-0.5">
                      {s.local_name}
                    </span>
                  )}
                  {s.capital && (
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono mt-0.5">
                      Cap: {s.capital}
                    </span>
                  )}
                </button>
              );
            })}
            {filteredStates.length === 0 && (
              <div className="col-span-full py-6 text-center text-sm font-mono text-slate-500">
                No state or UT found matching "{searchQuery}"
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
