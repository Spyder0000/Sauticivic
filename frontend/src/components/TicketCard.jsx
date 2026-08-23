import React from 'react';
import {
  CheckCircle2,
  MapPin,
  Building2,
  Download,
  Navigation,
  ArrowRight,
} from 'lucide-react';

export default function TicketCard({ artifact, onReset }) {
  if (!artifact) return null;

  const ticketId = artifact.tracking_id || artifact.ticket_id || 'GRA-2026-0087';
  const category = artifact.complaint_type || artifact.category || 'Blocked Drainage & Flood Risk';
  const location = artifact.location || 'Alagomeji, Yaba, Lagos Mainland';
  const assignedTo = artifact.assigned_department || 'Lagos State Ministry of the Environment & Water Resources';
  const priority = artifact.priority || 'High';
  const status = artifact.status || 'Accepted & Dispatched';
  const dateStr = artifact.created_at
    || new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

  const steps = [
    { title: 'Logged & dispatched', body: 'Your report is filed and queued for inspection.', done: true },
    { title: 'Field officer inspects', body: 'A physical inspection is scheduled within 24–48 hours.', done: false },
    { title: 'Updates by SMS & WhatsApp', body: 'You hear from us as maintenance begins.', done: false },
  ];

  return (
    <section className="rounded-xl2 bg-surface shadow-card ring-1 ring-line/70 overflow-hidden animate-settle">
      {/* Dispatch band */}
      <div className="bg-palm text-white px-6 lg:px-8 py-5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-display text-lg tracking-tight">Sent to municipal services</h3>
            <p className="text-xs text-mint-soft/90 mt-0.5">Logged, geo-tagged, and assigned to the responsible agency.</p>
          </div>
        </div>
        <span className="hidden sm:inline-flex px-3 py-1 rounded-full bg-white/15 text-[11px] font-mono uppercase tracking-[0.12em]">
          Municipal ticket
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-px bg-line/70">
        {/* Ticket body */}
        <div className="lg:col-span-7 bg-surface p-6 lg:p-8 space-y-6">
          <div className="flex items-end justify-between gap-4 pb-5 border-b border-line/70">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted">Tracking ID</span>
              <div className="font-mono text-2xl font-bold text-ink tracking-tight mt-0.5">{ticketId}</div>
            </div>
            <span className="px-3 py-1 rounded-full bg-palm/10 text-palm text-xs font-semibold ring-1 ring-palm/20 whitespace-nowrap">
              ● {status}
            </span>
          </div>

          <dl className="grid grid-cols-2 gap-4">
            <div className="rounded-2xl bg-paper ring-1 ring-line/70 p-4">
              <dt className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted mb-1">Issue category</dt>
              <dd className="font-semibold text-ink">{category}</dd>
            </div>
            <div className="rounded-2xl bg-paper ring-1 ring-line/70 p-4">
              <dt className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted mb-1.5">Priority</dt>
              <dd>
                <span className={`inline-flex px-2.5 py-0.5 rounded-md text-xs font-mono font-semibold ${
                  priority.toLowerCase() === 'high' ? 'bg-gold/15 text-gold-deep' : 'bg-palm/10 text-palm'
                }`}>
                  {priority}
                </span>
              </dd>
            </div>
            <div className="rounded-2xl bg-paper ring-1 ring-line/70 p-4 col-span-2">
              <dt className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted mb-1 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-palm" /> Location & landmark
              </dt>
              <dd className="font-semibold text-ink">{location}</dd>
            </div>
            <div className="rounded-2xl bg-paper ring-1 ring-line/70 p-4 col-span-2">
              <dt className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted mb-1 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-palm" /> Dispatched to
              </dt>
              <dd className="font-medium text-ink text-sm">{assignedTo}</dd>
            </div>
          </dl>

          <div className="flex flex-col sm:flex-row items-stretch gap-3 pt-5 border-t border-line/70">
            <button
              onClick={() => alert(`Preparing dispatch receipt for ${ticketId}…`)}
              className="flex-1 px-4 py-2.5 rounded-full bg-paper hover:bg-line/60 text-ink text-sm font-semibold inline-flex items-center justify-center gap-2 transition-colors"
            >
              <Download className="w-4 h-4" /> Download receipt
            </button>
            <button
              onClick={onReset}
              className="px-5 py-2.5 rounded-full bg-palm hover:bg-palm-dark text-white text-sm font-semibold inline-flex items-center justify-center gap-2 transition-colors"
            >
              New intake <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Next steps + geo */}
        <div className="lg:col-span-5 bg-surface p-6 lg:p-8 space-y-6">
          <div>
            <h5 className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted mb-4">What happens next</h5>
            <ol className="space-y-4">
              {steps.map((s, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-mono font-semibold shrink-0 ${
                    s.done ? 'bg-palm text-white' : 'bg-paper text-muted ring-1 ring-line'
                  }`}>
                    {s.done ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-ink">{s.title}</p>
                    <p className="text-xs text-muted mt-0.5 leading-snug">{s.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          {/* Geo-tag card */}
          <div className="relative rounded-2xl overflow-hidden ring-1 ring-line h-44 field-warm">
            <svg className="absolute inset-0 w-full h-full text-palm/15" aria-hidden="true">
              <defs>
                <pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">
                  <path d="M22 0H0V22" fill="none" stroke="currentColor" strokeWidth="1" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>
            <div className="relative z-10 h-full flex flex-col justify-between p-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface/90 text-palm text-[11px] font-semibold shadow-sm">
                  <Navigation className="w-3 h-3" /> Geo-tagged
                </span>
                <span className="text-[11px] font-mono text-muted">6.5000° N, 3.3792° E</span>
              </div>
              <div className="flex items-center gap-2.5 bg-surface/95 backdrop-blur px-3 py-2.5 rounded-xl shadow-sm">
                <MapPin className="w-5 h-5 text-gold-deep shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-ink">{location}</p>
                  <p className="text-[10px] text-muted">Filed {dateStr}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
