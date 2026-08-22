import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  PlusCircle, 
  FolderKanban, 
  History as HistoryIcon, 
  Bell, 
  BarChart3, 
  Settings, 
  LogOut, 
  TrendingUp, 
  Search, 
  Sparkles,
  HelpCircle,
  Building2,
  Scale
} from 'lucide-react';

import VoiceIntake from '../components/VoiceIntake';
import ClassificationView from '../components/ClassificationView';
import TicketCard from '../components/TicketCard';
import LegalBriefCard from '../components/LegalBriefCard';

export default function Dashboard() {
  const [activeNav, setActiveNav] = useState('new-intake'); // 'dashboard' | 'new-intake' | 'cases' | 'history' | 'analytics' | 'settings'
  const [currentOutcome, setCurrentOutcome] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Initial mock cases matching Screen 2 and Screen 5A of image1.jpeg
  const [cases, setCases] = useState([
    {
      id: 'GRA-2026-0087',
      type: 'infrastructure',
      title: 'Blocked Drainage at Alagomeji',
      status: 'Completed',
      date: 'Aug 14, 2026',
      assigned: 'Lagos Environmental Services',
      priority: 'Medium'
    },
    {
      id: 'LEG-2026-0051',
      type: 'legal',
      title: 'Land dispute with neighbor',
      status: 'In Review',
      date: 'Aug 13, 2026',
      assigned: 'Legal Aid Counsel',
      priority: 'High'
    },
    {
      id: 'GRA-2026-0086',
      type: 'infrastructure',
      title: 'Street light not working',
      status: 'Completed',
      date: 'Aug 12, 2026',
      assigned: 'Power & Grid Unit',
      priority: 'Low'
    },
    {
      id: 'LEG-2026-0048',
      type: 'legal',
      title: 'Noise disturbance complaint',
      status: 'Pending',
      date: 'Aug 11, 2026',
      assigned: 'Pro Bono Network',
      priority: 'Medium'
    },
    {
      id: 'ABB-2026-0012',
      type: 'abstained',
      title: 'Unclear community complaint',
      status: 'Clarification Sent',
      date: 'Aug 10, 2026',
      assigned: 'Gate Triage',
      priority: 'Low'
    }
  ]);

  const [filterCategory, setFilterCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Handle Voice / Text Intake submission to Backend API
  const handleIntakeSubmit = async (payload) => {
    setIsLoading(true);

    try {
      let response;
      if (payload.type === 'text') {
        response = await fetch('/intake', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: payload.text }),
        });
      } else if (payload.type === 'voice' && payload.file) {
        const formData = new FormData();
        formData.append('audio', payload.file, 'recording.wav');
        response = await fetch('/intake/voice', {
          method: 'POST',
          body: formData,
        });
      }

      if (response && response.ok) {
        const data = await response.json();
        setCurrentOutcome(data);
        if (data.status === 'routed') {
          const newCase = {
            id: data.artifact?.tracking_id || data.artifact?.brief_id || `INT-${Date.now().toString().slice(-4)}`,
            type: data.domain,
            title: data.artifact?.complaint_type || data.artifact?.grievance_type || (data.transcript.slice(0, 35) + '...'),
            status: 'In Review',
            date: 'Today',
            assigned: data.domain === 'infrastructure' ? 'Municipal Services' : 'Legal Aid Counsel',
            priority: 'High'
          };
          setCases(prev => [newCase, ...prev]);
        }
      } else {
        // Fallback simulation for client-only / offline demo mode
        const text = payload.text || payload.transcriptHint || "";
        const isLegal = /landlord|evict|rent|police|assault|dispute|tenant|court|rights/i.test(text);
        const isInfra = /drain|pothole|water|road|light|pipe|overflow|trash|waste/i.test(text);

        setTimeout(() => {
          if (!isLegal && !isInfra) {
            // Abstain Gate Triggered
            setCurrentOutcome({
              status: 'needs_clarification',
              session_id: 'sess-' + Math.random().toString(36).substring(2, 9),
              transcript: text,
              classification: { domain: 'needs_clarification', confidence: 0.52 },
              extraction: { entities: [] },
              clarifying_question: "Is this complaint about public infrastructure (like roads or water) or a legal issue (like tenancy or rights)?",
              reasons: ["Classifier confidence 52% below threshold 70%", "Missing required location / party entities"]
            });
          } else if (isInfra) {
            setCurrentOutcome({
              status: 'routed',
              domain: 'infrastructure',
              session_id: 'sess-' + Math.random().toString(36).substring(2, 9),
              transcript: text,
              classification: { domain: 'infrastructure', confidence: 0.94 },
              extraction: {
                entities: [
                  { type: 'location', value: 'Alagomeji, Yaba, Lagos', confidence: 0.96 },
                  { type: 'complaint_type', value: 'Blocked Drainage Overflow', confidence: 0.91 }
                ]
              },
              artifact: {
                tracking_id: 'GRA-2026-0087',
                category: 'Blocked Drainage & Flood Risk',
                location: 'Alagomeji, Yaba, Lagos Mainland',
                assigned_department: 'Lagos State Ministry of the Environment',
                priority: 'High',
                status: 'Accepted & Dispatched'
              },
              reasons: ["High confidence infrastructure classification (94%)", "Location entity extracted"]
            });
          } else {
            setCurrentOutcome({
              status: 'routed',
              domain: 'legal',
              session_id: 'sess-' + Math.random().toString(36).substring(2, 9),
              transcript: text,
              classification: { domain: 'legal', confidence: 0.91 },
              extraction: {
                entities: [
                  { type: 'party', value: 'Landlord / Property Owner', confidence: 0.92 },
                  { type: 'grievance_type', value: 'Unlawful Eviction Notice', confidence: 0.88 }
                ]
              },
              artifact: {
                brief_id: 'LEG-2026-0051',
                grievance_type: 'Tenancy Dispute & 3-Day Notice',
                respondent_party: 'Landlord / Property Owner',
                assigned_network: 'Legal Aid Council of Nigeria & Pro Bono Clearinghouse',
                urgency: 'High',
                statement_of_facts: text
              },
              reasons: ["Legal domain detected with 91% confidence", "Adverse party identified"]
            });
          }
        }, 700);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Clarify Submission (POST /intake/{session_id}/clarify)
  const handleClarifySubmit = async (answer) => {
    if (!currentOutcome?.session_id) return;
    setIsLoading(true);

    try {
      const res = await fetch(`/intake/${currentOutcome.session_id}/clarify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer }),
      });

      if (res.ok) {
        const data = await res.json();
        setCurrentOutcome(data);
      } else {
        const isLegal = /legal|landlord|dispute|person|rights/i.test(answer);
        setTimeout(() => {
          if (isLegal) {
            setCurrentOutcome({
              status: 'routed',
              domain: 'legal',
              session_id: currentOutcome.session_id,
              transcript: currentOutcome.transcript + " " + answer,
              classification: { domain: 'legal', confidence: 0.89 },
              extraction: {
                entities: [
                  { type: 'party', value: 'Landlord / Adverse Party', confidence: 0.88 },
                  { type: 'grievance_type', value: 'Civil Rights & Tenancy Dispute', confidence: 0.85 }
                ]
              },
              artifact: {
                brief_id: 'LEG-2026-0052',
                grievance_type: 'Tenancy Grievance Clarified',
                respondent_party: 'Landlord',
                assigned_network: 'Legal Aid Council of Nigeria',
                urgency: 'High',
                statement_of_facts: currentOutcome.transcript + " Clarification: " + answer
              },
              reasons: ["Clarification resolved domain ambiguity", "Routed to Legal Aid"]
            });
          } else {
            setCurrentOutcome({
              status: 'routed',
              domain: 'infrastructure',
              session_id: currentOutcome.session_id,
              transcript: currentOutcome.transcript + " " + answer,
              classification: { domain: 'infrastructure', confidence: 0.92 },
              extraction: {
                entities: [
                  { type: 'location', value: 'Lagos Mainland', confidence: 0.90 },
                  { type: 'complaint_type', value: 'Public Infrastructure Maintenance', confidence: 0.92 }
                ]
              },
              artifact: {
                tracking_id: 'GRA-2026-0088',
                category: 'Public Infrastructure Maintenance',
                location: 'Lagos Mainland Municipal Area',
                assigned_department: 'Lagos Environmental Services',
                priority: 'Medium',
                status: 'Accepted & Dispatched'
              },
              reasons: ["Clarification confirmed municipal infrastructure", "Ticket generated"]
            });
          }
        }, 650);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredCases = cases.filter(c => {
    const matchesCategory = filterCategory === 'all' || c.type === filterCategory;
    const matchesSearch = c.title.toLowerCase().includes(searchQuery.toLowerCase()) || c.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-[#F6FAFB] flex flex-col lg:flex-row text-[#0F172A] font-sans">
      {/* 1. Left Sidebar Navigation matching image1.jpeg */}
      <aside className="w-full lg:w-64 bg-[#0A1C16] text-white flex flex-col justify-between p-6 shrink-0">
        <div className="space-y-8">
          {/* Logo & Brand Header */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-brand-accent flex items-center justify-center text-brand-sidebar font-extrabold shadow-sm">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-base font-bold font-display tracking-tight text-white">SautiCivic</h1>
              <p className="text-[11px] text-emerald-400 font-mono font-medium">Bridge · Sahara v2.5</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
              { id: 'new-intake', label: 'New Intake', icon: PlusCircle, highlight: true },
              { id: 'cases', label: 'My Cases', icon: FolderKanban },
              { id: 'history', label: 'History', icon: HistoryIcon },
              { id: 'analytics', label: 'Analytics', icon: BarChart3 },
              { id: 'settings', label: 'Settings', icon: Settings },
            ].map(item => {
              const Icon = item.icon;
              const isActive = activeNav === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveNav(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold font-display transition-all ${
                    isActive 
                      ? 'bg-brand-accent text-[#0A1C16] shadow-sm font-bold' 
                      : 'text-gray-300 hover:text-white hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </div>
                  {item.id === 'new-intake' && !isActive && (
                    <span className="w-2 h-2 rounded-full bg-brand-accent animate-pulse" />
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* User Profile Pill at Bottom of Sidebar */}
        <div className="pt-6 border-t border-white/10 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-full bg-emerald-700 text-white flex items-center justify-center font-bold text-xs border border-emerald-500/40">
              AB
            </div>
            <div>
              <p className="text-xs font-bold font-display text-white">Aisha Bello</p>
              <p className="text-[10px] text-gray-400 font-mono">Citizen · Lagos</p>
            </div>
          </div>
          <button className="text-gray-400 hover:text-white transition-colors" title="Log out">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* 2. Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Header Bar */}
        <header className="bg-white border-b border-gray-200 px-6 lg:px-10 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 sticky top-0 z-20">
          <div>
            <h2 className="text-xl font-bold font-display text-gray-900 flex items-center space-x-2">
              <span>Welcome back, Aisha</span>
              <span className="text-lg">👋</span>
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Here's what's happening with your cases.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button 
              onClick={() => {
                setCurrentOutcome(null);
                setActiveNav('new-intake');
              }}
              className="px-4 py-2 rounded-xl bg-brand-primary hover:bg-brand-primaryHover text-white text-xs font-bold font-display flex items-center space-x-2 shadow-sm transition-all"
            >
              <PlusCircle className="w-4 h-4" />
              <span>+ New Intake</span>
            </button>
            <button className="p-2 rounded-xl border border-gray-200 hover:bg-gray-50 text-gray-600 relative">
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
            </button>
          </div>
        </header>

        <div className="p-6 lg:p-10 space-y-8 max-w-7xl mx-auto w-full">
          {/* Top Metrics Cards (Screen 2 from image1.jpeg) */}
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold font-mono text-gray-400 uppercase tracking-wider block">Total Intakes</span>
              <div className="text-2xl font-extrabold font-display text-gray-900 mt-1">24</div>
              <span className="text-[10px] font-bold text-emerald-600 flex items-center mt-1">
                <TrendingUp className="w-3 h-3 mr-0.5" /> +12% from last week
              </span>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold font-mono text-gray-400 uppercase tracking-wider block">Infrastructure</span>
              <div className="text-2xl font-extrabold font-display text-emerald-700 mt-1">14</div>
              <span className="text-[10px] font-bold text-emerald-600 flex items-center mt-1">
                <TrendingUp className="w-3 h-3 mr-0.5" /> +18% from last week
              </span>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold font-mono text-gray-400 uppercase tracking-wider block">Legal Grievances</span>
              <div className="text-2xl font-extrabold font-display text-indigo-700 mt-1">8</div>
              <span className="text-[10px] font-bold text-indigo-600 flex items-center mt-1">
                <TrendingUp className="w-3 h-3 mr-0.5" /> +5% from last week
              </span>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold font-mono text-gray-400 uppercase tracking-wider block">Abstained</span>
              <div className="text-2xl font-extrabold font-display text-amber-600 mt-1">2</div>
              <span className="text-[10px] font-bold text-amber-600 flex items-center mt-1">
                <HelpCircle className="w-3 h-3 mr-0.5" /> +2% from last week
              </span>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-sm col-span-2 sm:col-span-1">
              <span className="text-[11px] font-semibold font-mono text-gray-400 uppercase tracking-wider block">Abstention Rate</span>
              <div className="text-2xl font-extrabold font-display text-gray-900 mt-1">8.3%</div>
              <span className="text-[10px] font-bold text-emerald-600 flex items-center mt-1">
                ↓ 1.4% from last week
              </span>
            </div>
          </div>

          {/* Active View Switcher */}
          {activeNav === 'new-intake' && (
            <div className="space-y-8">
              {/* Intake Form (Voice / Text) */}
              <VoiceIntake 
                onIntakeSubmit={handleIntakeSubmit} 
                isLoading={isLoading} 
              />

              {/* Classification View & Gate Triage */}
              {currentOutcome && (
                <ClassificationView 
                  outcome={currentOutcome}
                  onClarifySubmit={handleClarifySubmit}
                  isLoading={isLoading}
                />
              )}

              {/* Downstream Artifact: Municipal Ticket */}
              {currentOutcome?.status === 'routed' && currentOutcome.domain === 'infrastructure' && (
                <TicketCard 
                  artifact={currentOutcome.artifact} 
                  onReset={() => setCurrentOutcome(null)} 
                />
              )}

              {/* Downstream Artifact: Legal Brief */}
              {currentOutcome?.status === 'routed' && currentOutcome.domain === 'legal' && (
                <LegalBriefCard 
                  artifact={currentOutcome.artifact} 
                  onReset={() => setCurrentOutcome(null)} 
                />
              )}
            </div>
          )}

          {(activeNav === 'dashboard' || activeNav === 'cases' || activeNav === 'history') && (
            /* Recent Cases Table matching Screen 2 & Screen 5A of image1.jpeg */
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 lg:p-8 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-100">
                <div>
                  <h3 className="text-lg font-bold font-display text-gray-900">
                    {activeNav === 'dashboard' ? 'Recent Cases' : 'My Cases'}
                  </h3>
                  <p className="text-xs text-gray-500">Track and manage citizen reports across municipal & legal routes.</p>
                </div>

                {/* Search Bar */}
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Search cases..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 pr-4 py-2 rounded-xl bg-gray-50 border border-gray-200 text-xs focus:ring-2 focus:ring-brand-accent/50 outline-none w-48 sm:w-64"
                    />
                  </div>
                </div>
              </div>

              {/* Category Filter Pills */}
              <div className="flex flex-wrap gap-2 text-xs font-semibold">
                {[
                  { id: 'all', label: 'All' },
                  { id: 'infrastructure', label: 'Infrastructure' },
                  { id: 'legal', label: 'Legal' },
                  { id: 'abstained', label: 'Abstained' },
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setFilterCategory(tab.id)}
                    className={`px-3.5 py-1.5 rounded-lg font-display transition-all ${
                      filterCategory === tab.id
                        ? 'bg-brand-primary text-white shadow-sm'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Cases Table matching image1.jpeg */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-gray-50 text-gray-500 font-semibold border-y border-gray-200">
                    <tr>
                      <th className="py-3 px-4">Case ID</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Title</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredCases.map(item => (
                      <tr key={item.id} className="hover:bg-gray-50/80 transition-colors">
                        <td className="py-3.5 px-4 font-mono font-bold text-gray-900">{item.id}</td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                            item.type === 'infrastructure'
                              ? 'bg-emerald-100 text-emerald-800'
                              : item.type === 'legal'
                              ? 'bg-indigo-100 text-indigo-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}>
                            {item.type === 'infrastructure' && <Building2 className="w-3 h-3 mr-1" />}
                            {item.type === 'legal' && <Scale className="w-3 h-3 mr-1" />}
                            {item.type === 'abstained' && <HelpCircle className="w-3 h-3 mr-1" />}
                            {item.type}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-medium text-gray-800">{item.title}</td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            item.status === 'Completed'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : item.status === 'In Review'
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : item.status === 'Clarification Sent'
                              ? 'bg-amber-50 text-amber-700 border border-amber-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}>
                            ● {item.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-gray-400">{item.date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeNav === 'analytics' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
                <h4 className="text-base font-bold font-display text-gray-900">Gate & Benchmark Reliability</h4>
                <p className="text-xs text-gray-600">
                  Real-time confidence gating performance against 30 Tier A Nigerian Code-Switched clips.
                </p>
                <div className="space-y-3 pt-2">
                  <div className="flex justify-between text-xs font-semibold">
                    <span>Artifact-Corrupted Rate (Goal ~0%)</span>
                    <span className="text-emerald-700 font-bold font-mono">0.0%</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-600 rounded-full" style={{ width: '100%' }} />
                  </div>
                  <div className="flex justify-between text-xs font-semibold pt-2">
                    <span>Confidence Gate Abstention Rate</span>
                    <span className="text-amber-700 font-bold font-mono">8.3%</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500 rounded-full" style={{ width: '8.3%' }} />
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4">
                <h4 className="text-base font-bold font-display text-gray-900">ASR & Model Integrations</h4>
                <p className="text-xs text-gray-600">Active transcription providers & fallback routes.</p>
                <div className="space-y-2.5 text-xs">
                  <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 flex items-center justify-between">
                    <div>
                      <p className="font-bold font-display text-emerald-950">Sahara v2.5 ASR (Primary)</p>
                      <p className="text-[11px] text-emerald-700">Code-switch bilingual (Pidgin + Yoruba + English)</p>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-emerald-200 text-emerald-900 font-bold font-mono text-[10px]">Active</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 flex items-center justify-between">
                    <div>
                      <p className="font-bold font-display text-gray-900">Whisper large-v3 (Colab / Fallback)</p>
                      <p className="text-[11px] text-gray-500">Zero-downtime text/voice contingency</p>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-gray-200 text-gray-700 font-bold font-mono text-[10px]">Standby</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeNav === 'settings' && (
            <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm space-y-4 max-w-xl">
              <h4 className="text-base font-bold font-display text-gray-900">Settings</h4>
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                  <div>
                    <p className="font-bold font-display text-gray-900">Language Preference</p>
                    <p className="text-gray-500">Bilingual code-switch detection</p>
                  </div>
                  <span className="font-semibold text-brand-primary">English + Yoruba</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
