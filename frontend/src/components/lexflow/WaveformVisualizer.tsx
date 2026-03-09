import { useEffect, useRef } from "react";

interface WaveformVisualizerProps {
  stream?: MediaStream | null;
  isRecording: boolean;
}

export function WaveformVisualizer({ stream, isRecording }: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    if (!stream || !isRecording || !canvasRef.current) return;
    const ctx = canvasRef.current.getContext("2d");
    if (!ctx) return;

    const audioCtx = new AudioContext();
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const barCount = 24;

    const draw = () => {
      const W = canvasRef.current!.width;
      const H = canvasRef.current!.height;
      analyser.getByteFrequencyData(dataArray);
      ctx.clearRect(0, 0, W, H);

      const barWidth = W / (barCount * 2);
      const gap = barWidth;

      for (let i = 0; i < barCount; i++) {
        const v = dataArray[i % bufferLength] / 255;
        const barH = Math.max(4, v * H * 0.8);
        const x = (W / 2) + (i - barCount / 2) * (barWidth + gap);
        const y = (H - barH) / 2;
        ctx.fillStyle = "#1A1A1A";
        ctx.fillRect(x, y, barWidth, barH);
      }
      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => { cancelAnimationFrame(animRef.current); audioCtx.close(); };
  }, [stream, isRecording]);

  if (!isRecording) {
    return (
      <div className="flex items-center justify-center gap-[3px] h-20 py-4">
        {Array.from({ length: 24 }).map((_, i) => (
          <div key={i} className="w-[2px] bg-primary/20 rounded-full"
            style={{ height: `${15 + Math.sin(i * 0.5) * 12}px` }} />
        ))}
      </div>
    );
  }

  return <canvas ref={canvasRef} width={500} height={80} className="w-full h-20" />;
}
