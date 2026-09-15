import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  HelpCircle,
  CheckCircle2,
  Send,
  ArrowRight,
  MapPin,
  User,
  Tag,
  Building2,
  Scale,
} from 'lucide-react';

const ENTITY_ICON = {
  location: MapPin,
  party: User,
  complaint_type: Tag,
  grievance_type: Scale,
};

export default function ClassificationView({ outcome, onClarifySubmit, isLoading }) {
  const [clarifyAnswer, setClarifyAnswer] = useState('');
  const [meterW, setMeterW] = useState(0);

  if (!outcome) return null;

  const isEmergency = outcome.status === 'emergency_recommendation';
  const isAbstain = outcome.status === 'needs_clarification' || isEmergency;
  const classification = outcome.classification || {};
  const extraction = outcome.extraction || { entities: [] };
  const confidencePercent = classification.confidence ? Math.round(classification.confidence * 100) : 85;
  const isInfra = outcome.domain === 'infrastructure';

  // Fill the confidence meter once, from zero.
  useEffect(() => {
    const id = requestAnimationFrame(() => setMeterW(confidencePercent));
    return () => cancelAnimationFrame(id);
  }, [confidencePercent]);

  const quickAnswers = [
    { label: "It's a legal matter — a person, landlord, or my rights", Icon: Scale },
    { label: "It's public infrastructure — roads, water, power", Icon: Building2 },
    { label: 'Not sure — connect me with a person', Icon: User },
  ];

  const handleQuickSelect = (answer) => {
    setClarifyAnswer(answer);
    if (outcome.session_id) onClarifySubmit(answer);
  };

  const handleCustomSubmit = (e) => {
    e.preventDefault();
    if (clarifyAnswer.trim() && outcome.session_id) onClarifySubmit(clarifyAnswer.trim());
  };

  // Accent tokens per outcome
  const accent = isAbstain
    ? { chip: 'bg-gold/12 text-gold-deep ring-gold/30', icon: 'bg-gold/12 text-gold-deep', bar: 'bg-gold' }
    : isInfra
    ? { chip: 'bg-palm/10 text-palm ring-palm/25', icon: 'bg-palm/10 text-palm', bar: 'bg-palm' }
    : { chip: 'bg-iris/10 text-iris ring-iris/25', icon: 'bg-iris/10 text-iris', bar: 'bg-iris' };

  return (
    <div className="space-y-5">
      {/* Routing decision */}
      <section className="rounded-xl2 bg-surface shadow-card ring-1 ring-line/70 p-6 lg:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-line/70">
          <div className="flex items-center gap-3.5">
            <div className={`w-11 h-11 rounded-2xl flex items-center justify-center ${accent.icon}`}>
              {isAbstain ? <HelpCircle className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
            </div>
            <div>
              <h3 className="font-display text-xl text-ink tracking-tight">
                {isEmergency ? 'Immediate safety recommendation' : isAbstain ? 'Held for one question' : 'Routing decision'}
              </h3>
              <p className="text-xs text-muted mt-0.5">
                Session <span className="font-mono text-ink/70">{outcome.session_id || 'sess-local-01'}</span>
              </p>
            </div>
          </div>

          <span className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold ring-1 ${accent.chip}`}>
            {isAbstain ? (
              <><HelpCircle className="w-3.5 h-3.5" /> {isEmergency ? 'Emergency recommendation' : 'Abstained — asking first'}</>
            ) : isInfra ? (
              <><CheckCircle2 className="w-3.5 h-3.5" /> Routed to municipal services</>
            ) : (
              <><CheckCircle2 className="w-3.5 h-3.5" /> Routed to legal aid</>
            )}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-5 mt-6">
          {/* Confidence */}
          <div className="md:col-span-4 rounded-2xl bg-paper ring-1 ring-line/70 p-4">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted">Routing confidence</span>
              <span className={`text-sm font-mono font-bold ${confidencePercent >= 70 ? 'text-palm' : 'text-gold-deep'}`}>
                {confidencePercent}%
              </span>
            </div>
            <div className="w-full h-2 bg-line rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-[width] duration-700 ease-out ${confidencePercent >= 70 ? 'bg-palm' : 'bg-gold'}`}
                style={{ width: `${meterW}%` }}
              />
            </div>
            <p className="text-[11px] text-muted/80 mt-2.5 leading-snug">
              Threshold <span className="font-mono">τ = 70%</span>. The gate weighs clarity and whether the
              entities needed to act are present.
            </p>
          </div>

          {/* Entities */}
          <div className="md:col-span-8 rounded-2xl bg-paper ring-1 ring-line/70 p-4">
            <span className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted block mb-3">What we extracted</span>
            <div className="flex flex-wrap gap-2">
              {extraction.entities && extraction.entities.length > 0 ? (
                extraction.entities.map((ent, i) => {
                  const Icon = ENTITY_ICON[ent.type] || Tag;
                  return (
                    <span key={i} className="inline-flex items-center gap-1.5 pl-2 pr-2.5 py-1.5 rounded-xl bg-surface ring-1 ring-line text-xs">
                      <Icon className="w-3.5 h-3.5 text-palm" />
                      <span className="text-muted capitalize">{ent.type.replace('_', ' ')}</span>
                      <span className="font-semibold text-ink">{ent.value}</span>
                      <span className="font-mono text-[10px] text-muted/70">{Math.round(ent.confidence * 100)}%</span>
                    </span>
                  );
                })
              ) : (
                <span className="text-sm text-muted/70 italic font-serif">No location or named party is clear yet — that's exactly why we're asking.</span>
              )}
            </div>
          </div>
        </div>

        {/* Audit reasoning — plain, honest, one chip per reason */}
        {outcome.reasons && outcome.reasons.length > 0 && (
          <div className="mt-5 pt-5 border-t border-line/70">
            <span className="text-[11px] font-mono uppercase tracking-[0.14em] text-muted block mb-2.5">Why — the audit trail</span>
            <div className="flex flex-wrap gap-2">
              {outcome.reasons.map((reason, i) => (
                <span key={i} className="inline-flex items-start gap-1.5 px-3 py-1.5 rounded-lg bg-paper ring-1 ring-line text-xs text-ink/80">
                  <span className="font-mono text-muted/60 mt-px">{String(i + 1).padStart(2, '0')}</span>
                  {reason}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* The gate — a calm request, not an error */}
      {isAbstain && (
        <section className="rounded-xl2 bg-warm grain ring-1 ring-gold/30 shadow-card p-6 lg:p-8">
          <div className="flex items-start gap-4 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-gold/15 text-gold-deep flex items-center justify-center shrink-0">
              <HelpCircle className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-display text-xl text-ink tracking-tight">{isEmergency ? 'Please put safety first' : "We'd rather ask than guess"}</h4>
              <p className="text-sm text-muted mt-1 max-w-xl text-pretty">
                {isEmergency ? 'This is an escalation recommendation, not an emergency dispatch. Contact 112 or your local emergency number if anyone is in immediate danger.' : "Sending this to the wrong place would cost you time — or worse. One quick answer and we'll route it right."}
              </p>
            </div>
          </div>

          <div className="rounded-2xl bg-surface ring-1 ring-gold/25 p-5 mb-6">
            <span className="text-[11px] font-mono uppercase tracking-[0.14em] text-gold-deep">Our question</span>
            <p className="font-serif text-xl text-ink mt-1.5 leading-snug text-pretty">
              {outcome.clarifying_question
                || 'Is this about public infrastructure — drainage, roads, power — or a private legal matter like tenancy, threats, or your rights?'}
            </p>
          </div>

          {!isEmergency && <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
            {quickAnswers.map(({ label, Icon }, idx) => (
              <button
                key={idx}
                onClick={() => handleQuickSelect(label)}
                disabled={isLoading}
                className="group text-left p-4 rounded-2xl bg-surface ring-1 ring-line hover:ring-palm hover:bg-palm/[0.04] transition-all active:scale-[0.98] disabled:opacity-50 flex flex-col gap-2.5"
              >
                <span className="w-8 h-8 rounded-xl bg-paper group-hover:bg-palm/10 flex items-center justify-center transition-colors">
                  <Icon className="w-4 h-4 text-palm" />
                </span>
                <span className="text-xs font-medium text-ink leading-snug">{label}</span>
              </button>
            ))}
          </div>}

          {!isEmergency && <form onSubmit={handleCustomSubmit} className="flex flex-col sm:flex-row gap-3 pt-5 border-t border-gold/20">
            <input
              type="text"
              value={clarifyAnswer}
              onChange={(e) => setClarifyAnswer(e.target.value)}
              placeholder="Or say it in your own words — e.g. “na my landlord for Ikeja”…"
              className="flex-1 px-4 py-2.5 rounded-full bg-surface border border-line text-base focus:border-palm outline-none transition-colors"
            />
            <button
              type="submit"
              disabled={isLoading || !clarifyAnswer.trim()}
              className="px-5 py-2.5 rounded-full bg-palm hover:bg-palm-dark text-white text-sm font-semibold inline-flex items-center justify-center gap-2 transition-all disabled:opacity-40"
            >
              <Send className="w-3.5 h-3.5" /> Send answer
            </button>
          </form>}
        </section>
      )}
    </div>
  );
}
