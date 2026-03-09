import { useState, useRef, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Breadcrumb } from "@/components/lexflow/Breadcrumb";
import { WaveformVisualizer } from "@/components/lexflow/WaveformVisualizer";
import { Mic, Square, Pause, Play, Flag, Upload, Check, Pencil, Lightbulb } from "lucide-react";
import { toast } from "sonner";
import type { Session } from "@supabase/supabase-js";

interface DictationPageProps {
  session: Session;
  onEntryExtracted: (entries: any[], confidence: number | null) => void;
}

export function DictationPage({ session, onEntryExtracted }: DictationPageProps) {
  const navigate = useNavigate();
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [transcript, setTranscript] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<'idle' | 'transcribing' | 'extracting' | 'done'>('idle');
  const [extractedEntry, setExtractedEntry] = useState<any>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Timer
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isRecording, isPaused]);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const ss = (s % 60).toString().padStart(2, '0');
    return `${m}:${ss}`;
  };

  const startRecording = async () => {
    try {
      const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
      setStream(ms);
      const recorder = new MediaRecorder(ms);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        processAudio(new File([blob], 'dictation.webm', { type: 'audio/webm' }));
      };
      recorder.start(1000);
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setIsPaused(false);
      setElapsed(0);
      setExtractedEntry(null);
      setTranscript("");
    } catch {
      toast.error("Microphone access denied. Please allow microphone access.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    stream?.getTracks().forEach(t => t.stop());
    setIsRecording(false);
    setIsPaused(false);
  };

  const togglePause = () => {
    if (!mediaRecorderRef.current) return;
    if (isPaused) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
    } else {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
    }
  };

  const handleUpload = () => fileInputRef.current?.click();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processAudio(file);
    e.target.value = '';
  };

  const processAudio = async (file: File) => {
    setIsProcessing(true);
    setPipelineStage('transcribing');

    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      setPipelineStage('extracting');
      const res = await fetch('/transcribe', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${session.access_token}` },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        const msg = err.detail || 'Processing failed';
        toast.error(msg.includes('429') || msg.includes('rate limit') ? 'High traffic. Please try again in a moment.' : msg);
        setPipelineStage('idle');
      } else {
        const data = await res.json();
        const entries = data.entries || [data];
        const conf = data.confidence;
        const pct = conf != null ? Math.round(conf * 100) : null;
        const confLabel = pct != null ? (pct >= 80 ? `High confidence (${pct}%)` : `Review carefully (${pct}%)`) : '';
        toast.success(`Extraction complete \u2014 ${entries.length} ${entries.length === 1 ? 'entry' : 'entries'} found. ${confLabel}`);

        setExtractedEntry(entries[0] || null);
        setTranscript(data.transcript || entries[0]?.matter_description || '');
        setPipelineStage('done');

        // Pass to parent for review navigation
        onEntryExtracted(entries.map((e: any) => ({ ...e, original_ai_output: { ...e } })), conf ?? null);
      }
    } catch {
      toast.error('Network error. Please check your connection.');
      setPipelineStage('idle');
    } finally {
      setIsProcessing(false);
    }
  };

  const statusSteps = [
    { key: 'transcribing', label: 'Client detection', done: pipelineStage === 'extracting' || pipelineStage === 'done', active: pipelineStage === 'transcribing' },
    { key: 'extracting', label: 'Matter classification', done: pipelineStage === 'done', active: pipelineStage === 'extracting' },
    { key: 'done', label: 'Description generation', done: pipelineStage === 'done', active: false },
  ];

  return (
    <div className="space-y-6 pt-2">
      <Breadcrumb items={[{ label: "Back to Dashboard", to: "/" }, { label: "Active Dictation" }]} />

      <div>
        <h1 className="text-4xl font-serif text-primary">Active Dictation</h1>
        <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground font-semibold mt-2">Voice-to-billing in real time</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Recording panel */}
        <div className="lg:col-span-3 space-y-6">
          <div className="bento-card p-8 space-y-6">
            {/* Recording status */}
            <div className="flex items-center justify-between">
              {isRecording ? (
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500 rec-pulse" />
                  <span className="text-xs font-semibold uppercase tracking-[0.15em] text-red-600">
                    {isPaused ? 'Paused' : 'Recording'}
                  </span>
                </div>
              ) : (
                <span className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Ready</span>
              )}
              <span className="text-3xl font-medium tabular-nums text-primary">
                {formatTime(elapsed)} <span className="text-sm font-light text-muted-foreground">elapsed</span>
              </span>
            </div>

            {/* Waveform */}
            <WaveformVisualizer stream={stream} isRecording={isRecording && !isPaused} />

            {/* Controls */}
            <div className="flex items-center justify-center gap-4">
              {isRecording ? (
                <>
                  <button onClick={togglePause} className="flex items-center gap-2 px-5 py-3 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
                    {isPaused ? <Play size={16} /> : <Pause size={16} />}
                    {isPaused ? 'Resume' : 'Pause'}
                  </button>
                  <button onClick={stopRecording} className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center hover:bg-red-600 transition-colors">
                    <Square size={18} className="text-white" fill="white" />
                  </button>
                  <button className="flex items-center gap-2 px-5 py-3 border border-border text-sm font-medium hover:bg-secondary/50 transition-colors rounded-lg">
                    <Flag size={16} /> Mark
                  </button>
                </>
              ) : (
                <>
                  <button onClick={startRecording} disabled={isProcessing}
                    className="flex items-center gap-3 px-8 py-4 bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-all rounded-lg">
                    <Mic size={18} /> Start Dictation
                  </button>
                  <button onClick={handleUpload} disabled={isProcessing}
                    className="flex items-center gap-3 px-8 py-4 border border-border font-medium text-sm hover:bg-secondary/50 transition-all rounded-lg">
                    <Upload size={18} /> Upload Recording
                  </button>
                </>
              )}
            </div>
            <input ref={fileInputRef} type="file" accept="audio/*" onChange={handleFileSelect} className="hidden" />
          </div>

          {/* Live transcription */}
          <div className="bento-card p-8">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-4 h-4 flex items-center justify-center text-muted-foreground">&#9776;</div>
              <span className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Live Transcription</span>
            </div>
            <div className="min-h-[100px] text-sm leading-relaxed text-primary">
              {transcript ? (
                <p>{transcript}</p>
              ) : (
                <p className="text-muted-foreground/50 italic">
                  {isRecording ? 'Transcription will appear here as you speak...' : 'Start recording or upload a file to see transcription'}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Right: Extraction sidebar */}
        <div className="lg:col-span-2 space-y-6">
          {/* Extraction Status */}
          <div className="bento-sidebar p-6 rounded-lg space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-lg">&#10024;</span>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.15em] text-primary">Extraction Status</div>
                <div className="text-xs text-muted-foreground">
                  {pipelineStage === 'idle' ? 'Waiting for audio...' : 'Extracting billing details...'}
                </div>
              </div>
            </div>
            <div className="space-y-3">
              {statusSteps.map(step => (
                <div key={step.key} className="flex items-center justify-between text-sm">
                  <span className="text-primary">{step.label}</span>
                  {step.done ? (
                    <span className="flex items-center gap-1 text-emerald-600 text-xs font-medium">
                      <Check size={14} /> {step.key === 'done' ? 'Generated' : step.key === 'transcribing' ? 'Detected' : 'Classified'}
                    </span>
                  ) : step.active ? (
                    <span className="flex items-center gap-1 text-muted-foreground text-xs pipeline-active">
                      &#8635; In progress
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground/40">Pending</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Extracted Billing Entry */}
          <div className="bento-sidebar p-6 rounded-lg space-y-5">
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-primary">Extracted Billing Entry</div>

            {extractedEntry ? (
              <>
                <div className="space-y-4">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Timestamp</div>
                    <div className="text-sm text-primary">{new Date().toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })} \u2014 {new Date().toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Client Entity</div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-primary">{extractedEntry.client_name}</span>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600">Matched</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Matter Description</div>
                    <div className="text-sm text-muted-foreground italic leading-relaxed">{extractedEntry.matter_description}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Duration</div>
                      <div className="text-2xl font-medium tabular-nums text-primary">{extractedEntry.duration}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-semibold mb-1">Est. Amount</div>
                      <div className="text-2xl font-medium tabular-nums text-primary">{extractedEntry.billable_amount}</div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <button onClick={() => navigate('/review')}
                    className="flex-1 flex items-center justify-center gap-2 py-4 bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-all rounded-lg">
                    <Check size={16} /> Confirm Entry
                  </button>
                  <button className="p-4 border border-border hover:bg-secondary/50 transition-colors rounded-lg">
                    <Pencil size={16} className="text-muted-foreground" />
                  </button>
                </div>
              </>
            ) : (
              <div className="py-8 text-center text-sm text-muted-foreground/50 italic">
                Billing details will appear here once audio is processed
              </div>
            )}
          </div>

          {/* Dictation Tip */}
          <div className="bento-sidebar p-5 rounded-lg">
            <div className="flex items-start gap-3">
              <Lightbulb size={16} className="text-amber-500 mt-0.5 shrink-0" />
              <div>
                <div className="text-sm font-medium text-primary">Dictation Tip</div>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  Mention the client name and matter type clearly at the start. The system will auto-detect and populate billing fields more accurately.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
