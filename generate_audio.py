import wave
import math
import struct

# Audio parameters
sample_rate = 44100
duration = 1.0  # seconds
frequency = 440.0  # Hz

# Generate simple sine wave
data = []
for i in range(int(sample_rate * duration)):
    t = float(i) / sample_rate
    value = int(32767.0 * math.sin(2.0 * math.pi * frequency * t))
    data.append(value)

# Write to WAV file
with wave.open("test_audio.wav", "w") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)
    for value in data:
        wav_file.writeframes(struct.pack('h', value))

print("Created test_audio.wav")
