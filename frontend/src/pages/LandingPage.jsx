import React from 'react';
import { ArrowRight, Mic, ShieldCheck, Languages, AlertTriangle } from 'lucide-react';
import Brandmark from '../components/Brandmark';
import Waveform from '../components/Waveform';
import { benchmarkResults } from '../data/benchmark';

export default function LandingPage({ onStart }) {
  return <main className="min-h-screen bg-paper text-ink">
    <header className="max-w-7xl mx-auto px-5 sm:px-8 py-5 flex items-center justify-between">
      <div className="flex items-center gap-3"><span className="w-10 h-10 rounded-xl2 bg-ink text-mint grid place-items-center"><Brandmark /></span><span><b className="font-display text-lg">SautiCivic Bridge</b><small className="block text-[10px] font-mono tracking-wider text-muted">CIVIC INTAKE · NIGERIA</small></span></div>
      <button onClick={onStart} className="rounded-full bg-palm px-4 py-2 text-sm font-semibold text-white hover:bg-palm-dark">Report a problem</button>
    </header>
    <section className="max-w-7xl mx-auto px-5 sm:px-8 pt-10 pb-16 lg:pt-20 lg:pb-24 grid lg:grid-cols-[1.1fr_.9fr] gap-10 items-center">
      <div className="max-w-3xl animate-settle">
        <p className="font-mono text-[11px] uppercase tracking-[.16em] text-palm">Voice-first civic grievance & legal-aid intake</p>
        <h1 className="font-display text-thesis mt-5">Speak in the words that come naturally.</h1>
        <p className="mt-6 text-lg leading-relaxed text-muted max-w-2xl">Report road, water, power, tenancy, workplace, or rights concerns in Nigerian Pidgin and English. Your complaint is reviewed with you before any draft is prepared.</p>
        <div className="mt-8 flex flex-wrap gap-3"><button onClick={onStart} className="rounded-full bg-palm px-6 py-3 text-white font-semibold inline-flex gap-2 items-center shadow-lift hover:bg-palm-dark">Report a problem <ArrowRight size={18}/></button><span className="inline-flex items-center gap-2 px-4 py-3 text-sm text-muted"><ShieldCheck className="text-palm" size={18}/> We clarify rather than guess.</span></div>
      </div>
      <div className="rounded-xl2 bg-ink text-white overflow-hidden p-7 sm:p-9 shadow-lift relative">
        <Waveform active bars={38} className="absolute inset-x-7 top-10 h-16 text-mint opacity-50" />
        <div className="relative pt-24"><p className="font-display text-hero">Your voice stays in the case.</p><p className="text-sm leading-relaxed text-paper/70 mt-3">Play back original audio, compare the original and normalized transcript, correct it, then confirm consent before processing.</p><div className="mt-7 grid grid-cols-3 gap-3 text-[11px]"><span className="border-t border-white/15 pt-3"><Mic className="mb-2 text-mint" size={18}/>Record or upload</span><span className="border-t border-white/15 pt-3"><Languages className="mb-2 text-mint" size={18}/>Pidgin / English</span><span className="border-t border-white/15 pt-3"><AlertTriangle className="mb-2 text-mint" size={18}/>Emergency recommendation</span></div></div>
      </div>
    </section>
    <section className="border-y border-line bg-surface"><div className="max-w-7xl mx-auto px-5 sm:px-8 py-10"><p className="font-mono text-[11px] uppercase tracking-[.16em] text-muted">Verified benchmark results · not production guarantees</p><div className="mt-5 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">{benchmarkResults.map(item => <div key={item.label} className="rounded-2xl bg-paper p-4 ring-1 ring-line"><b className="font-display text-2xl text-palm">{item.value}</b><p className="mt-2 text-xs font-semibold">{item.label}</p><p className="text-[11px] text-muted">{item.detail}</p></div>)}</div></div></section>
  </main>;
}
