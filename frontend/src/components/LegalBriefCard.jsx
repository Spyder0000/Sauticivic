import React from 'react';
import {
  Scale,
  User,
  FileText,
  Download,
  Building,
  ShieldCheck,
  ArrowRight,
} from 'lucide-react';

import CodeSwitchTranscript, { LangLegend } from './CodeSwitchTranscript';

export default function LegalBriefCard({ artifact, onReset }) {
  if (!artifact) return null;

  const briefId = artifact.brief_id || artifact.tracking_id || 'LEG-2026-0051';
  const grievanceType = artifact.grievance_type || artifact.category || 'Tenancy Dispute & Unlawful Notice';
  const respondent = artifact.respondent_party || artifact.party || 'Landlord / Property Manager';
  const assignedNetwork = artifact.assigned_network || 'Legal Aid Council of Nigeria & Pro Bono Clearinghouse';
  const urgency = artifact.urgency || 'High';
  const facts = artifact.statement_of_facts || artifact.description
    || 'Citizen reported sudden 3-day eviction notice following maintenance dispute over roof leak and gate lock.';
  const dateStr = artifact.created_at
    || new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

  return (
    <section className="rounded-xl2 bg-surface shadow-card ring-1 ring-line/70 overflow-hidden animate-settle">
      {/* Counsel band */}
      <div className="bg-iris text-white px-6 lg:px-8 py-5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center shrink-0">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-display text-lg tracking-tight">Prepared for legal aid</h3>
            <p className="text-xs text-iris-light/90 mt-0.5">A structured brief a paralegal can act on — in the citizen's own words.</p>
          </div>
        </div>
        <span className="hidden sm:inline-flex px-3 py-1 rounded-full bg-white/15 text-[11px] font-mono uppercase tracking-[0.12em]">
          Legal brief
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-px bg-line/70">
        {/* Brief body */}
        <div className="lg:col-span-8 bg-surface p-6 lg:p-8 space-y-6">
          <div className="flex items-end justify-between gap-4 pb-5 border-b border-line/70">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted">Intake reference</span>
              <div className="font-mono text-2xl font-bold text-ink tracking-tight mt-0.5">{briefId}</div>
            </div>
            <span className="px-3 py-1 rounded-full bg-iris/10 text-iris text-xs font-semibold ring-1 ring-iris/20 whitespace-nowrap">
              ● Ready for counsel
            </span>
          </div>

          <dl className="grid grid-cols-2 gap-4">
            <div className="rounded-2xl bg-paper ring-1 ring-line/70 p-4">
              <dt className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted mb-1">Nature of grievance</dt>
              <dd className="font-semibold text-ink">{grievanceType}</dd>
            </div>
            <div className="rounded-2xl bg-paper ring-1 ring-line/70 p-4">
              <dt className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted mb-1.5">Urgency</dt>
              <dd>
                <span className={`inline-flex px-2.5 py-0.5 rounded-md text-xs font-mono font-semibold ${
                  urgency.toLowerCase() === 'high' ? 'bg-gold/15 text-gold-deep' : 'bg-iris/10 text-iris'
                }`}>
                  {urgency} priority
                </span>
              </dd>
            </div>
            <div className="rounded-2xl bg-paper ring-1 ring-line/70 p-4 col-span-2">
              <dt className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted mb-1 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-iris" /> Respondent / adverse party
              </dt>
              <dd className="font-semibold text-ink">{respondent}</dd>
            </div>
          </dl>

          {/* Statement of Facts — the citizen's own voice, preserved */}
          <div className="rounded-2xl bg-warm grain ring-1 ring-line/70 p-5">
            <div className="flex items-center justify-between gap-3 mb-3">
              <h5 className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-iris" /> Statement of facts — as spoken
              </h5>
              <LangLegend />
            </div>
            <CodeSwitchTranscript text={facts} className="text-lg leading-relaxed" />
            <p className="text-[11px] text-muted/70 mt-3 pt-3 border-t border-line/60">
              Recorded verbatim and preserved in the languages spoken — nothing translated away before counsel sees it.
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-stretch gap-3 pt-5 border-t border-line/70">
            <button
              onClick={() => alert(`Exporting signed PDF legal brief for ${briefId}…`)}
              className="flex-1 px-4 py-2.5 rounded-full bg-paper hover:bg-line/60 text-ink text-sm font-semibold inline-flex items-center justify-center gap-2 transition-colors"
            >
              <Download className="w-4 h-4" /> Export signed brief (PDF)
            </button>
            <button
              onClick={onReset}
              className="px-5 py-2.5 rounded-full bg-iris hover:bg-iris/90 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 transition-colors"
            >
              New intake <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Routing / network column */}
        <div className="lg:col-span-4 bg-surface p-6 lg:p-8 space-y-6">
          <div>
            <h5 className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted mb-3 flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5 text-iris" /> Legal aid network
            </h5>
            <p className="text-sm font-semibold text-ink mb-2">{assignedNetwork}</p>
            <p className="text-xs text-muted leading-relaxed">
              Indexed with statutory legal-aid providers. A duty counsel will review jurisdiction and the
              rights-protection remedies available.
            </p>
          </div>

          <div className="rounded-2xl bg-iris-light ring-1 ring-iris/20 p-4">
            <div className="flex items-center gap-2 mb-1.5">
              <ShieldCheck className="w-4 h-4 text-iris" />
              <span className="text-xs font-semibold text-iris">Confidential</span>
            </div>
            <p className="text-xs text-ink/75 leading-relaxed">
              Initial merit review within 24 hours. Your account is protected under the Legal Aid charter.
            </p>
          </div>

          <div className="pt-4 border-t border-line/70">
            <span className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted">Filed</span>
            <p className="text-sm font-medium text-ink mt-0.5">{dateStr}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
