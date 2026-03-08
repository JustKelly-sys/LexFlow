import { useState, useCallback, useRef } from "react";
import { Mic, Upload, Loader2, StopCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AudioUploaderProps {
  onUpload: (file: File) => Promise<void>;
  isProcessing: boolean;
  statusMsg?: string;
}

export function AudioUploader({ onUpload, isProcessing, statusMsg }: AudioUploaderProps) {
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
          <div className="flex flex-col items-center gap-6 animate-in fade-in zoom-in duration-500">
            <Loader2 className="w-16 h-16 text-accent animate-spin" strokeWidth={1} />
            <p className="font-headline text-2xl font-light tracking-tight text-primary">
              {statusMsg || "Transcribing with Gemini AI..."}
            </p>
            <p className="text-muted-foreground text-sm uppercase tracking-widest">Analyzing Client Context & Matter Details</p>
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

                <span className="text-muted-foreground/40 text-sm font-light">or</span>

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
