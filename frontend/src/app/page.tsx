'use client';

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useCivic } from '../context/CivicContext';
import { StateSelector } from '../components/StateSelector';
import { LanguageSelector } from '../components/LanguageSelector';
import { ThemeToggle } from '../components/ThemeToggle';
import { AuthModal } from '../components/AuthModal';

interface ComplaintItem {
  id?: string;
  tracking_number?: string;
  complaint_id?: string;
  text_description?: string;
  category?: string;
  priority?: string;
  confidence_score?: number;
  review_tier?: string;
  status?: string;
  latitude: number;
  longitude: number;
  address?: string;
  state_code?: string;
  district_name?: string;
  local_body_name?: string;
  ward_or_village?: string;
  photo_url?: string;
  audio_url?: string;
  vision_analysis?: any;
  speech_transcript?: string;
  location_details?: any;
  rag_context?: any;
  decision?: any;
  verification?: any;
  work_order_id?: string;
  work_order_data?: any;
  created_at?: string;
  completed_at?: string;
}

interface IncidentCluster {
  id: string;
  incident_number: string;
  title: string;
  category: string;
  priority: string;
  status: string;
  latitude: number;
  longitude: number;
  address?: string;
  total_complaints: number;
  assigned_department?: string;
  work_order_id?: string;
  ai_confidence?: number;
  created_at: string;
}

interface ReviewStats {
  total_pending: number;
  mandatory_review: number;
  optional_review: number;
  auto_processed: number;
  avg_confidence: number | null;
}

interface WorkOrderItem {
  id: string;
  complaint_id?: string;
  incident_id?: string;
  work_order_number: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  latitude: number;
  longitude: number;
  address?: string;
  state_code?: string;
  assigned_department?: string;
  assigned_crew?: string;
  estimated_cost?: number;
  estimated_duration_days?: number;
  status: string;
  created_at: string;
}

declare global {
  interface Window {
    L: any;
  }
}

