import React from 'react';
import { 
  CheckCircle2, 
  MapPin, 
  Building2, 
  Download, 
  ListOrdered, 
  Navigation
} from 'lucide-react';

export default function TicketCard({ artifact, onReset }) {
  if (!artifact) return null;

  const ticketId = artifact.tracking_id || artifact.ticket_id || 'GRA-2026-0087';
  const category = artifact.complaint_type || artifact.category || 'Blocked Drainage & Flood Risk';
  const location = artifact.location || 'Alagomeji, Yaba, Lagos Mainland';
  const assignedTo = artifact.assigned_department || 'Lagos State Ministry of the Environment & Water Resources';
  const priority = artifact.priority || 'High';
  const status = artifact.status || 'Accepted & Dispatched';
  const dateStr = artifact.created_at || new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

  return (
    <div className="space-y-6">
      {/* Top Success Banner matching Screen 4 */}
      <div className="bg-emerald-500 text-white rounded-2xl p-5 shadow-sm flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center font-bold text-white shrink-0">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold font-display">Ticket successfully dispatched!</h3>
            <p className="text-xs text-emerald-100 mt-0.5">
              Your infrastructure issue has been logged, geo-tagged, and assigned to municipal responders.
            </p>
          </div>
        </div>
        <span className="hidden sm:inline-flex px-3 py-1 bg-white/20 text-white text-xs font-semibold font-mono rounded-full uppercase tracking-wider">
          Official Artifact
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Structured Ticket Details */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-gray-100">
            <div>
              <span className="text-[11px] font-bold font-mono uppercase tracking-wider text-gray-400">Municipal Ticket</span>
              <h4 className="text-xl font-extrabold text-gray-900 font-mono tracking-tight">{ticketId}</h4>
            </div>
            <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-bold font-display rounded-full border border-emerald-200">
              ● {status}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-gray-50 rounded-xl">
              <span className="text-gray-400 block mb-1">Issue Category</span>
              <span className="font-bold font-display text-gray-900 text-sm">{category}</span>
            </div>
            <div className="p-3 bg-gray-50 rounded-xl">
              <span className="text-gray-400 block mb-1">Assigned Priority</span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold font-mono ${
                priority.toLowerCase() === 'high' 
                  ? 'bg-red-100 text-red-700' 
                  : 'bg-amber-100 text-amber-800'
              }`}>
                {priority} Priority
              </span>
            </div>
            <div className="p-3 bg-gray-50 rounded-xl col-span-2">
              <span className="text-gray-400 block mb-1 flex items-center">
                <MapPin className="w-3.5 h-3.5 text-red-500 mr-1" />
                Location & Landmark
              </span>
              <span className="font-bold font-display text-gray-900 text-sm">{location}</span>
            </div>
            <div className="p-3 bg-gray-50 rounded-xl col-span-2">
              <span className="text-gray-400 block mb-1 flex items-center">
                <Building2 className="w-3.5 h-3.5 text-brand-primary mr-1" />
                Dispatched Agency
              </span>
              <span className="font-bold text-gray-800 text-xs">{assignedTo}</span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3 pt-4 border-t border-gray-100">
            <button 
              onClick={() => alert(`Downloading dispatch receipt for ${ticketId}`)}
              className="flex-1 px-4 py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-bold font-display flex items-center justify-center space-x-2 transition-all"
            >
              <Download className="w-4 h-4" />
              <span>Download Receipt</span>
            </button>
            <button
              onClick={onReset}
              className="px-5 py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primaryHover text-white text-xs font-bold font-display transition-all"
            >
              Create New Intake
            </button>
          </div>
        </div>

        {/* Right: What happens next + Geo Map Card */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
            <h5 className="text-sm font-bold font-display text-gray-900 mb-4 flex items-center">
              <ListOrdered className="w-4 h-4 text-brand-primary mr-2" />
              What happens next?
            </h5>
            <div className="space-y-4 text-xs">
              <div className="flex items-start space-x-3">
                <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center shrink-0 mt-0.5">1</span>
                <div>
                  <p className="font-bold text-gray-900 font-display">Ticket Assigned to Field Unit</p>
                  <p className="text-gray-500 mt-0.5">Your report has been queued for immediate inspection.</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-600 font-bold flex items-center justify-center shrink-0 mt-0.5">2</span>
                <div>
                  <p className="font-bold text-gray-800 font-display">Field Officer Inspection</p>
                  <p className="text-gray-500 mt-0.5">Physical inspection scheduled within 24–48 hours.</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-600 font-bold flex items-center justify-center shrink-0 mt-0.5">3</span>
                <div>
                  <p className="font-bold text-gray-800 font-display">SMS & WhatsApp Updates</p>
                  <p className="text-gray-500 mt-0.5">You will receive status alerts as maintenance begins.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Map Pinpoint Mock Card */}
          <div className="bg-[#EBF3F1] rounded-2xl border border-emerald-200 p-5 relative overflow-hidden flex flex-col justify-between h-40">
            <div className="flex items-center justify-between z-10">
              <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-white/90 text-brand-primary text-xs font-bold font-display shadow-sm">
                <Navigation className="w-3 h-3 mr-1" /> Geo-Tagged Location
              </span>
              <span className="text-[11px] font-mono text-gray-600">6.5000° N, 3.3792° E</span>
            </div>
            
            <div className="flex items-center space-x-2 z-10 bg-white/90 backdrop-blur p-3 rounded-xl shadow-sm">
              <MapPin className="w-5 h-5 text-red-600 shrink-0" />
              <div>
                <p className="font-bold text-xs text-gray-900 font-display">{location}</p>
                <p className="text-[10px] text-gray-500">Lagos Mainland Municipal District</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
