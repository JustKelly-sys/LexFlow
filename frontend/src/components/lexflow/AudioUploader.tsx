import { useState, useCallback, useRef } from "react";
import { Mic, Upload, StopCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AudioUploaderProps {
  onUpload: (file: File) => Promise<void>;
  isProcessing: boolean;
  statusMsg?: string;
  pipelineStage?: 'idle' | 'uploading' | 'transcribing' | 'extracting' | 'done';
}

export function AudioUploader({ onUpload, isProcessing, statusMsg, pipelineStage = "idle" }: AudioUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const handleFile = async (file: File) => {
    if (!file.type.startsWith("audio/")) {
      return;
    }
    await onUpload(file);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const file = new File([blob], 'recording.webm', { type: 'audio/webm' });
        stream.getTracks().forEach(t => t.stop());
        await onUpload(file);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Microphone access denied:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className="relative w-full max-w-4xl mx-auto py-20">
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        className={cn(
          "fluted-glass relative flex flex-col items-center justify-center min-h-[400px] transition-all duration-700 overflow-hidden",
          isDragging ? "scale-[1.02] border-accent/40 bg-white/40" : "bg-white/10",
          isProcessing && "pointer-events-none"
        )}
      >
        {isProcessing ? (
          <div className="flex flex-col items-center gap-8 animate-in fade-in zoom-in duration-500">
            <div className="w-full max-w-sm space-y-4">
              {/* Step 1: Upload */}
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  pipelineStage === 'uploading' ? 'bg-amber-400 text-white pipeline-active' :
                  ['transcribing','extracting','done'].includes(pipelineStage) ? 'bg-emerald-500 text-white pipeline-check' :
                  'bg-primary/10 text-muted-foreground'
                }`}>
                  {['transcribing','extracting','done'].includes(pipelineStage) ? '\u2713' : '1'}
                </div>
                <span className={`text-sm font-headline tracking-tight ${
                  pipelineStage === 'uploading' ? 'text-primary font-medium' : 'text-muted-foreground'
                }`}>Audio received</span>
              </div>

              {/* Step 2: Transcribe */}
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  pipelineStage === 'transcribing' ? 'bg-amber-400 text-white pipeline-active' :
                  ['extracting','done'].includes(pipelineStage) ? 'bg-emerald-500 text-white pipeline-check' :
                  'bg-primary/10 text-muted-foreground'
                }`}>
                  {['extracting','done'].includes(pipelineStage) ? '\u2713' : '2'}
                </div>
                <span className={`text-sm font-headline tracking-tight ${
                  pipelineStage === 'transcribing' ? 'text-primary font-medium' : 'text-muted-foreground'
                }`}>Transcribing audio...</span>
              </div>

              {/* Step 3: Extract */}
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  pipelineStage === 'extracting' ? 'bg-amber-400 text-white pipeline-active' :
                  pipelineStage === 'done' ? 'bg-emerald-500 text-white pipeline-check' :
                  'bg-primary/10 text-muted-foreground'
                }`}>
                  {pipelineStage === 'done' ? '\u2713' : '3'}
                </div>
                <span className={`text-sm font-headline tracking-tight ${
                  pipelineStage === 'extracting' ? 'text-primary font-medium' : 'text-muted-foreground'
                }`}>Extracting billing entities</span>
              </div>
            </div>

            <p className="text-muted-foreground text-xs uppercase tracking-[0.2em]">
              {statusMsg || "Processing..."}
            </p>
          </div>
        ) : isRecording ? (
          <div className="flex flex-col items-center gap-8 z-10">
            <div className="w-20 h-20 rounded-full bg-destructive/10 flex items-center justify-center animate-pulse">
              <Mic className="w-10 h-10 text-destructive" strokeWidth={1.5} />
            </div>
            <p className="font-headline text-2xl font-light tracking-tight text-primary">Recording...</p>
            <button
              onClick={stopRecording}
              className="px-12 py-4 bg-destructive text-white font-headline text-lg tracking-tight hover:bg-destructive/90 transition-all flex items-center gap-3"
            >
              <StopCircle size={20} strokeWidth={1.5} />
              Stop Recording
            </button>
          </div>
        ) : (
          <>
            <div className="absolute top-8 left-8">
              <Mic className="w-12 h-12 text-primary/20" strokeWidth={1} />
            </div>
            
            <div className="flex flex-col items-center gap-12 z-10 text-center px-12">
              <div className="space-y-4">
                <h1 className="text-5xl md:text-6xl font-headline font-light leading-tight tracking-tight text-primary">
                  Voice Intelligence <br /> 
                  <span className="italic font-normal">Simplified.</span>
                </h1>
                <p className="text-muted-foreground text-lg font-light max-w-md mx-auto">
                  Drag your case notes or audio recording here to generate instant billing entries.
                </p>
              </div>

              <div className="flex items-center gap-6">
                <button
                  onClick={startRecording}
                  className="px-10 py-4 border border-primary/20 text-primary font-headline text-lg tracking-tight hover:bg-primary/5 transition-all flex items-center gap-3"
                >
                  <Mic size={20} strokeWidth={1.5} />
                  Start Dictation
                </button>



                <label className="group relative cursor-pointer">
                  <input type="file" className="hidden" accept="audio/*" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
                  <div className="px-10 py-4 bg-primary text-white font-headline text-lg tracking-tight hover:bg-primary/90 transition-all flex items-center gap-3">
                    <Upload size={20} strokeWidth={1.5} />
                    Upload Recording
                  </div>
                </label>
              </div>
            </div>

            <div className="absolute bottom-8 right-8">
              <div className="w-1.5 h-1.5 rounded-full bg-accent/30" />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