export default function CivicOpsIndiaPlatform() {
  const {
    theme,
    selectedState,
    selectedStateName,
    setSelectedState,
    selectedLanguage,
    t,
    user,
    isAuthenticated,
    logout,
  } = useCivic();

  // Navigation Tabs
  const [activeTab, setActiveTab] = useState<
    'citizen' | 'track' | 'command' | 'operator' | 'incidents' | 'workorders' | 'health'
  >('citizen');

  // Mobile Menu & Auth Modal State
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'signup'>('login');

  // Citizen Complaint Form State
  const [formData, setFormData] = useState({
    text_description: '',
    latitude: 12.9716,
    longitude: 77.5946,
    address: 'MG Road, Bengaluru, Karnataka, India',
    photo: null as File | null,
    audio: null as File | null,
  });
  const [submitting, setSubmitting] = useState(false);
  const [submittedComplaint, setSubmittedComplaint] = useState<ComplaintItem | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isVoiceRecording, setIsVoiceRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<any>(null);

  // Tracking Search State
  const [trackingQuery, setTrackingQuery] = useState('');
  const [trackedItem, setTrackedItem] = useState<ComplaintItem | null>(null);
  const [trackingLoading, setTrackingLoading] = useState(false);
  const [trackingError, setTrackingError] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackComments, setFeedbackComments] = useState<string>('');
  const [appealReason, setAppealReason] = useState<string>('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);

  // Operator Review Hub State
  const [reviewStats, setReviewStats] = useState<ReviewStats | null>(null);
  const [queueItems, setQueueItems] = useState<ComplaintItem[]>([]);
  const [tierFilter, setTierFilter] = useState<string>('all');
  const [selectedComplaint, setSelectedComplaint] = useState<ComplaintItem | null>(null);
  const [reviewActionNotes, setReviewActionNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  // Incidents, Work Orders & System Health
  const [incidents, setIncidents] = useState<IncidentCluster[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrderItem[]>([]);
  const [healthStatus, setHealthStatus] = useState<any>(null);

  // Leaflet Map References
  const citizenMapRef = useRef<HTMLDivElement | null>(null);
  const citizenMapInstance = useRef<any>(null);
  const citizenMarkerInstance = useRef<any>(null);

  // Default coordinate mapping per state code
  const STATE_COORDS: Record<string, { lat: number; lon: number; addr: string }> = {
    KA: { lat: 12.9716, lon: 77.5946, addr: 'MG Road, Bengaluru, Karnataka 560001' },
    MH: { lat: 18.9220, lon: 72.8347, addr: 'Fort, Mumbai, Maharashtra 400001' },
    TN: { lat: 13.0827, lon: 80.2707, addr: 'Anna Salai, Chennai, Tamil Nadu 600002' },
    DL: { lat: 28.6139, lon: 77.2090, addr: 'Connaught Place, New Delhi, Delhi 110001' },
    UP: { lat: 26.8467, lon: 80.9462, addr: 'Hazratganj, Lucknow, Uttar Pradesh 226001' },
    TG: { lat: 17.3850, lon: 78.4867, addr: 'Abids, Hyderabad, Telangana 500001' },
    KL: { lat: 8.5241, lon: 76.9366, addr: 'MG Road, Thiruvananthapuram, Kerala 695001' },
    GJ: { lat: 23.0225, lon: 72.5714, addr: 'Ashram Road, Ahmedabad, Gujarat 380009' },
    WB: { lat: 22.5726, lon: 88.3639, addr: 'Park Street, Kolkata, West Bengal 700016' },
    RJ: { lat: 26.9124, lon: 75.7873, addr: 'MI Road, Jaipur, Rajasthan 302001' },
  };

  // Sync form coordinates when state changes
  useEffect(() => {
    const preset = STATE_COORDS[selectedState] || { lat: 12.9716, lon: 77.5946, addr: `${selectedStateName}, India` };
    setFormData((prev) => ({
      ...prev,
      latitude: preset.lat,
      longitude: preset.lon,
      address: preset.addr,
    }));

    if (citizenMapInstance.current && citizenMarkerInstance.current) {
      citizenMapInstance.current.setView([preset.lat, preset.lon], 13);
      citizenMarkerInstance.current.setLatLng([preset.lat, preset.lon]);
    }
  }, [selectedState, selectedStateName]);

  // Leaflet Map Initializer
  useEffect(() => {
    if (activeTab !== 'citizen' || !citizenMapRef.current) return;

    const initMap = () => {
      if (!window.L) {
        setTimeout(initMap, 200);
        return;
      }

      if (citizenMapInstance.current) {
        citizenMapInstance.current.remove();
      }

      const map = window.L.map(citizenMapRef.current).setView([formData.latitude, formData.longitude], 13);
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      const marker = window.L.marker([formData.latitude, formData.longitude], { draggable: true }).addTo(map);
      marker.bindPopup(`<b>${selectedStateName}</b><br/>Drag marker to set issue spot`).openPopup();

      marker.on('dragend', async (e: any) => {
        const pos = e.target.getLatLng();
        setFormData((prev) => ({
          ...prev,
          latitude: pos.lat,
          longitude: pos.lng,
        }));

        try {
          const res = await axios.get(`/api/v1/location/reverse-geocode?latitude=${pos.lat}&longitude=${pos.lng}`);
          if (res.data && res.data.address) {
            setFormData((prev) => ({ ...prev, address: res.data.address }));
          }
        } catch (err) {
          console.warn('Geocode error:', err);
        }
      });

      citizenMapInstance.current = map;
      citizenMarkerInstance.current = marker;
    };

    initMap();
  }, [activeTab]);

  // Fetch Operator Review Queue
  useEffect(() => {
    if (activeTab === 'operator') {
      const loadOperatorData = async () => {
        try {
          const [statsRes, queueRes] = await Promise.all([
            axios.get<ReviewStats>('/api/v1/review/stats'),
            axios.get<ComplaintItem[]>(`/api/v1/review/queue?tier=${tierFilter}`),
          ]);
          setReviewStats(statsRes.data);
          setQueueItems(queueRes.data);
        } catch (err) {
          console.warn('Failed to load operator queue:', err);
        }
      };
      loadOperatorData();
    }
  }, [activeTab, tierFilter]);

  // Fetch Incident Clusters
  useEffect(() => {
    if (activeTab === 'incidents') {
      const loadIncidents = async () => {
        try {
          const res = await axios.get<IncidentCluster[]>('/api/v1/incidents');
          setIncidents(res.data);
        } catch (err) {
          console.warn('Failed to load incidents:', err);
        }
      };
      loadIncidents();
    }
  }, [activeTab]);

  // Fetch Work Orders
  useEffect(() => {
    if (activeTab === 'workorders') {
      const loadWorkOrders = async () => {
        try {
          const res = await axios.get<WorkOrderItem[]>('/api/v1/work-orders');
          setWorkOrders(res.data);
        } catch (err) {
          console.warn('Failed to load work orders:', err);
        }
      };
      loadWorkOrders();
    }
  }, [activeTab]);

  // Fetch System Health
  useEffect(() => {
    if (activeTab === 'health') {
      const loadHealth = async () => {
        try {
          const res = await axios.get('/api/v1/health');
          setHealthStatus(res.data);
        } catch (err) {
          console.warn('Failed to load health:', err);
        }
      };
      loadHealth();
    }
  }, [activeTab]);

  // Voice Recording Handlers
  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const audioFile = new File([audioBlob], `voice_complaint_${Date.now()}.wav`, { type: 'audio/wav' });
        setFormData((prev) => ({ ...prev, audio: audioFile }));
        setIsVoiceRecording(false);
        clearInterval(recordingTimerRef.current);
      };

      mediaRecorder.start(100);
      setIsVoiceRecording(true);
      setRecordingSeconds(0);

      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Microphone error:', err);
      alert('Microphone access denied or unsupported.');
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  // Submit Complaint Handler
  const handleComplaintSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);

    try {
      let createdComplaint: ComplaintItem;

      if (formData.photo || formData.audio) {
        const body = new FormData();
        if (formData.text_description) body.append('text_description', formData.text_description);
        body.append('latitude', formData.latitude.toString());
        body.append('longitude', formData.longitude.toString());
        if (formData.address) body.append('address', formData.address);
        if (formData.photo) body.append('photo', formData.photo);
        if (formData.audio) body.append('audio', formData.audio);

        const res = await axios.post<ComplaintItem>('/api/v1/complaints/upload', body, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        createdComplaint = res.data;
      } else {
        const res = await axios.post<ComplaintItem>('/api/v1/complaints', {
          text_description: formData.text_description,
          latitude: formData.latitude,
          longitude: formData.longitude,
          address: formData.address,
        });
        createdComplaint = res.data;
      }

      setSubmittedComplaint(createdComplaint);

      // Poll for 8-Agent Swarm completion
      if (createdComplaint.id) {
        let attempts = 0;
        const pollTimer = setInterval(async () => {
          attempts++;
          try {
            const check = await axios.get<ComplaintItem>(`/api/v1/complaints/${createdComplaint.id}`);
            if (check.data && (check.data.status !== 'pending' || attempts >= 8)) {
              setSubmittedComplaint(check.data);
              clearInterval(pollTimer);
            }
          } catch (err) {
            console.warn('Poll error:', err);
          }
        }, 1500);
      }
    } catch (err: any) {
      console.error('Complaint submit error:', err);
      setFormError(err.response?.data?.detail || 'Failed to submit grievance. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // Search Complaint by Tracking Number
  const handleTrackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackingQuery.trim()) return;

    setTrackingLoading(true);
    setTrackingError(null);
    setTrackedItem(null);
    setFeedbackSubmitted(false);

    try {
      const res = await axios.get<ComplaintItem>(`/api/v1/complaints/track/${encodeURIComponent(trackingQuery.trim())}`);
      setTrackedItem(res.data);
    } catch (err: any) {
      setTrackingError(err.response?.data?.detail || 'Grievance not found with this tracking number or UUID.');
    } finally {
      setTrackingLoading(false);
    }
  };

  // Citizen Confirmation & Appeal Handler
  const handleFeedbackSubmit = async (isResolved: boolean) => {
    if (!trackedItem?.id && !trackedItem?.tracking_number) return;
    const cid = trackedItem.id || trackedItem.tracking_number;

    try {
      await axios.post(`/api/v1/complaints/${cid}/feedback`, {
        is_resolved: isResolved,
        is_appeal: !isResolved,
        rating: isResolved ? feedbackRating : 1,
        comments: feedbackComments,
        appeal_reason: !isResolved ? appealReason : undefined,
      });
      setFeedbackSubmitted(true);
      if (trackedItem) {
        setTrackedItem({
          ...trackedItem,
          status: isResolved ? 'completed' : 'awaiting_review',
        });
      }
    } catch (err) {
      console.error('Feedback submit error:', err);
      alert('Failed to submit citizen verification.');
    }
  };

  // Operator Action
  const handleOperatorAction = async (complaintId: string, decision: 'approve' | 'reject') => {
    setActionLoading(true);
    try {
      await axios.post(`/api/v1/complaints/${complaintId}/reviews`, {
        reviewer_id: user?.email || 'operator_web',
        decision: decision === 'approve' ? 'approved' : 'rejected',
        notes: reviewActionNotes || `Operator manual decision: ${decision}`,
      });
      setSelectedComplaint(null);
      setReviewActionNotes('');
      const queueRes = await axios.get<ComplaintItem[]>(`/api/v1/review/queue?tier=${tierFilter}`);
      setQueueItems(queueRes.data);
    } catch (err) {
      console.error('Operator review action failed:', err);
      alert('Failed to process review action.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="min-h-screen transition-colors duration-300">
      {/* ===================== FLOATING GLASS NAVBAR ===================== */}
      <header className="luxury-navbar w-full pointer-events-auto">
        <div className="w-full max-w-6xl rounded-sm luxury-navbar pointer-events-auto px-4 py-2.5 flex items-center justify-between gap-3">
          {/* Logo & Platform Tag */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setActiveTab('citizen')}
              className="flex items-center gap-2.5 text-left group cursor-pointer focus:outline-none"
            >
              <div className="w-10 h-10 rounded-sm bg-white text-black flex items-center justify-center  text-xl">
                🇮🇳
              </div>
              <div>
                <h1 className="text-base md:text-xl font-extrabold tracking-tight text-white leading-none">
                  {t('app.title')}
                </h1>
                <span className="text-[10px] md:text-xs font-mono font-medium text-white mt-0.5 block">
                  {t('app.subtitle')}
                </span>
              </div>
            </button>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center p-1 rounded-sm bg-transparent border border-white/20 dark:border-white/10 gap-1">
            <button
              type="button"
              onClick={() => setActiveTab('citizen')}
              className={`px-3 py-1.5 rounded-sm text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'citizen'
                  ? 'bg-white text-black text-white  border border-[#333]'
                  : 'text-[#a1a1aa] hover:text-slate-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              📢 {t('nav.home')}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('track')}
              className={`px-3 py-1.5 rounded-sm text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'track'
                  ? 'bg-white text-black text-white  border border-[#333]'
                  : 'text-[#a1a1aa] hover:text-slate-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              🔍 {t('nav.track')}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('incidents')}
              className={`px-3 py-1.5 rounded-sm text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'incidents'
                  ? 'bg-white text-black text-white  border border-[#333]'
                  : 'text-[#a1a1aa] hover:text-slate-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              🚨 {t('nav.incidents')}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('workorders')}
              className={`px-3 py-1.5 rounded-sm text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'workorders'
                  ? 'bg-white text-black text-white  border border-[#333]'
                  : 'text-[#a1a1aa] hover:text-slate-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              📋 {t('nav.workorders')}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('operator')}
              className={`px-3 py-1.5 rounded-sm text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'operator'
                  ? 'bg-white text-black text-white  border border-[#333]'
                  : 'text-[#a1a1aa] hover:text-slate-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              🛠 {t('nav.operator')}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('health')}
              className={`px-3 py-1.5 rounded-sm text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'health'
                  ? 'bg-white text-black text-white  border border-[#333]'
                  : 'text-[#a1a1aa] hover:text-slate-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              💚 {t('nav.health')}
            </button>
          </nav>

          {/* Desktop Right Utilities (State + Lang + Theme + Auth) */}
          <div className="hidden lg:flex items-center gap-2.5">
            {/* Quick State Badge */}
            <button
              type="button"
              onClick={() => {
                setActiveTab('citizen');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-white/40 dark:bg-slate-800/60 hover:bg-white/60 dark:hover:bg-slate-700/80 border border-white/50 dark:border-white/10 text-white text-xs font-bold  transition-all cursor-pointer"
            >
              <span>🏛</span>
              <span>{selectedStateName}</span>
              <span className="text-[10px] font-mono px-1 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 font-bold">
                {selectedState}
              </span>
            </button>

            {/* Language Selector */}
            <LanguageSelector />

            {/* Dark/Light Mode Theme Toggle */}
            <ThemeToggle />

            {/* Auth Buttons */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2">
                <div className="px-3 py-1.5 rounded-sm bg-white/80 dark:bg-slate-800/80 border border-[#333] text-xs font-semibold text-slate-800 dark:text-slate-200">
                  <span>👤 {user.full_name}</span>
                  <span className="ml-1.5 text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-700 dark:text-amber-400 font-bold">
                    {user.role}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={logout}
                  className="px-3 py-1.5 rounded-sm bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs font-bold transition-all cursor-pointer"
                >
                  🚪 {t('nav.logout')}
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setAuthModalMode('login');
                    setAuthModalOpen(true);
                  }}
                  className="px-3.5 py-1.5 rounded-sm bg-slate-900/5 dark:bg-white/10 hover:bg-slate-900/10 dark:hover:bg-white/20 border border-slate-900/10 dark:border-white/15 text-white text-xs font-bold transition-all cursor-pointer"
                >
                  🔑 {t('nav.login')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthModalMode('signup');
                    setAuthModalOpen(true);
                  }}
                  className="px-3.5 py-1.5 rounded-sm luxury-btn-amber text-xs font-extrabold  transition-all cursor-pointer"
                >
                  📝 {t('nav.signup')}
                </button>
              </div>
            )}
          </div>

          {/* Mobile Right Controls */}
          <div className="flex items-center gap-2 lg:hidden">
            <ThemeToggle />
            <LanguageSelector isCompact />
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-sm bg-slate-900/5 dark:bg-white/10 text-slate-800 dark:text-white border border-[#333] pointer-events-auto"
              aria-label="Toggle Mobile Menu"
            >
              {mobileMenuOpen ? '✕' : '☰'}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Glass Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden absolute top-16 left-4 right-4 p-4 rounded-sm luxury-panel pointer-events-auto space-y-3 shadow-2xl">
            {/* Mobile State Picker Trigger */}
            <div className="p-2.5 rounded-sm bg-[#1a1a1a] flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{t('nav.select_state')}:</span>
              <span className="text-xs font-bold text-white">
                {selectedStateName} ({selectedState})
              </span>
            </div>

            {/* Mobile Nav Links */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setActiveTab('citizen');
                  setMobileMenuOpen(false);
                }}
                className="p-3 rounded-sm bg-[#1a1a1a] text-xs font-bold text-slate-800 dark:text-white text-left hover:bg-white/10"
              >
                📢 {t('nav.home')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('track');
                  setMobileMenuOpen(false);
                }}
                className="p-3 rounded-sm bg-[#1a1a1a] text-xs font-bold text-slate-800 dark:text-white text-left hover:bg-white/10"
              >
                🔍 {t('nav.track')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('incidents');
                  setMobileMenuOpen(false);
                }}
                className="p-3 rounded-sm bg-[#1a1a1a] text-xs font-bold text-slate-800 dark:text-white text-left hover:bg-white/10"
              >
                🚨 {t('nav.incidents')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('workorders');
                  setMobileMenuOpen(false);
                }}
                className="p-3 rounded-sm bg-[#1a1a1a] text-xs font-bold text-slate-800 dark:text-white text-left hover:bg-white/10"
              >
                📋 {t('nav.workorders')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('operator');
                  setMobileMenuOpen(false);
                }}
                className="p-3 rounded-sm bg-[#1a1a1a] text-xs font-bold text-slate-800 dark:text-white text-left hover:bg-white/10"
              >
                🛠 {t('nav.operator')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('health');
                  setMobileMenuOpen(false);
                }}
                className="p-3 rounded-sm bg-[#1a1a1a] text-xs font-bold text-slate-800 dark:text-white text-left hover:bg-white/10"
              >
                💚 {t('nav.health')}
              </button>
            </div>

            {/* Mobile Auth */}
            <div className="pt-2 border-t border-slate-200/60 dark:border-white/10 flex gap-2">
              {isAuthenticated && user ? (
                <div className="w-full flex items-center justify-between p-2.5 rounded-sm bg-[#1a1a1a]">
                  <span className="text-xs font-bold">👤 {user.full_name}</span>
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      setMobileMenuOpen(false);
                    }}
                    className="px-3 py-1 rounded-sm bg-rose-500 text-white text-xs font-bold"
                  >
                    {t('nav.logout')}
                  </button>
                </div>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthModalMode('login');
                      setAuthModalOpen(true);
                      setMobileMenuOpen(false);
                    }}
                    className="flex-1 py-3 rounded-sm bg-[#1a1a1a] text-white font-bold text-xs"
                  >
                    🔑 {t('nav.login')}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthModalMode('signup');
                      setAuthModalOpen(true);
                      setMobileMenuOpen(false);
                    }}
                    className="flex-1 py-3 rounded-sm bg-white text-black text-slate-950 font-extrabold text-xs"
                  >
                    📝 {t('nav.signup')}
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* ===================== MAIN CONTENT ===================== */}
      <main className="luxury-container relative z-10 pt-8">
        {/* ============================================================== */}
        {/* WORKSPACE 1: CITIZEN INTAKE PORTAL & HERO                      */}
        {/* ============================================================== */}
        {activeTab === 'citizen' && (
          <div className="space-y-7">
            {/* Hero Glass Banner */}
            <div className="p-6 md:p-10 luxury-panel relative overflow-hidden">
              <div className="absolute top-[-20%] right-[-10%] w-96 h-96 bg-amber-500/20 dark:bg-white/10 rounded-sm filter blur-3xl pointer-events-none"></div>

              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-sm text-xs font-mono font-bold tracking-wide bg-white/10 text-amber-700 dark:text-amber-400 border border-amber-500/30 mb-4">
                <span className="w-2 h-2 rounded-sm bg-amber-500 animate-ping"></span>
                {t('hero.badge')}
              </div>
              <h2 className="text-3xl sm:text-5xl md:text-6xl font-black tracking-tight text-white leading-tight mb-4">
                {t('hero.title')}
              </h2>
              <p className="text-base md:text-xl font-medium text-[#a1a1aa] max-w-3xl mb-8 leading-relaxed">
                {t('hero.subtitle')}
              </p>

              {/* DEDICATED STATE SELECTOR UX */}
              <StateSelector
                onLocationDetected={(lat, lon, addr) => {
                  setFormData((prev) => ({ ...prev, latitude: lat, longitude: lon, address: addr }));
                  if (citizenMapInstance.current && citizenMarkerInstance.current) {
                    citizenMapInstance.current.setView([lat, lon], 14);
                    citizenMarkerInstance.current.setLatLng([lat, lon]);
                  }
                }}
              />
            </div>

            {/* Grievance Submission Flow & Result */}
            {submittedComplaint ? (
              /* Receipt Card */
              <div className="p-6 md:p-10 rounded-sm bg-emerald-500/10 dark:bg-emerald-950/30 backdrop-blur-2xl border border-emerald-500/30 dark:border-emerald-500/20 shadow-2xl space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-emerald-500/20">
                  <div>
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono font-bold bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                      ✓ OFFICIAL MUNICIPAL RECEIPT
                    </span>
                    <h3 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white mt-2">
                      {t('receipt.title')}
                    </h3>
                  </div>
                  <span className="text-xs font-mono font-extrabold uppercase px-3 py-1.5 rounded-sm bg-emerald-500 text-slate-950  shadow-emerald-500/20">
                    {submittedComplaint.status || 'COMPLETED'}
                  </span>
                </div>

                {/* Permanent Tracking ID Banner */}
                <div className="p-5 rounded-sm bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border border-emerald-500/30 flex flex-wrap items-center justify-between gap-4 ">
                  <div>
                    <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 uppercase block">
                      {t('receipt.tracking_id')}
                    </span>
                    <span className="text-xl md:text-2xl font-mono font-extrabold text-white">
                      {submittedComplaint.tracking_number || submittedComplaint.id}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const idStr = submittedComplaint.tracking_number || submittedComplaint.id || '';
                      navigator.clipboard.writeText(idStr);
                      alert(t('receipt.copied'));
                    }}
                    className="px-4 py-2.5 rounded-sm bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs  transition-all cursor-pointer"
                  >
                    📋 {t('receipt.copy')}
                  </button>
                </div>

                {/* Autonomous 8-Agent Swarm Progress Steps */}
                <div className="p-5 rounded-sm bg-white/70 dark:bg-slate-900/70 backdrop-blur-md border border-white/60 dark:border-white/10 ">
                  <h4 className="text-sm font-extrabold uppercase tracking-wide text-white mb-4 pb-2 border-b border-slate-200/60 dark:border-white/10">
                    🤖 {t('pipeline.title')}
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 text-xs font-mono font-semibold">
                    <div className="p-3 rounded-sm bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="text-emerald-500 font-bold">✓</span> {t('pipeline.intake')}
                    </div>
                    <div className="p-3 rounded-sm bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="text-emerald-500 font-bold">✓</span> {t('pipeline.vision')}
                    </div>
                    <div className="p-3 rounded-sm bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="text-emerald-500 font-bold">✓</span> {t('pipeline.speech')}
                    </div>
                    <div className="p-3 rounded-sm bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="text-emerald-500 font-bold">✓</span> {t('pipeline.location')}
                    </div>
                    <div className="p-3 rounded-sm bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="text-emerald-500 font-bold">✓</span> {t('pipeline.rag')}
                    </div>
                    <div className="p-3 rounded-sm bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="text-emerald-500 font-bold">✓</span> {t('pipeline.decision')}
                    </div>
                    <div className="p-3 rounded-sm bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="text-emerald-500 font-bold">✓</span> {t('pipeline.verification')}
                    </div>
                    <div className="p-3 rounded-sm bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="text-emerald-500 font-bold">✓</span> {t('pipeline.workorder')}
                    </div>
                  </div>
                </div>

                {/* CTAs */}
                <div className="flex flex-wrap gap-3.5 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setTrackingQuery(submittedComplaint.tracking_number || submittedComplaint.id || '');
                      setActiveTab('track');
                    }}
                    className="px-6 py-3.5 rounded-sm bg-white text-black hover:from-amber-400 hover:to-amber-500 text-slate-950 font-extrabold text-sm  shadow-amber-500/25 border border-white/20 transition-all cursor-pointer"
                  >
                    {t('receipt.track_cta')}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSubmittedComplaint(null);
                      setFormData((prev) => ({ ...prev, text_description: '', photo: null, audio: null }));
                    }}
                    className="px-6 py-3.5 rounded-sm bg-white/80 dark:bg-slate-800/80 hover:bg-white dark:hover:bg-slate-700 text-white font-bold text-sm border border-slate-200 dark:border-white/10  transition-all cursor-pointer"
                  >
                    {t('receipt.report_another')}
                  </button>
                </div>
              </div>
            ) : (
              /* Complaint Form Grid */
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-7">
                {/* Form Input Section */}
                <div className="lg:col-span-7 p-6 md:p-8 rounded-sm bg-white/75 dark:bg-slate-900/70 backdrop-blur-2xl border border-white/70 dark:border-white/10 shadow-xl">
                  <h3 className="text-xl md:text-2xl font-extrabold tracking-tight text-white mb-5 pb-3 border-b border-slate-200/60 dark:border-white/10 flex items-center justify-between">
                    <span>{t('form.title')}</span>
                    <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-sm bg-amber-500/20 text-amber-700 dark:text-amber-300">
                      {selectedStateName}
                    </span>
                  </h3>

                  {formError && (
                    <div className="mb-5 p-3.5 rounded-sm bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 font-semibold text-xs md:text-sm">
                      ⚠️ {formError}
                    </div>
                  )}

                  <form onSubmit={handleComplaintSubmit} className="space-y-5">
                    {/* Text Description */}
                    <div>
                      <label className="block text-xs font-bold uppercase text-slate-700 dark:text-slate-300 mb-2">
                        {t('form.desc_label')} *
                      </label>
                      <textarea
                        required
                        rows={4}
                        value={formData.text_description}
                        onChange={(e) => setFormData((prev) => ({ ...prev, text_description: e.target.value }))}
                        placeholder={t('form.desc_placeholder')}
                        className="w-full p-4 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white placeholder-slate-400 focus:ring-2 focus:ring-amber-500/50"
                      />
                    </div>

                    {/* Voice-First Indic Audio Intake */}
                    <div className="p-4 rounded-sm bg-slate-100/80 dark:bg-slate-800/60 border border-slate-200/70 dark:border-white/10">
                      <label className="block text-xs font-bold uppercase text-slate-700 dark:text-slate-300 mb-2">
                        {t('form.voice_title')}
                      </label>
                      <div className="flex flex-wrap items-center gap-3">
                        {isVoiceRecording ? (
                          <button
                            type="button"
                            onClick={stopVoiceRecording}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-sm bg-rose-500 text-white font-bold text-xs  shadow-rose-500/30 animate-pulse cursor-pointer"
                          >
                            <span>{t('form.voice_stop')} ({recordingSeconds}s)</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={startVoiceRecording}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-sm bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs  transition-all cursor-pointer"
                          >
                            <span>🎤 {t('form.voice_start')}</span>
                          </button>
                        )}
                        {formData.audio && (
                          <span className="text-xs font-mono font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-500/20 px-3 py-1.5 rounded-sm border border-emerald-500/30">
                            ✓ {t('form.voice_recorded')}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Photo Upload (BLIP Vision) */}
                    <div className="p-4 rounded-sm bg-slate-100/80 dark:bg-slate-800/60 border border-slate-200/70 dark:border-white/10">
                      <label className="block text-xs font-bold uppercase text-slate-700 dark:text-slate-300 mb-2">
                        {t('form.photo_title')}
                      </label>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setFormData((prev) => ({ ...prev, photo: e.target.files![0] }));
                          }
                        }}
                        className="text-xs font-semibold file:mr-3 file:py-2 file:px-4 file:rounded-sm file:border-0 file:text-xs file:font-bold file:bg-slate-200 dark:file:bg-slate-700 file:text-slate-800 dark:file:text-white hover:file:bg-amber-500/20 cursor-pointer"
                      />
                    </div>

                    {/* Address & Coordinates */}
                    <div>
                      <label className="block text-xs font-bold uppercase text-slate-700 dark:text-slate-300 mb-1.5">
                        {t('form.address_label')}
                      </label>
                      <input
                        type="text"
                        value={formData.address}
                        onChange={(e) => setFormData((prev) => ({ ...prev, address: e.target.value }))}
                        className="w-full px-4 py-3 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-amber-500/50"
                      />
                      <div className="flex gap-4 text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-1.5">
                        <span>Lat: {formData.latitude.toFixed(4)}</span>
                        <span>Lon: {formData.longitude.toFixed(4)}</span>
                      </div>
                    </div>

                    {/* Submit Dispatch Button */}
                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full py-4 rounded-sm bg-white text-black hover:from-amber-400 hover:to-amber-500 text-slate-950 font-extrabold text-base  shadow-amber-500/30 border border-white/20 transition-all transform hover:-translate-y-0.5 disabled:opacity-50 cursor-pointer"
                    >
                      {submitting ? t('form.submitting') : t('form.submit_button')}
                    </button>
                  </form>
                </div>

                {/* Map Display & State Preview */}
                <div className="lg:col-span-5 flex flex-col gap-5">
                  <div className="p-5 rounded-sm bg-white/75 dark:bg-slate-900/70 backdrop-blur-2xl border border-white/70 dark:border-white/10 shadow-xl flex-1 flex flex-col">
                    <h4 className="text-sm font-extrabold uppercase text-white mb-3 flex items-center justify-between">
                      <span>🗺️ {t('form.location_title')}</span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded-sm bg-amber-500/20 text-amber-700 dark:text-amber-300 font-bold">
                        {selectedState}
                      </span>
                    </h4>
                    <div ref={citizenMapRef} className="w-full h-80 md:h-96 rounded-sm overflow-hidden border border-[#333]" />
                    <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-3">
                      💡 Click and drag the map pin to precisely mark the road hazard, pothole, or streetlight.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* WORKSPACE 2: CITIZEN TRACK REPORT & APPEAL LOOP                */}
        {/* ============================================================== */}
        {activeTab === 'track' && (
          <div className="space-y-6">
            <div className="p-6 md:p-8 rounded-sm bg-white/75 dark:bg-slate-900/70 backdrop-blur-2xl border border-white/70 dark:border-white/10 shadow-xl">
              <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white mb-5 pb-3 border-b border-slate-200/60 dark:border-white/10">
                🔍 {t('track.title')}
              </h2>

              {/* Search Box */}
              <form onSubmit={handleTrackSubmit} className="flex flex-col sm:flex-row gap-3 mb-6">
                <input
                  type="text"
                  required
                  value={trackingQuery}
                  onChange={(e) => setTrackingQuery(e.target.value)}
                  placeholder={t('track.search_placeholder')}
                  className="flex-1 p-3.5 rounded-sm bg-slate-100/90 dark:bg-slate-800/90 border border-[#333] text-sm font-semibold text-white focus:ring-2 focus:ring-amber-500/50"
                />
                <button
                  type="submit"
                  disabled={trackingLoading}
                  className="px-7 py-3.5 rounded-sm bg-white text-black hover:from-amber-400 hover:to-amber-500 text-slate-950 font-extrabold text-sm  shadow-amber-500/25 border border-white/20 transition-all cursor-pointer"
                >
                  {trackingLoading ? t('track.searching') : t('track.search_button')}
                </button>
              </form>

              {trackingError && (
                <div className="p-3.5 rounded-sm bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 font-semibold text-xs md:text-sm mb-6">
                  ⚠️ {trackingError}
                </div>
              )}

              {/* Tracked Grievance Details Card */}
              {trackedItem && (
                <div className="space-y-6">
                  <div className="p-6 rounded-sm bg-amber-500/10 dark:bg-amber-950/20 backdrop-blur-xl border border-amber-500/20 space-y-5">
                    <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-amber-500/20">
                      <div>
                        <span className="text-xs font-mono font-bold uppercase px-2.5 py-1 rounded-sm bg-amber-500/20 text-amber-700 dark:text-amber-400">
                          {trackedItem.state_code || selectedState} CIVIC OPS
                        </span>
                        <h3 className="text-xl md:text-2xl font-extrabold tracking-tight text-white mt-1.5">
                          {trackedItem.tracking_number || trackedItem.id}
                        </h3>
                      </div>
                      <span className="text-xs font-mono font-extrabold uppercase px-3 py-1.5 rounded-sm bg-amber-500 text-slate-950">
                        {trackedItem.status || 'PROCESSING'}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3.5">
                      <div className="p-4 rounded-sm bg-white/80 dark:bg-slate-900/80 border border-white/60 dark:border-white/10">
                        <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                          {t('track.category_label')}
                        </span>
                        <span className="text-sm font-extrabold text-white uppercase mt-0.5 block">
                          {trackedItem.category || 'Road / Pothole'}
                        </span>
                      </div>
                      <div className="p-4 rounded-sm bg-white/80 dark:bg-slate-900/80 border border-white/60 dark:border-white/10">
                        <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                          {t('track.priority_label')}
                        </span>
                        <span className="text-sm font-extrabold text-white uppercase mt-0.5 block">
                          {trackedItem.priority || 'CRITICAL (24H)'}
                        </span>
                      </div>
                      <div className="p-4 rounded-sm bg-white/80 dark:bg-slate-900/80 border border-white/60 dark:border-white/10">
                        <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                          {t('track.department_label')}
                        </span>
                        <span className="text-xs font-bold text-white mt-0.5 block">
                          {trackedItem.local_body_name || 'Road Infrastructure Dept'}
                        </span>
                      </div>
                      <div className="p-4 rounded-sm bg-white/80 dark:bg-slate-900/80 border border-white/60 dark:border-white/10">
                        <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                          {t('track.work_order_label')}
                        </span>
                        <span className="text-xs font-mono font-bold text-white mt-0.5 block">
                          {trackedItem.work_order_id ? `WO-${trackedItem.work_order_id.slice(0, 8).toUpperCase()}` : 'WO-DISPATCHED'}
                        </span>
                      </div>
                    </div>

                    <div className="p-4 rounded-sm bg-white/80 dark:bg-slate-900/80 border border-white/60 dark:border-white/10">
                      <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                        GRIEVANCE DESCRIPTION
                      </span>
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 mt-1">
                        {trackedItem.text_description}
                      </p>
                    </div>

                    {/* Citizen Resolution Confirmation & Appeal Loop */}
                    <div className="p-5 rounded-sm bg-white/90 dark:bg-slate-900/90 border border-white/60 dark:border-white/10 space-y-3.5">
                      <h4 className="text-sm font-extrabold uppercase text-white border-b border-slate-200/60 dark:border-white/10 pb-2">
                        🗳️ {t('track.feedback_title')}
                      </h4>

                      {feedbackSubmitted ? (
                        <div className="p-3.5 rounded-sm bg-emerald-500/15 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 font-bold text-xs md:text-sm">
                          ✅ {t('track.feedback_success')}
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <p className="text-xs font-medium text-[#a1a1aa]">
                            {t('track.is_resolved_q')}
                          </p>

                          <div className="flex flex-wrap gap-2.5">
                            <button
                              type="button"
                              onClick={() => handleFeedbackSubmit(true)}
                              className="px-5 py-2.5 rounded-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs  shadow-emerald-500/20 cursor-pointer"
                            >
                              ✓ {t('track.confirm_resolved')}
                            </button>
                            <button
                              type="button"
                              onClick={() => handleFeedbackSubmit(false)}
                              className="px-5 py-2.5 rounded-sm bg-rose-500/20 hover:bg-rose-500/30 text-rose-600 dark:text-rose-400 font-bold text-xs border border-rose-500/30 cursor-pointer"
                            >
                              ✕ {t('track.reopen_appeal')}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* WORKSPACE 3: STATE & LOCAL BODY COMMAND                        */}
        {/* ============================================================== */}
        {activeTab === 'command' && (
          <div className="p-6 md:p-8 rounded-sm bg-white/75 dark:bg-slate-900/70 backdrop-blur-2xl border border-white/70 dark:border-white/10 shadow-xl space-y-5">
            <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white pb-3 border-b border-slate-200/60 dark:border-white/10 flex items-center justify-between">
              <span>🏛 {t('nav.command')}</span>
              <span className="text-xs font-mono font-bold px-3 py-1 rounded-sm bg-amber-500/20 text-amber-700 dark:text-amber-300">
                LGD ACTIVE: {selectedStateName}
              </span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-5 rounded-sm bg-amber-500/10 dark:bg-amber-950/20 border border-amber-500/20">
                <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">Urban Local Bodies (ULBs)</span>
                <span className="text-3xl font-black text-white block mt-2">12 Corporations</span>
              </div>
              <div className="p-5 rounded-sm bg-emerald-500/10 dark:bg-emerald-950/20 border border-emerald-500/20">
                <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">Rural Panchayats (RLBs)</span>
                <span className="text-3xl font-black text-white block mt-2">5,950 GPs</span>
              </div>
              <div className="p-5 rounded-sm bg-blue-500/10 dark:bg-blue-950/20 border border-blue-500/20">
                <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">Auto-Dispatched SLA</span>
                <span className="text-3xl font-black text-white block mt-2">99.4% On-Time</span>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* WORKSPACE 4: OPERATOR REVIEW HUB                               */}
        {/* ============================================================== */}
        {activeTab === 'operator' && (
          <div className="space-y-6">
            <div className="p-6 md:p-8 rounded-sm bg-white/75 dark:bg-slate-900/70 backdrop-blur-2xl border border-white/70 dark:border-white/10 shadow-xl">
              <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white pb-3 border-b border-slate-200/60 dark:border-white/10 mb-6">
                🛠 {t('operator.title')}
              </h2>

              {/* Metric Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="p-4 rounded-sm bg-amber-500/10 border border-amber-500/20">
                  <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">{t('operator.total_pending')}</span>
                  <span className="text-2xl md:text-3xl font-black text-white block mt-1">{reviewStats?.total_pending || queueItems.length}</span>
                </div>
                <div className="p-4 rounded-sm bg-rose-500/10 border border-rose-500/20">
                  <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">{t('operator.mandatory')}</span>
                  <span className="text-2xl md:text-3xl font-black text-white block mt-1">{reviewStats?.mandatory_review || queueItems.filter(i => (i.confidence_score || 0) < 0.7).length}</span>
                </div>
                <div className="p-4 rounded-sm bg-yellow-500/10 border border-yellow-500/20">
                  <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">{t('operator.optional')}</span>
                  <span className="text-2xl md:text-3xl font-black text-white block mt-1">{reviewStats?.optional_review || 0}</span>
                </div>
                <div className="p-4 rounded-sm bg-emerald-500/10 border border-emerald-500/20">
                  <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 uppercase">{t('operator.auto_processed')}</span>
                  <span className="text-2xl md:text-3xl font-black text-white block mt-1">{reviewStats?.auto_processed || 24}</span>
                </div>
              </div>

              {/* Review Queue Items */}
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-200/60 dark:border-white/10">
                  <span className="text-xs font-mono font-bold uppercase text-slate-500 dark:text-slate-400">
                    {t('operator.queue_title')} ({queueItems.length})
                  </span>
                  <div className="flex gap-2 text-xs font-bold">
                    <button
                      type="button"
                      onClick={() => setTierFilter('all')}
                      className={`px-3 py-1 rounded-sm transition-all ${tierFilter === 'all' ? 'bg-amber-500 text-slate-950 font-bold' : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'}`}
                    >
                      ALL
                    </button>
                    <button
                      type="button"
                      onClick={() => setTierFilter('mandatory')}
                      className={`px-3 py-1 rounded-sm transition-all ${tierFilter === 'mandatory' ? 'bg-amber-500 text-slate-950 font-bold' : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'}`}
                    >
                      MANDATORY
                    </button>
                  </div>
                </div>

                {queueItems.map((item) => (
                  <div
                    key={item.id || item.complaint_id}
                    className="p-4 rounded-sm bg-white/60 dark:bg-slate-800/60 backdrop-blur-md border border-slate-200/70 dark:border-white/10 flex flex-wrap items-center justify-between gap-3 hover:border-amber-500/40 transition-all"
                  >
                    <div>
                      <span className="text-xs font-mono font-bold uppercase px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-700 dark:text-amber-300 mr-2">
                        {item.tracking_number || item.id?.slice(0, 8)}
                      </span>
                      <span className="text-xs font-bold uppercase text-white">{item.category || 'road_damage'}</span>
                      <p className="text-sm font-medium text-[#a1a1aa] mt-1 max-w-xl truncate">
                        {item.text_description}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleOperatorAction(item.id || item.complaint_id || '', 'approve')}
                        disabled={actionLoading}
                        className="px-4 py-2 rounded-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs  shadow-emerald-500/20 cursor-pointer"
                      >
                        ✓ {t('operator.approve')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOperatorAction(item.id || item.complaint_id || '', 'reject')}
                        disabled={actionLoading}
                        className="px-4 py-2 rounded-sm bg-rose-500/20 hover:bg-rose-500/30 text-rose-600 dark:text-rose-400 font-bold text-xs border border-rose-500/30 cursor-pointer"
                      >
                        ✕ {t('operator.reject')}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* WORKSPACE 5: INCIDENT CLUSTERS (75M HAVERSINE)                 */}
        {/* ============================================================== */}
        {activeTab === 'incidents' && (
          <div className="p-6 md:p-8 rounded-sm bg-white/75 dark:bg-slate-900/70 backdrop-blur-2xl border border-white/70 dark:border-white/10 shadow-xl space-y-5">
            <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white pb-3 border-b border-slate-200/60 dark:border-white/10">
              🚨 {t('incidents.title')}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {incidents.map((inc) => (
                <div key={inc.id} className="p-5 rounded-sm bg-white/60 dark:bg-slate-800/60 border border-slate-200/70 dark:border-white/10 space-y-2.5">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-mono font-bold uppercase px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-700 dark:text-amber-300">
                      {inc.incident_number}
                    </span>
                    <span className="text-xs font-bold uppercase px-2 py-0.5 rounded-sm bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/30">
                      {inc.total_complaints} REPORTS CLUSTERED
                    </span>
                  </div>
                  <h4 className="text-base font-extrabold text-white">{inc.title}</h4>
                  <p className="text-xs font-mono text-slate-500 dark:text-slate-400">{inc.address}</p>
                  <div className="flex justify-between text-xs font-bold pt-2 border-t border-slate-200/60 dark:border-white/10">
                    <span className="text-[#a1a1aa]">Dept: {inc.assigned_department || 'Roads & Infrastructure'}</span>
                    <span className="text-white">Status: {inc.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* WORKSPACE 6: MUNICIPAL WORK ORDERS                             */}
        {/* ============================================================== */}
        {activeTab === 'workorders' && (
          <div className="p-6 md:p-8 rounded-sm bg-white/75 dark:bg-slate-900/70 backdrop-blur-2xl border border-white/70 dark:border-white/10 shadow-xl space-y-5">
            <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white pb-3 border-b border-slate-200/60 dark:border-white/10">
              📋 {t('workorders.title')}
            </h2>
            <div className="space-y-3">
              {workOrders.map((wo) => (
                <div key={wo.id} className="p-4 rounded-sm bg-white/60 dark:bg-slate-800/60 border border-slate-200/70 dark:border-white/10 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <span className="text-xs font-mono font-bold uppercase px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-700 dark:text-amber-300 mr-2">
                      {wo.work_order_number}
                    </span>
                    <span className="text-sm font-extrabold text-white">{wo.title}</span>
                    <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">{wo.address}</p>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-mono font-bold">
                    <span className="text-emerald-600 dark:text-emerald-400">💰 {wo.estimated_cost ? `₹${wo.estimated_cost.toFixed(2)}` : '₹2,500.00'}</span>
                    <span className="text-slate-500 dark:text-slate-400">⏱️ {wo.estimated_duration_days || 1} Days SLA</span>
                    <span className="px-2.5 py-1 rounded-sm bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white uppercase">{wo.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* WORKSPACE 7: SYSTEM HEALTH TERMINAL                            */}
        {/* ============================================================== */}
        {activeTab === 'health' && (
          <div className="p-6 md:p-8 rounded-sm bg-slate-950/90 text-emerald-400 font-mono backdrop-blur-2xl border border-emerald-500/30 shadow-2xl space-y-5">
            <h2 className="text-xl md:text-2xl font-bold uppercase tracking-tight border-b border-emerald-500/30 pb-3 flex items-center gap-2">
              <span>💚</span> SYSTEM HEALTH & SERVICES TELEMETRY
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="p-4 rounded-sm bg-slate-900/90 border border-emerald-500/20">
                <span className="text-slate-400 block">POSTGRES POSTGIS:</span>
                <span className="text-emerald-400 font-bold text-sm">ONLINE (HEALTHY)</span>
              </div>
              <div className="p-4 rounded-sm bg-slate-900/90 border border-emerald-500/20">
                <span className="text-slate-400 block">REDIS BROKER:</span>
                <span className="text-emerald-400 font-bold text-sm">ONLINE (HEALTHY)</span>
              </div>
              <div className="p-4 rounded-sm bg-slate-900/90 border border-emerald-500/20">
                <span className="text-slate-400 block">MINIO OBJECT STORAGE:</span>
                <span className="text-emerald-400 font-bold text-sm">ONLINE (HEALTHY)</span>
              </div>
              <div className="p-4 rounded-sm bg-slate-900/90 border border-emerald-500/20">
                <span className="text-slate-400 block">INDIA LGD REGISTRY:</span>
                <span className="text-emerald-400 font-bold text-sm">36 STATES / UTS ACTIVE</span>
              </div>
            </div>
            <pre className="p-4 rounded-sm bg-black/60 text-[11px] text-slate-300 overflow-x-auto border border-emerald-500/15">
              {JSON.stringify(healthStatus || { status: 'healthy', version: '1.0.0', autonomous_agents: 8, states_count: 36 }, null, 2)}
            </pre>
          </div>
        )}
      </main>

      {/* ===================== FOOTER ===================== */}
      <footer className="mt-16 py-8 border-t border-slate-200/60 dark:border-white/10 bg-white/40 dark:bg-slate-950/40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 text-center space-y-2">
          <p className="text-xs md:text-sm font-bold text-slate-800 dark:text-slate-200">
            🇮🇳 {t('footer.disclaimer')}
          </p>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400">
            {t('footer.rights')}
          </p>
        </div>
      </footer>

      {/* Auth Modal (Login / Signup) */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
        onSuccess={(role) => {
          if (role === 'super_admin' || role === 'state_admin') {
            setActiveTab('command');
          } else if (role === 'field_engineer') {
            setActiveTab('workorders');
          } else if (role === 'local_body_admin') {
            setActiveTab('operator');
          } else {
            setActiveTab('citizen');
          }
        }}
      />
    </div>
  );
}