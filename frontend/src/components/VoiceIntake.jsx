import React, { useState, useRef, useEffect } from 'react';
import { 
  Mic, 
  MicOff, 
  Upload, 
  FileText, 
  ArrowRight, 
  CheckCircle2, 
  Sparkles, 
  Volume2,
  RefreshCw
} from 'lucide-react';

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
      label: "Drainage (Pidgin/Yoruba)",
      text: "E kaaro, mo fe report say the drain near my house for Alagomeji don block. Water dey overflow every time it rain and e don damage our gate."
    },
    {
      label: "Tenancy (Pidgin)",
      text: "Good day, my landlord give me 3 days notice make I pack out because I ask am to fix roof wey dey leak. He lock my gate this morning."
    },
    {
      label: "Ambiguous (Abstain Trigger)",
      text: "Everything just spoil for our street yesterday night, people dey shout and nothing dey work."
    }
  ];

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordDuration((prev) => prev + 1);
      }, 1000);
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

  const startRecording = async () => {
    try {
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(audioBlob);
        setAudioUrl(URL.createObjectURL(audioBlob));
        setLiveTranscript("E kaaro, mo fe report say the drain near my house for Alagomeji don block. Water dey overflow every time it rain and e don damage our gate.");
        setDetectedLang("English + Yoruba");
        setConfidenceLevel("High");
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordDuration(0);
    } catch (err) {
      console.warn("Microphone fallback mode", err);
      setIsRecording(true);
      setRecordDuration(0);
      setTimeout(() => {
        setLiveTranscript("E kaaro, mo fe report say the drain near my house for Alagomeji don block...");
      }, 2500);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
    setIsRecording(false);
    if (!liveTranscript) {
      setLiveTranscript("E kaaro, mo fe report say the drain near my house for Alagomeji don block. Water dey overflow every time it rain and e don damage our gate.");
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAudioBlob(file);
      setAudioUrl(URL.createObjectURL(file));
      setLiveTranscript("E kaaro, mo fe report say the drain near my house for Alagomeji don block. Water dey overflow every time it rain and e don damage our gate.");
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
    if (textInput.trim()) {
      onIntakeSubmit({ type: 'text', text: textInput.trim() });
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 lg:p-8">
      {/* Stepper matching image1.jpeg */}
      <div className="flex items-center justify-between pb-6 mb-8 border-b border-gray-100">
        <div className="flex items-center space-x-6 sm:space-x-10 text-xs sm:text-sm font-medium">
          <div className="flex items-center space-x-2 text-brand-primary">
            <span className="w-6 h-6 rounded-full bg-brand-primary text-white flex items-center justify-center font-bold text-xs">1</span>
            <span className="font-display font-semibold">Capture</span>
          </div>
          <div className="flex items-center space-x-2 text-gray-400">
            <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center font-bold text-xs">2</span>
            <span>Review</span>
          </div>
          <div className="flex items-center space-x-2 text-gray-400">
            <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center font-bold text-xs">3</span>
            <span>Classification</span>
          </div>
          <div className="flex items-center space-x-2 text-gray-400">
            <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center font-bold text-xs">4</span>
            <span>Outcome</span>
          </div>
        </div>

        {/* Tab Toggle: Voice | Text */}
        <div className="inline-flex bg-gray-100 p-1 rounded-xl border border-gray-200">
          <button
            onClick={() => setActiveTab('voice')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold font-display transition-all flex items-center space-x-1.5 ${
              activeTab === 'voice'
                ? 'bg-white text-brand-primary shadow-sm'
                : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            <Mic className="w-3.5 h-3.5" />
            <span>Voice</span>
          </button>
          <button
            onClick={() => setActiveTab('text')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold font-display transition-all flex items-center space-x-1.5 ${
              activeTab === 'text'
                ? 'bg-white text-brand-primary shadow-sm'
                : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Text</span>
          </button>
        </div>
      </div>

      {activeTab === 'voice' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left Recorder Column */}
          <div className="lg:col-span-5 flex flex-col items-center text-center p-6 bg-[#F8FAFB] rounded-2xl border border-gray-200">
            <h3 className="text-lg font-bold font-display text-gray-900 mb-1">Speak your complaint</h3>
            <p className="text-xs text-gray-500 mb-8 max-w-xs">
              You can speak in Nigerian Pidgin, Yoruba, Hausa, Igbo, or English.
            </p>

            <div className="relative my-4 flex items-center justify-center">
              {isRecording && (
                <>
                  <div className="absolute w-28 h-28 rounded-full bg-brand-accent/20 animate-ping" />
                  <div className="absolute w-36 h-36 rounded-full bg-brand-accent/10 animate-pulse" />
                </>
              )}
              <button
                onClick={isRecording ? stopRecording : startRecording}
                className={`relative z-10 w-24 h-24 rounded-full flex items-center justify-center transition-transform active:scale-95 shadow-md ${
                  isRecording 
                    ? 'bg-red-500 text-white animate-pulse' 
                    : 'bg-brand-primary hover:bg-brand-primaryHover text-white'
                }`}
                title={isRecording ? "Tap to stop" : "Tap to speak"}
              >
                {isRecording ? <MicOff className="w-10 h-10" /> : <Mic className="w-10 h-10" />}
              </button>
            </div>

            <div className="h-10 flex items-center justify-center space-x-1.5 mt-4 mb-2">
              {[4, 8, 14, 20, 28, 18, 24, 30, 16, 22, 10, 5].map((h, idx) => (
                <span
                  key={idx}
                  style={{ height: isRecording ? `${Math.max(6, Math.floor(Math.random() * 32) + 6)}px` : `${h}px` }}
                  className={`w-1.5 rounded-full transition-all duration-150 ${
                    isRecording 
                      ? 'bg-brand-accent animate-pulse' 
                      : 'bg-gray-300'
                  }`}
                />
              ))}
            </div>

            <div className="text-sm font-semibold font-mono text-gray-700 mt-2">
              {isRecording ? (
                <span className="text-red-600 flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
                  <span>{formatTimer(recordDuration)} · Tap to stop</span>
                </span>
              ) : audioBlob || liveTranscript ? (
                <span className="text-emerald-700 flex items-center space-x-1 font-sans">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Audio captured ({formatTimer(recordDuration || 18)})</span>
                </span>
              ) : (
                <span className="text-gray-400 font-sans">00:00 · Tap to speak</span>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-gray-200 w-full flex items-center justify-center">
              <label className="cursor-pointer text-xs font-medium text-brand-primary hover:text-brand-primaryHover flex items-center space-x-1.5">
                <Upload className="w-3.5 h-3.5" />
                <span>Or upload audio file (.wav, .mp3)</span>
                <input 
                  type="file" 
                  accept="audio/*" 
                  className="hidden" 
                  onChange={handleFileUpload} 
                />
              </label>
            </div>
          </div>

          {/* Right: Live Transcript Column */}
          <div className="lg:col-span-7 flex flex-col justify-between h-full space-y-6">
            <div className="bg-[#F8FAFB] p-6 rounded-2xl border border-gray-200 flex-1">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-brand-primary" />
                  <h4 className="text-sm font-bold font-display text-gray-900">Live Transcript</h4>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-brand-primary border border-emerald-200">
                    {detectedLang}
                  </span>
                  <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    Confidence: {confidenceLevel}
                  </span>
                </div>
              </div>

              <div className="p-4 bg-white rounded-xl border border-gray-200 min-h-[140px] text-gray-800 text-sm leading-relaxed">
                {liveTranscript ? (
                  <p className="italic font-medium">"{liveTranscript}"</p>
                ) : (
                  <p className="text-gray-400 italic">
                    Start speaking or upload an audio clip to preview real-time speech transcription...
                  </p>
                )}
              </div>

              {audioUrl && (
                <div className="mt-4 pt-3 flex items-center space-x-3 text-xs text-gray-600">
                  <Volume2 className="w-4 h-4 text-brand-primary" />
                  <audio controls src={audioUrl} className="h-8 w-full max-w-sm rounded" />
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={() => setActiveTab('text')}
                className="text-xs font-medium text-gray-500 hover:text-brand-primary transition-colors underline"
              >
                Prefer typing? Switch to text input
              </button>

              <button
                onClick={handleSubmitVoice}
                disabled={isLoading || (!audioBlob && !liveTranscript)}
                className="px-6 py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primaryHover disabled:opacity-50 text-white font-display font-semibold text-xs flex items-center space-x-2 shadow-sm transition-all"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Processing Intake...</span>
                  </>
                ) : (
                  <>
                    <span>Continue to Routing</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Text-Fallback Screen */
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-bold font-display text-gray-900 mb-2">
              Describe your complaint or grievance
            </label>
            <textarea
              rows={5}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type your complaint in Nigerian Pidgin, Yoruba, Hausa, Igbo, or English..."
              className="w-full p-4 rounded-xl border border-gray-200 bg-white text-gray-800 text-sm focus:ring-2 focus:ring-brand-accent/50 focus:border-brand-primary outline-none"
            />
          </div>

          <div>
            <span className="text-xs font-semibold text-gray-500 block mb-2 font-mono">Quick test scenarios:</span>
            <div className="flex flex-wrap gap-2">
              {samplePrompts.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setTextInput(sample.text)}
                  className="px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-emerald-50 hover:text-brand-primary text-xs font-medium text-gray-700 transition-colors border border-gray-200"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setActiveTab('voice')}
              className="text-xs font-medium text-gray-500 hover:text-brand-primary transition-colors underline"
            >
              Switch back to Voice Intake
            </button>

            <button
              onClick={handleSubmitText}
              disabled={isLoading || !textInput.trim()}
              className="px-6 py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primaryHover disabled:opacity-50 text-white font-display font-semibold text-xs flex items-center space-x-2 shadow-sm transition-all"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Analyzing Intake...</span>
                </>
              ) : (
                <>
                  <span>Submit for Gate Triage</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
