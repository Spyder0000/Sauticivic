import React from 'react';
import { 
  Scale, 
  User, 
  FileText, 
  Download, 
  Building
} from 'lucide-react';

export default function LegalBriefCard({ artifact, onReset }) {
  if (!artifact) return null;

  const briefId = artifact.brief_id || artifact.tracking_id || 'LEG-2026-0051';
  const grievanceType = artifact.grievance_type || artifact.category || 'Tenancy Dispute & Unlawful Notice';
  const respondent = artifact.respondent_party || artifact.party || 'Landlord / Property Manager';
  const assignedNetwork = artifact.assigned_network || 'Legal Aid Council of Nigeria & Pro Bono Clearinghouse';
  const urgency = artifact.urgency || 'High';
  const facts = artifact.statement_of_facts || artifact.description || 'Citizen reported sudden 3-day eviction notice following maintenance dispute over roof leak and gate lock.';
  const dateStr = artifact.created_at || new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

  return (
    <div className="space-y-6">
      {/* Top Banner for Legal Brief */}
      <div className="bg-indigo-600 text-white rounded-2xl p-5 shadow-sm flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center font-bold text-white shrink-0">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold font-display">Legal Aid Intake Brief Generated!</h3>
            <p className="text-xs text-indigo-100 mt-0.5">
              Structured statement of facts formatted for paralegal review and pro bono attorney dispatch.
            </p>
          </div>
        </div>
        <span className="hidden sm:inline-flex px-3 py-1 bg-white/20 text-white text-xs font-semibold font-mono rounded-full uppercase tracking-wider">
          Legal Aid Brief
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Formal Brief Artifact */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-gray-100">
            <div>
              <span className="text-[11px] font-bold font-mono uppercase tracking-wider text-gray-400">Intake Reference</span>
              <h4 className="text-xl font-extrabold text-gray-900 font-mono">{briefId}</h4>
            </div>
            <span className="px-3 py-1 bg-indigo-100 text-indigo-800 text-xs font-bold font-display rounded-full border border-indigo-200">
              ● Ready for Counsel
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-gray-50 rounded-xl">
              <span className="text-gray-400 block mb-1">Grievance Nature</span>
              <span className="font-bold font-display text-gray-900 text-sm">{grievanceType}</span>
            </div>
            <div className="p-3 bg-gray-50 rounded-xl">
              <span className="text-gray-400 block mb-1">Triage Urgency</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold font-mono bg-amber-100 text-amber-800">
                {urgency} Priority
              </span>
            </div>
            <div className="p-3 bg-gray-50 rounded-xl col-span-2">
              <span className="text-gray-400 block mb-1 flex items-center">
                <User className="w-3.5 h-3.5 text-indigo-600 mr-1" />
                Adverse / Respondent Party
              </span>
              <span className="font-bold font-display text-gray-900 text-sm">{respondent}</span>
            </div>
          </div>

          {/* Statement of Facts */}
          <div className="p-4 bg-[#F8FAFB] rounded-xl border border-gray-200">
            <h5 className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-2 flex items-center font-mono">
              <FileText className="w-3.5 h-3.5 text-indigo-600 mr-1.5" />
              Transcribed Statement of Facts
            </h5>
            <p className="text-xs text-gray-800 leading-relaxed italic">
              "{facts}"
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t border-gray-100">
            <button 
              onClick={() => alert(`Exporting signed PDF legal brief for ${briefId}`)}
              className="flex-1 px-4 py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-bold font-display flex items-center justify-center space-x-2 transition-all"
            >
              <Download className="w-4 h-4" />
              <span>Export Signed PDF Brief</span>
            </button>
            <button
              onClick={onReset}
              className="px-5 py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primaryHover text-white text-xs font-bold font-display transition-all"
            >
              Start New Intake
            </button>
          </div>
        </div>

        {/* Right: Legal Aid Network Routing Info */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
            <h5 className="text-sm font-bold font-display text-gray-900 mb-3 flex items-center">
              <Building className="w-4 h-4 text-indigo-600 mr-2" />
              Legal Aid Network
            </h5>
            <p className="text-xs font-semibold text-gray-800 mb-2">{assignedNetwork}</p>
            <p className="text-xs text-gray-500 leading-relaxed mb-4">
              Your matter has been indexed with statutory legal aid providers. A duty counsel will review jurisdiction and rights protection remedies.
            </p>
            <div className="p-3 bg-indigo-50 rounded-xl border border-indigo-100 text-xs text-indigo-900">
              <span className="font-bold">Next Step:</span> Initial case merit review within 24 hours. Confidentiality protected under Legal Aid charter.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
