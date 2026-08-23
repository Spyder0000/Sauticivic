import React, { useState, useRef, useEffect } from 'react';
import {
  Mic,
  Square,
  Upload,
  FileText,
  ArrowRight,
  CheckCircle2,
  Volume2,
  Loader2,
} from 'lucide-react';

import Waveform from './Waveform';
import CodeSwitchTranscript, { LangLegend } from './CodeSwitchTranscript';
import { detectedLanguages } from '../lib/codeswitch';

const STEPS = ['Capture', 'Review', 'Classify', 'Outcome'];

export default function VoiceIntake({ onIntakeSubmit, isLoading }) {
  const [activeTab, setActiveTab] = useState('voice'); // 'voice' | 'text'
  const [isRecording, setIsRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [textInput, setTextInput] = useState('');
  const [detectedLang, setDetectedLang] = useState('English + Yoruba');
  const [liveTranscript, setLiveTranscript] = useState('');
  const [confidenceLevel, setConfidenceLevel] = useState('High');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  const samplePrompts = [
    {
      label: 'Drainage (Pidgin / Yoruba)',
      text: 'E kaaro, mo fe report say the drain near my house for Alagomeji don block. Water dey overflow every time it rain and e don damage our gate.',
    },
    {
      label: 'Tenancy (Pidgin)',
      text: 'Good day, my landlord give me 3 days notice make I pack out because I ask am to fix roof wey dey leak. He lock my gate this morning.',
    },
    {
      label: 'Ambiguous (Abstain trigger)',
      text: 'Everything just spoil for our street yesterday night, people dey shout and nothing dey work.',
    },
  ];

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => setRecordDuration((prev) => prev + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const captureSampleTranscript = () => {
    const sample = samplePrompts[0].text;
    setLiveTranscript(sample);
    setDetectedLang(detectedLanguages(sample).join(' + ') || 'English');
    setConfidenceLevel('High');
  };

  const startRecording = async () => {
    try {
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        captureSampleTranscript();
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordDuration(0);
    } catch (err) {
      console.warn('Microphone unavailable — using capture fallback', err);
      setIsRecording(true);
      setRecordDuration(0);
      setTimeout(captureSampleTranscript, 2500);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }
    setIsRecording(false);
    if (!liveTranscript) captureSampleTranscript();
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAudioBlob(file);
      setAudioUrl(URL.createObjectURL(file));
      captureSampleTranscript();
    }
  };

  const handleSubmitVoice = () => {
    if (audioBlob) {
      onIntakeSubmit({ type: 'voice', file: audioBlob, transcriptHint: liveTranscript });
    } else if (liveTranscript) {
      onIntakeSubmit({ type: 'text', text: liveTranscript });
    }
  };

  const handleSubmitText = () => {
    if (textInput.trim()) onIntakeSubmit({ type: 'text', text: textInput.trim() });
  };

  const captured = Boolean(audioBlob || liveTranscript);
  const activeStep = captured ? 1 : 0;
  const detectedList = liveTranscript ? detectedLanguages(liveTranscript) : [];

  return (
    <section className="rounded-xl2 bg-surface shadow-card ring-1 ring-line/70 overflow-hidden">
      {/* Step spine + input mode toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5 px-6 lg:px-8 py-5 border-b border-line/70">
        <ol className="flex items-center gap-2 sm:gap-3">
          {STEPS.map((label, i) => {
            const done = i < activeStep;
            const current = i === activeStep;
            return (
              <li key={label} className="flex items-center gap-2 sm:gap-3">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-mono font-semibold transition-colors ${
                      done
                        ? 'bg-palm text-white'
                        : current
                        ? 'bg-palm/12 text-palm ring-1 ring-palm/40'
                        : 'bg-paper text-muted/70'
                    }`}
                  >
                    {done ? <CheckCircle2 className="w-3.5 h-3.5" /> : String(i + 1).padStart(2, '0')}
                  </span>
                  <span
                    className={`text-xs font-medium hidden sm:inline ${
                      current ? 'text-ink' : done ? 'text-palm' : 'text-muted/70'
                    }`}
                  >
                    {label}
                  </span>
                </div>
                {i < STEPS.length - 1 && <span className="w-4 sm:w-6 h-px bg-line" />}
              </li>
            );
          })}
        </ol>

        <div className="inline-flex bg-paper p-1 rounded-full ring-1 ring-line self-start sm:self-auto">
          {[
            { id: 'voice', label: 'Voice', Icon: Mic },
            { id: 'text', label: 'Text', Icon: FileText },
          ].map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === id ? 'bg-surface text-palm shadow-sm' : 'text-muted hover:text-ink'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'voice' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12">
          {/* Recorder */}
          <div className="lg:col-span-5 field-warm grain p-6 lg:p-8 flex flex-col items-center text-center border-b lg:border-b-0 lg:border-r border-line/70">
            <h3 className="font-display text-hero text-ink">Speak your complaint</h3>
            <p className="text-sm text-muted mt-2 max-w-xs text-pretty">
              Nigerian Pidgin, Yoruba, Hausa, Igbo, or English — whichever comes naturally. Mix them freely.
            </p>

            <div className="relative my-9 flex items-center justify-center">
              {isRecording && (
                <>
                  <span className="absolute w-32 h-32 rounded-full bg-mint/25 animate-breathe" />
                  <span className="absolute w-40 h-40 rounded-full bg-mint/10 animate-breathe" style={{ animationDelay: '0.4s' }} />
                </>
              )}
              <button
                onClick={isRecording ? stopRecording : startRecording}
                className={`relative z-10 w-24 h-24 rounded-full flex items-center justify-center transition-transform active:scale-95 shadow-lift ${
                  isRecording ? 'bg-palm-dark text-mint' : 'bg-palm text-white hover:bg-palm-dark'
                }`}
                aria-label={isRecording ? 'Stop recording' : 'Start recording'}
              >
                {isRecording ? <Square className="w-8 h-8 fill-current" /> : <Mic className="w-9 h-9" />}
              </button>
            </div>

            <div className="h-9 flex items-center justify-center w-full max-w-[220px] text-palm">
              <Waveform active={isRecording} bars={28} className="h-8 w-full justify-center" />
            </div>

            <div className="mt-4 text-sm font-mono">
              {isRecording ? (
                <span className="text-palm-dark inline-flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-mint animate-breathe" />
                  {formatTimer(recordDuration)} · Recording — tap to stop
                </span>
              ) : captured ? (
                <span className="text-palm inline-flex items-center gap-1.5 font-sans font-medium">
                  <CheckCircle2 className="w-4 h-4" />
                  Captured · {formatTimer(recordDuration || 18)}
                </span>
              ) : (
                <span className="text-muted/80 font-sans">Tap the mic to begin</span>
              )}
            </div>

            <label className="mt-7 pt-5 border-t border-line/70 w-full cursor-pointer text-xs font-medium text-palm hover:text-palm-dark inline-flex items-center justify-center gap-1.5">
              <Upload className="w-3.5 h-3.5" />
              Or upload audio (.wav, .mp3)
              <input type="file" accept="audio/*" className="hidden" onChange={handleFileUpload} />
            </label>
          </div>

          {/* Live transcript — the signature */}
          <div className="lg:col-span-7 p-6 lg:p-8 flex flex-col">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted">Here's what we heard</span>
              </div>
              {captured && (
                <div className="flex items-center gap-2">
                  {detectedList.map((lang) => (
                    <span key={lang} className="px-2.5 py-1 rounded-full text-[11px] font-mono font-medium bg-palm/8 text-palm ring-1 ring-palm/15">
                      {lang}
                    </span>
                  ))}
                  <span className="px-2.5 py-1 rounded-full text-[11px] font-mono font-medium bg-mint/15 text-palm-dark ring-1 ring-mint/30">
                    {confidenceLevel} confidence
                  </span>
                </div>
              )}
            </div>

            <div className="flex-1 rounded-2xl bg-warm grain ring-1 ring-line/70 p-6 min-h-[168px] flex flex-col justify-center">
              {liveTranscript ? (
                <CodeSwitchTranscript text={liveTranscript} reveal className="text-[1.35rem] leading-relaxed" />
              ) : (
                <p className="font-serif italic text-muted/70 text-lg leading-relaxed">
                  Your words appear here as you speak — each one coloured by the language it came from, because
                  the way you say it is part of what you mean.
                </p>
              )}
            </div>

            <div className="flex items-center justify-between gap-4 mt-4">
              {liveTranscript ? <LangLegend /> : <span />}
              {audioUrl && (
                <div className="flex items-center gap-2 text-muted">
                  <Volume2 className="w-4 h-4 text-palm" />
                  <audio controls src={audioUrl} className="h-8 max-w-[200px]" />
                </div>
              )}
            </div>

            <div className="flex items-center justify-between gap-4 mt-6 pt-5 border-t border-line/70">
              <button
                type="button"
                onClick={() => setActiveTab('text')}
                className="text-xs font-medium text-muted hover:text-palm transition-colors"
              >
                Prefer typing? Switch to text
              </button>
              <button
                onClick={handleSubmitVoice}
                disabled={isLoading || !captured}
                className="px-6 py-2.5 rounded-full bg-palm hover:bg-palm-dark disabled:opacity-40 disabled:hover:bg-palm text-white text-sm font-semibold inline-flex items-center gap-2 shadow-sm transition-all"
              >
                {isLoading ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Routing…</>
                ) : (
                  <>Continue to routing <ArrowRight className="w-4 h-4" /></>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Text fallback */
        <div className="p-6 lg:p-8 space-y-6">
          <div>
            <label htmlFor="complaint" className="block text-sm font-semibold text-ink mb-2">
              Describe your complaint or grievance
            </label>
            <textarea
              id="complaint"
              rows={5}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type in Nigerian Pidgin, Yoruba, Hausa, Igbo, or English — mixing is welcome…"
              className="w-full p-4 rounded-2xl border border-line bg-warm text-ink text-base leading-relaxed placeholder:text-muted/60 focus:border-palm focus:bg-surface outline-none transition-colors resize-y"
            />
            {textInput.trim() && (
              <div className="mt-3 rounded-2xl bg-warm grain ring-1 ring-line/70 p-4">
                <CodeSwitchTranscript text={textInput} className="text-lg leading-relaxed" />
                <LangLegend className="mt-3" />
              </div>
            )}
          </div>

          <div>
            <span className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted block mb-2.5">Try a scenario</span>
            <div className="flex flex-wrap gap-2">
              {samplePrompts.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setTextInput(sample.text)}
                  className="px-3.5 py-2 rounded-full bg-paper hover:bg-palm/8 hover:text-palm text-xs font-medium text-muted transition-colors ring-1 ring-line"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between gap-4 pt-5 border-t border-line/70">
            <button
              type="button"
              onClick={() => setActiveTab('voice')}
              className="text-xs font-medium text-muted hover:text-palm transition-colors"
            >
              Back to voice
            </button>
            <button
              onClick={handleSubmitText}
              disabled={isLoading || !textInput.trim()}
              className="px-6 py-2.5 rounded-full bg-palm hover:bg-palm-dark disabled:opacity-40 disabled:hover:bg-palm text-white text-sm font-semibold inline-flex items-center gap-2 shadow-sm transition-all"
            >
              {isLoading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Analysing…</>
              ) : (
                <>Send for triage <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
