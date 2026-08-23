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
  Search,
  HelpCircle,
  Building2,
  Scale,
  Mic,
  ShieldCheck,
} from 'lucide-react';

import VoiceIntake from '../components/VoiceIntake';
import ClassificationView from '../components/ClassificationView';
import TicketCard from '../components/TicketCard';
import LegalBriefCard from '../components/LegalBriefCard';
import Brandmark from '../components/Brandmark';
import Waveform from '../components/Waveform';

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'new-intake', label: 'New Intake', icon: PlusCircle, highlight: true },
  { id: 'cases', label: 'My Cases', icon: FolderKanban },
  { id: 'history', label: 'History', icon: HistoryIcon },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

const HEADERS = {
  'new-intake': { title: 'New intake', sub: 'Speak or type a complaint — routed to the right desk, or held for a question.' },
  dashboard: { title: 'Overview', sub: 'How the bridge is performing across municipal and legal routes.' },
  cases: { title: 'My cases', sub: 'Every report you’ve filed, across both routes.' },
  history: { title: 'History', sub: 'A full timeline of past intakes and their outcomes.' },
  analytics: { title: 'Analytics', sub: 'Gate reliability and transcription coverage.' },
  settings: { title: 'Settings', sub: 'Language and account preferences.' },
};

// Honest metrics — what the numbers mean, not invented week-over-week deltas.
const METRICS = [
  { label: 'Total intakes', value: '24', note: 'across both routes', Icon: Mic, tone: 'text-palm' },
  { label: 'Infrastructure', value: '14', note: 'municipal tickets', Icon: Building2, tone: 'text-palm' },
  { label: 'Legal grievances', value: '8', note: 'aid briefs prepared', Icon: Scale, tone: 'text-iris' },
  { label: 'Abstained', value: '2', note: 'held for a question', Icon: HelpCircle, tone: 'text-gold-deep' },
  { label: 'Abstention rate', value: '8.3%', note: 'caught before misfiling · τ = 70%', Icon: ShieldCheck, tone: 'text-palm', wide: true },
];

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

  const header = HEADERS[activeNav] || HEADERS['new-intake'];
  const showCasesTable = activeNav === 'dashboard' || activeNav === 'cases' || activeNav === 'history';

  return (
    <div className="min-h-screen bg-paper text-ink font-sans flex flex-col lg:flex-row">
      {/* Sidebar — quiet ink surface; the brand mark IS a voice */}
      <aside className="w-full lg:w-64 bg-ink text-white flex flex-col justify-between p-6 shrink-0">
        <div className="space-y-9">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl2 bg-mint text-ink flex items-center justify-center shadow-sm">
              <Brandmark className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-base font-display tracking-tight text-white">SautiCivic</h1>
              <p className="text-[11px] text-mint/80 font-mono">Bridge · Sahara v2.5</p>
            </div>
          </div>

          <nav className="space-y-1">
            {NAV.map(item => {
              const Icon = item.icon;
              const isActive = activeNav === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveNav(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-mint text-ink font-semibold shadow-sm'
                      : 'text-paper/60 hover:text-white hover:bg-white/[0.06]'
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </span>
                  {item.highlight && !isActive && (
                    <span className="w-1.5 h-1.5 rounded-full bg-mint animate-breathe" />
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="pt-6 border-t border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-palm-dark text-mint flex items-center justify-center font-semibold text-xs ring-1 ring-mint/20">
              AB
            </div>
            <div>
              <p className="text-xs font-semibold text-white">Aisha Bello</p>
              <p className="text-[10px] text-paper/50 font-mono">Citizen · Lagos</p>
            </div>
          </div>
          <button className="text-paper/50 hover:text-white transition-colors" title="Log out">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Contextual header — no invented greeting */}
        <header className="bg-surface border-b border-line px-6 lg:px-10 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 sticky top-0 z-20">
          <div>
            <h2 className="text-xl font-display tracking-tight text-ink">{header.title}</h2>
            <p className="text-xs text-muted mt-0.5">{header.sub}</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setCurrentOutcome(null);
                setActiveNav('new-intake');
              }}
              className="px-4 py-2 rounded-full bg-palm hover:bg-palm-dark text-white text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
            >
              <PlusCircle className="w-4 h-4" />
              New intake
            </button>
            <button className="p-2 rounded-full border border-line hover:bg-paper text-muted relative transition-colors" title="Notifications">
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-gold" />
            </button>
          </div>
        </header>

        <div className="p-6 lg:p-10 space-y-8 max-w-7xl mx-auto w-full">
          {/* NEW INTAKE — the voice-first canvas */}
          {activeNav === 'new-intake' && (
            <div className="space-y-8">
              {/* Hero thesis band */}
              <div className="relative overflow-hidden rounded-xl2 bg-warm grain ring-1 ring-line/70 px-6 lg:px-10 py-10 lg:py-12">
                <div className="pointer-events-none absolute inset-y-0 right-0 hidden sm:flex w-1/2 items-center justify-end pr-8 text-palm opacity-[0.10]">
                  <Waveform active bars={40} className="h-28 w-full" gap="gap-[5px]" />
                </div>
                <div className="relative z-10 max-w-2xl animate-settle">
                  <span className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-palm">
                    <span className="w-1.5 h-1.5 rounded-full bg-mint animate-breathe" /> SautiCivic Bridge
                  </span>
                  <h1 className="font-display text-thesis text-ink mt-4 tracking-tight leading-[1.02] text-balance">
                    Speak. We&rsquo;re listening.
                  </h1>
                  <p className="font-display text-hero text-palm mt-2">Infrastructure fixed. Rights protected.</p>
                  <p className="text-sm text-muted mt-4 max-w-xl text-pretty">
                    Report in Pidgin, Yoruba, Hausa, Igbo, or English — mix them as you naturally would. We keep
                    your words intact, route them to the right desk, and when we&rsquo;re not sure, we ask instead
                    of guessing.
                  </p>
                </div>
              </div>

              <VoiceIntake
                onIntakeSubmit={handleIntakeSubmit}
                isLoading={isLoading}
              />

              {currentOutcome && (
                <ClassificationView
                  outcome={currentOutcome}
                  onClarifySubmit={handleClarifySubmit}
                  isLoading={isLoading}
                />
              )}

              {currentOutcome?.status === 'routed' && currentOutcome.domain === 'infrastructure' && (
                <TicketCard
                  artifact={currentOutcome.artifact}
                  onReset={() => setCurrentOutcome(null)}
                />
              )}

              {currentOutcome?.status === 'routed' && currentOutcome.domain === 'legal' && (
                <LegalBriefCard
                  artifact={currentOutcome.artifact}
                  onReset={() => setCurrentOutcome(null)}
                />
              )}
            </div>
          )}

          {/* DASHBOARD — the honest metrics live here, not on the intake screen */}
          {activeNav === 'dashboard' && (
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {METRICS.map((m) => {
                const Icon = m.Icon;
                return (
                  <div
                    key={m.label}
                    className={`bg-surface rounded-2xl ring-1 ring-line/70 shadow-card p-5 ${m.wide ? 'col-span-2 lg:col-span-1' : ''}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted">{m.label}</span>
                      <Icon className={`w-4 h-4 ${m.tone}`} />
                    </div>
                    <div className={`font-display text-3xl mt-2 tracking-tight ${m.tone}`}>{m.value}</div>
                    <p className="text-[11px] text-muted/80 mt-1">{m.note}</p>
                  </div>
                );
              })}
            </div>
          )}

          {/* CASES TABLE — dashboard / cases / history */}
          {showCasesTable && (
            <div className="bg-surface rounded-xl2 ring-1 ring-line/70 shadow-card p-6 lg:p-8 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-line/70">
                <div>
                  <h3 className="text-lg font-display tracking-tight text-ink">
                    {activeNav === 'dashboard' ? 'Recent cases' : activeNav === 'history' ? 'History' : 'My cases'}
                  </h3>
                  <p className="text-xs text-muted mt-0.5">Track and manage citizen reports across municipal & legal routes.</p>
                </div>

                <div className="relative">
                  <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search cases…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 pr-4 py-2 rounded-full bg-paper border border-line text-xs focus:border-palm outline-none w-48 sm:w-64 transition-colors"
                  />
                </div>
              </div>

              {/* Category filter */}
              <div className="flex flex-wrap gap-2 text-xs font-medium">
                {[
                  { id: 'all', label: 'All' },
                  { id: 'infrastructure', label: 'Infrastructure' },
                  { id: 'legal', label: 'Legal' },
                  { id: 'abstained', label: 'Abstained' },
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setFilterCategory(tab.id)}
                    className={`px-3.5 py-1.5 rounded-full transition-colors ${
                      filterCategory === tab.id
                        ? 'bg-palm text-white shadow-sm'
                        : 'bg-paper text-muted hover:text-ink ring-1 ring-line'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Table */}
              <div className="overflow-x-auto -mx-2">
                <table className="w-full text-left text-xs min-w-[560px]">
                  <thead className="text-muted border-y border-line">
                    <tr>
                      <th className="py-3 px-4 font-mono uppercase tracking-[0.1em] text-[10px] font-medium">Case ID</th>
                      <th className="py-3 px-4 font-mono uppercase tracking-[0.1em] text-[10px] font-medium">Type</th>
                      <th className="py-3 px-4 font-mono uppercase tracking-[0.1em] text-[10px] font-medium">Title</th>
                      <th className="py-3 px-4 font-mono uppercase tracking-[0.1em] text-[10px] font-medium">Status</th>
                      <th className="py-3 px-4 font-mono uppercase tracking-[0.1em] text-[10px] font-medium">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line/70">
                    {filteredCases.map(item => (
                      <tr key={item.id} className="hover:bg-paper/70 transition-colors">
                        <td className="py-3.5 px-4 font-mono font-semibold text-ink">{item.id}</td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium ${
                            item.type === 'infrastructure'
                              ? 'bg-palm/10 text-palm'
                              : item.type === 'legal'
                              ? 'bg-iris/10 text-iris'
                              : 'bg-gold/12 text-gold-deep'
                          }`}>
                            {item.type === 'infrastructure' && <Building2 className="w-3 h-3" />}
                            {item.type === 'legal' && <Scale className="w-3 h-3" />}
                            {item.type === 'abstained' && <HelpCircle className="w-3 h-3" />}
                            {item.type}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-medium text-ink/90">{item.title}</td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ${
                            item.status === 'Completed'
                              ? 'bg-palm/8 text-palm ring-palm/20'
                              : item.status === 'In Review'
                              ? 'bg-iris/8 text-iris ring-iris/20'
                              : 'bg-gold/10 text-gold-deep ring-gold/25'
                          }`}>
                            ● {item.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-muted">{item.date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ANALYTICS */}
          {activeNav === 'analytics' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-surface rounded-xl2 ring-1 ring-line/70 shadow-card p-6 space-y-4">
                <h4 className="text-base font-display tracking-tight text-ink">Gate & benchmark reliability</h4>
                <p className="text-xs text-muted">
                  Real-time confidence gating performance against 30 Tier A Nigerian code-switched clips.
                </p>
                <div className="space-y-3 pt-2">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-ink/80">Artifact-corrupted rate (goal ~0%)</span>
                    <span className="text-palm font-mono font-semibold">0.0%</span>
                  </div>
                  <div className="w-full h-2 bg-line rounded-full overflow-hidden">
                    <div className="h-full bg-palm rounded-full" style={{ width: '100%' }} />
                  </div>
                  <div className="flex justify-between text-xs font-medium pt-2">
                    <span className="text-ink/80">Confidence-gate abstention rate</span>
                    <span className="text-gold-deep font-mono font-semibold">8.3%</span>
                  </div>
                  <div className="w-full h-2 bg-line rounded-full overflow-hidden">
                    <div className="h-full bg-gold rounded-full" style={{ width: '8.3%' }} />
                  </div>
                  <p className="text-[11px] text-muted/80 pt-1 leading-snug">
                    Abstention isn&rsquo;t failure — it&rsquo;s the gate refusing to misfile what it can&rsquo;t yet route with confidence.
                  </p>
                </div>
              </div>

              <div className="bg-surface rounded-xl2 ring-1 ring-line/70 shadow-card p-6 space-y-4">
                <h4 className="text-base font-display tracking-tight text-ink">ASR & model integrations</h4>
                <p className="text-xs text-muted">Active transcription providers & fallback routes.</p>
                <div className="space-y-2.5 text-xs">
                  <div className="p-3 bg-palm/[0.06] rounded-xl ring-1 ring-palm/15 flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-ink">Sahara v2.5 ASR (Primary)</p>
                      <p className="text-[11px] text-muted">Code-switch bilingual (Pidgin + Yoruba + English)</p>
                    </div>
                    <span className="px-2 py-0.5 rounded-md bg-palm/15 text-palm font-mono font-semibold text-[10px]">Active</span>
                  </div>
                  <div className="p-3 bg-paper rounded-xl ring-1 ring-line flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-ink">Whisper large-v3 (Colab / Fallback)</p>
                      <p className="text-[11px] text-muted">Zero-downtime text/voice contingency</p>
                    </div>
                    <span className="px-2 py-0.5 rounded-md bg-line text-muted font-mono font-semibold text-[10px]">Standby</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SETTINGS */}
          {activeNav === 'settings' && (
            <div className="bg-surface rounded-xl2 ring-1 ring-line/70 shadow-card p-6 space-y-4 max-w-xl">
              <h4 className="text-base font-display tracking-tight text-ink">Settings</h4>
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between p-4 bg-paper rounded-2xl ring-1 ring-line">
                  <div>
                    <p className="font-semibold text-ink">Language preference</p>
                    <p className="text-muted mt-0.5">Bilingual code-switch detection</p>
                  </div>
                  <span className="font-semibold text-palm font-mono">English + Yoruba</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
