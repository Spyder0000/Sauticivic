import React, { useState } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  HelpCircle, 
  CheckCircle2, 
  Send, 
  Info,
  ArrowRight,
  MapPin,
  User
} from 'lucide-react';

export default function ClassificationView({ outcome, onClarifySubmit, isLoading }) {
  const [clarifyAnswer, setClarifyAnswer] = useState('');

  if (!outcome) return null;

  const isAbstain = outcome.status === 'needs_clarification';
  const classification = outcome.classification || {};
  const extraction = outcome.extraction || { entities: [] };
  const confidencePercent = classification.confidence ? Math.round(classification.confidence * 100) : 85;

  const quickAnswers = [
    "Yes, it's a legal matter involving a landlord/person",
    "No, it's about public infrastructure and street maintenance",
    "Not sure, please connect me with a human representative"
  ];

  const handleQuickSelect = (answer) => {
    setClarifyAnswer(answer);
    if (outcome.session_id) {
      onClarifySubmit(answer);
    }
  };

  const handleCustomSubmit = (e) => {
    e.preventDefault();
    if (clarifyAnswer.trim() && outcome.session_id) {
      onClarifySubmit(clarifyAnswer.trim());
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Main AI Routing & Gate Decision Header Card */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 lg:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-100">
          <div className="flex items-center space-x-3">
            <div className={`p-2.5 rounded-xl ${
              isAbstain 
                ? 'bg-amber-50 text-amber-600' 
                : outcome.domain === 'infrastructure'
                ? 'bg-emerald-50 text-emerald-600'
                : 'bg-indigo-50 text-indigo-600'
            }`}>
              {isAbstain ? (
                <AlertTriangle className="w-6 h-6" />
              ) : (
                <ShieldCheck className="w-6 h-6" />
              )}
            </div>
            <div>
              <h3 className="text-lg font-bold font-display text-gray-900">
                {isAbstain ? "Confidence Gate: Clarification Needed" : "Intake Routing Decision"}
              </h3>
              <p className="text-xs text-gray-500">
                Session ID: <span className="font-mono text-gray-700">{outcome.session_id || 'sess-local-01'}</span>
              </p>
            </div>
          </div>

          <div>
            {isAbstain ? (
              <span className="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-bold font-display bg-amber-100 text-amber-800 border border-amber-300">
                <HelpCircle className="w-3.5 h-3.5 mr-1.5 text-amber-700" />
                Needs Clarification (Abstained)
              </span>
            ) : outcome.domain === 'infrastructure' ? (
              <span className="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-bold font-display bg-emerald-100 text-emerald-800 border border-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-700" />
                Infrastructure Dispatched
              </span>
            ) : (
              <span className="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-bold font-display bg-indigo-100 text-indigo-800 border border-indigo-300">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-indigo-700" />
                Legal Aid Brief Generated
              </span>
            )}
          </div>
        </div>

        {/* Confidence & Explainability Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 mt-6">
          <div className="md:col-span-4 bg-[#F8FAFB] p-4 rounded-xl border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-600">Routing Confidence</span>
              <span className={`text-sm font-bold font-mono ${
                confidencePercent >= 75 ? 'text-emerald-700' : 'text-amber-700'
              }`}>
                {confidencePercent}%
              </span>
            </div>
            <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-500 rounded-full ${
                  confidencePercent >= 75 ? 'bg-emerald-600' : 'bg-amber-500'
                }`}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
            <p className="text-[11px] text-gray-400 mt-2">
              Threshold τ = 70% · Gate evaluates clarity + required entities
            </p>
          </div>

          <div className="md:col-span-8 bg-[#F8FAFB] p-4 rounded-xl border border-gray-200 flex flex-col justify-between">
            <span className="text-xs font-semibold text-gray-600 mb-2 font-mono">Extracted Entities & Tags:</span>
            <div className="flex flex-wrap gap-2">
              {extraction.entities && extraction.entities.length > 0 ? (
                extraction.entities.map((ent, i) => (
                  <span 
                    key={i} 
                    className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium bg-white text-gray-800 border border-gray-200 shadow-sm"
                  >
                    {ent.type === 'location' && <MapPin className="w-3 h-3 text-red-500 mr-1" />}
                    {ent.type === 'party' && <User className="w-3 h-3 text-indigo-500 mr-1" />}
                    <span className="capitalize text-gray-500 mr-1">{ent.type}:</span>
                    <span className="font-semibold text-gray-900">{ent.value}</span>
                    <span className="ml-1.5 text-[10px] font-mono text-gray-400">({Math.round(ent.confidence * 100)}%)</span>
                  </span>
                ))
              ) : (
                <span className="text-xs text-gray-400 italic">No specific location or named parties extracted yet.</span>
              )}
            </div>
          </div>
        </div>

        {outcome.reasons && outcome.reasons.length > 0 && (
          <div className="mt-4 p-3 bg-gray-50 rounded-xl border border-gray-200 text-xs text-gray-600 flex items-start space-x-2">
            <Info className="w-4 h-4 text-brand-primary shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-gray-800">Gate Audit Reasoning: </span>
              {outcome.reasons.join(' · ')}
            </div>
          </div>
        )}
      </div>

      {/* 2. Interactive Clarification Flow (Screen 5B in image1.jpeg) */}
      {isAbstain && (
        <div className="bg-white rounded-2xl border-2 border-amber-300 shadow-md p-6 lg:p-8 relative overflow-hidden">
          <div className="flex items-start space-x-4 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-amber-500 text-white flex items-center justify-center font-display font-bold text-xl shrink-0 shadow-sm">
              ?
            </div>
            <div>
              <h4 className="text-lg font-bold font-display text-gray-900">We need a bit more information</h4>
              <p className="text-xs text-gray-600 mt-0.5">
                We weren't confident enough to route this safely. Please help us understand your situation.
              </p>
            </div>
          </div>

          <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 mb-6">
            <span className="text-xs font-bold font-mono text-amber-900 uppercase tracking-wide">Question for Citizen:</span>
            <p className="text-sm font-semibold text-gray-900 mt-1">
              "{outcome.clarifying_question || "Is this complaint about public infrastructure (drainage, roads, power) or a private legal matter (tenancy, threats, rights)?"}"
            </p>
          </div>

          <div className="space-y-3 mb-6">
            <span className="text-xs font-semibold text-gray-600 font-mono">Choose one of the quick responses:</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {quickAnswers.map((ans, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickSelect(ans)}
                  disabled={isLoading}
                  className="p-3 rounded-xl bg-gray-50 hover:bg-emerald-50 hover:border-brand-primary border border-gray-200 text-left text-xs font-medium text-gray-800 transition-all active:scale-[0.98] flex items-center justify-between"
                >
                  <span>{ans}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-gray-400 shrink-0 ml-1" />
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleCustomSubmit} className="pt-4 border-t border-gray-100 flex gap-3">
            <input
              type="text"
              value={clarifyAnswer}
              onChange={(e) => setClarifyAnswer(e.target.value)}
              placeholder="Or type specific clarification (e.g. 'It is about our landlord in Ikeja')..."
              className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-amber-400/50 outline-none"
            />
            <button
              type="submit"
              disabled={isLoading || !clarifyAnswer.trim()}
              className="px-5 py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primaryHover text-white text-xs font-bold font-display flex items-center space-x-2 transition-all disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Send Clarification</span>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
