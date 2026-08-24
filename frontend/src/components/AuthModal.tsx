'use client';

import React, { useState } from 'react';
import { useCivic } from '../context/CivicContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'login' | 'signup';
  onSuccess?: (role?: string) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initialMode = 'login',
  onSuccess,
}) => {
  const { login, register, t, states, selectedState, selectedLanguage } = useCivic();
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);

  // Login Form
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Signup Form
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPhone, setSignupPhone] = useState('');
  const [signupState, setSignupState] = useState(selectedState || 'KA');
  const [signupDistrict, setSignupDistrict] = useState('');
  const [signupLanguage, setSignupLanguage] = useState(selectedLanguage || 'en');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirmPassword, setSignupConfirmPassword] = useState('');
  const [agreeTerms, setAgreeTerms] = useState(true);

  // UI States
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  // Handle Login
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setLoading(true);

    const res = await login(loginEmail, loginPassword);
    setLoading(false);

    if (res.success) {
      if (onSuccess) onSuccess(res.role);
      onClose();
    } else {
      setErrorMessage(res.error || t('login.err_invalid'));
    }
  };

  // Quick Demo Account Auto-Fill
  const fillDemoAccount = (email: string) => {
    setLoginEmail(email);
    setLoginPassword('CivicOps2026!');
    setErrorMessage(null);
  };

  // Handle Signup
  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (signupPassword !== signupConfirmPassword) {
      setErrorMessage(t('signup.err_mismatch'));
      return;
    }

    if (!agreeTerms) {
      setErrorMessage(t('signup.err_terms'));
      return;
    }

    setLoading(true);
    const res = await register({
      email: signupEmail,
      full_name: signupName,
      phone: signupPhone || undefined,
      password: signupPassword,
      state_code: signupState,
      district_name: signupDistrict || undefined,
      preferred_language: signupLanguage,
      role: 'citizen',
    });
    setLoading(false);

    if (res.success) {
      setSuccessMessage(t('signup.success'));
      setTimeout(() => {
        if (onSuccess) onSuccess('citizen');
        onClose();
      }, 1000);
    } else {
      setErrorMessage(res.error || 'Registration failed');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
      <div className="relative w-full max-w-lg luxury-panel max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-200/60 dark:border-white/10">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">🇮🇳</span>
            <span className="font-extrabold text-lg text-white">
              {mode === 'login' ? t('login.title') : t('signup.title')}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-sm flex items-center justify-center bg-slate-200/70 dark:bg-slate-800 text-[#a1a1aa] hover:bg-slate-300 dark:hover:bg-slate-700 text-sm font-bold transition-all cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="grid grid-cols-2 p-1.5 mx-5 mt-4 rounded-sm bg-slate-100 dark:bg-slate-800/60 border border-slate-200/70 dark:border-white/10">
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setErrorMessage(null);
            }}
            className={`py-2.5 rounded-sm text-center text-xs font-bold transition-all cursor-pointer ${
              mode === 'login'
                ? 'bg-white dark:bg-slate-700 text-white '
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            🔑 {t('nav.login')}
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('signup');
              setErrorMessage(null);
            }}
            className={`py-2.5 rounded-sm text-center text-xs font-bold transition-all cursor-pointer ${
              mode === 'signup'
                ? 'bg-white dark:bg-slate-700 text-emerald-600 dark:text-emerald-400 '
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            📝 {t('nav.signup')}
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6">
          {/* Error Alert */}
          {errorMessage && (
            <div className="mb-4 p-3.5 rounded-sm bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 font-semibold text-xs md:text-sm">
              ⚠️ {errorMessage}
            </div>
          )}

          {/* Success Alert */}
          {successMessage && (
            <div className="mb-4 p-3.5 rounded-sm bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 font-semibold text-xs md:text-sm">
              ✅ {successMessage}
            </div>
          )}

          {/* =================== LOGIN MODE =================== */}
          {mode === 'login' && (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <p className="text-xs font-medium text-[#a1a1aa]">
                {t('login.welcome')}
              </p>

              {/* Email */}
              <div>
                <label className="block text-xs font-bold uppercase mb-1.5 text-slate-700 dark:text-slate-300">
                  {t('login.email_label')} *
                </label>
                <input
                  type="text"
                  required
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder={t('login.email_placeholder')}
                  className="w-full px-4 py-3 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-amber-500/50"
                />
              </div>

              {/* Password */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-bold uppercase text-slate-700 dark:text-slate-300">
                    {t('login.password_label')} *
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-xs font-medium text-white hover:underline cursor-pointer"
                  >
                    {showPassword ? t('login.hide_password') : t('login.show_password')}
                  </button>
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder={t('login.password_placeholder')}
                  className="w-full px-4 py-3 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-amber-500/50"
                />
              </div>

              {/* Login Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full luxury-btn-amber py-3.5 text-base cursor-pointer"
              >
                {loading ? t('login.loading') : `⚡ ${t('login.button')}`}
              </button>

              {/* Quick Demo Credentials Panel */}
              <div className="mt-5 pt-4 border-t border-slate-200/60 dark:border-white/10">
                <span className="text-[11px] font-mono font-bold uppercase text-slate-400 block mb-2.5">
                  {t('login.demo_credentials_title')}
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => fillDemoAccount('super_admin@civicops.in')}
                    className="p-2 rounded-sm bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 text-[11px] font-bold text-purple-700 dark:text-purple-300 text-left cursor-pointer truncate"
                  >
                    👑 Super Admin
                  </button>
                  <button
                    type="button"
                    onClick={() => fillDemoAccount('ka_admin@civicops.in')}
                    className="p-2 rounded-sm bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 text-[11px] font-bold text-blue-700 dark:text-blue-300 text-left cursor-pointer truncate"
                  >
                    🏛 State KA
                  </button>
                  <button
                    type="button"
                    onClick={() => fillDemoAccount('blr_admin@bbmp.gov.in')}
                    className="p-2 rounded-sm bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 text-[11px] font-bold text-emerald-700 dark:text-emerald-300 text-left cursor-pointer truncate"
                  >
                    🏢 BBMP Admin
                  </button>
                  <button
                    type="button"
                    onClick={() => fillDemoAccount('field_blr@bbmp.gov.in')}
                    className="p-2 rounded-sm bg-orange-500/10 hover:bg-orange-500/20 border border-orange-500/20 text-[11px] font-bold text-orange-700 dark:text-orange-300 text-left cursor-pointer truncate"
                  >
                    👷 Field Crew
                  </button>
                  <button
                    type="button"
                    onClick={() => fillDemoAccount('citizen@civicops.in')}
                    className="p-2 rounded-sm bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 text-[11px] font-bold text-amber-700 dark:text-amber-300 text-left cursor-pointer truncate col-span-2 sm:col-span-2"
                  >
                    👤 Verified Citizen
                  </button>
                </div>
              </div>

              {/* Guest Link */}
              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={onClose}
                  className="text-xs font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-white underline cursor-pointer"
                >
                  {t('login.guest_link')}
                </button>
              </div>
            </form>
          )}

          {/* =================== SIGNUP MODE =================== */}
          {mode === 'signup' && (
            <form onSubmit={handleSignupSubmit} className="space-y-3.5">
              <p className="text-xs font-medium text-[#a1a1aa] mb-2">
                {t('signup.welcome')}
              </p>

              {/* Name & Phone */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase mb-1 text-slate-700 dark:text-slate-300">
                    {t('signup.name_label')} *
                  </label>
                  <input
                    type="text"
                    required
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    placeholder={t('signup.name_placeholder')}
                    className="w-full px-3.5 py-2.5 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase mb-1 text-slate-700 dark:text-slate-300">
                    {t('signup.phone_label')}
                  </label>
                  <input
                    type="tel"
                    value={signupPhone}
                    onChange={(e) => setSignupPhone(e.target.value)}
                    placeholder={t('signup.phone_placeholder')}
                    className="w-full px-3.5 py-2.5 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-emerald-500/50"
                  />
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="block text-xs font-bold uppercase mb-1 text-slate-700 dark:text-slate-300">
                  {t('signup.email_label')} *
                </label>
                <input
                  type="email"
                  required
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder={t('signup.email_placeholder')}
                  className="w-full px-3.5 py-2.5 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-emerald-500/50"
                />
              </div>

              {/* State & District */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase mb-1 text-slate-700 dark:text-slate-300">
                    {t('signup.state_label')} *
                  </label>
                  <select
                    value={signupState}
                    onChange={(e) => setSignupState(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-emerald-500/50"
                  >
                    {states.map((s) => (
                      <option key={s.code} value={s.code}>
                        {s.name} ({s.code})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase mb-1 text-slate-700 dark:text-slate-300">
                    {t('signup.district_label')}
                  </label>
                  <input
                    type="text"
                    value={signupDistrict}
                    onChange={(e) => setSignupDistrict(e.target.value)}
                    placeholder={t('signup.district_placeholder')}
                    className="w-full px-3.5 py-2.5 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-emerald-500/50"
                  />
                </div>
              </div>

              {/* Password & Confirm */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase mb-1 text-slate-700 dark:text-slate-300">
                    {t('signup.password_label')} *
                  </label>
                  <input
                    type="password"
                    required
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full px-3.5 py-2.5 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase mb-1 text-slate-700 dark:text-slate-300">
                    {t('signup.confirm_password_label')} *
                  </label>
                  <input
                    type="password"
                    required
                    value={signupConfirmPassword}
                    onChange={(e) => setSignupConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full px-3.5 py-2.5 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-emerald-500/50"
                  />
                </div>
              </div>

              {/* Terms Checkbox */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="terms"
                  checked={agreeTerms}
                  onChange={(e) => setAgreeTerms(e.target.checked)}
                  className="w-4 h-4 rounded-md accent-emerald-500"
                />
                <label htmlFor="terms" className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  {t('signup.terms')}
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 mt-2 rounded-sm bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-extrabold text-sm  shadow-emerald-500/25 border border-white/20 transition-all transform hover:-translate-y-0.5 disabled:opacity-50 cursor-pointer"
              >
                {loading ? t('signup.loading') : `📝 ${t('signup.button')}`}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
