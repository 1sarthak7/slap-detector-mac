import math
import time
import os
import random
import subprocess
import numpy as np
import sounddevice as sd


# ==============================
# CONFIGURATION
# ==============================

# --- Detection tuning ---
THRESHOLD = 0.35              # Peak amplitude threshold (0.0-1.0). Lower = more sensitive
SPIKE_RATIO = 3.0             # How much louder a slap must be vs. the ambient noise
COOLDOWN = 1.0                # Seconds between triggers
AMBIENT_DECAY = 0.95          # How fast the ambient level adapts (0-1, higher = slower)

# --- Audio input settings ---
SAMPLE_RATE = 44100           # Hz
BLOCK_SIZE = 1024             # Samples per block (~23ms at 44100Hz)

# --- Sound files ---
AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")


# ==============================
# Collect audio files recursively
# ==============================

def find_audio_files(folder):
    """Recursively find all .mp3 and .wav files in the given folder."""
    audio_files = []
    if not os.path.isdir(folder):
        return audio_files
    for root, _dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith((".wav", ".mp3")):
                audio_files.append(os.path.join(root, f))
    return audio_files


# ==============================
# Microphone-based Slap Detector
# ==============================

class SlapDetector:
    def __init__(self):
        self.last_trigger_time = 0
        self.ambient_level = 0.05   # Initial ambient noise estimate
        self.audio_files = find_audio_files(AUDIO_FOLDER)

        if not self.audio_files:
            print(f"⚠  No audio files found in '{AUDIO_FOLDER}' or its subfolders.")
        else:
            print(f"🎵 Found {len(self.audio_files)} audio files across subfolders.")

    def _play_random_sound(self):
        if not self.audio_files:
            print("⚠  No audio files available.")
            return

        sound_path = random.choice(self.audio_files)
        print(f"💥 SLAP DETECTED! Playing: {os.path.basename(sound_path)}")
        subprocess.Popen(
            ["afplay", sound_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status:
            # Ignore overflow/underflow warnings silently
            pass

        # Calculate peak amplitude of this block
        peak = np.max(np.abs(indata))

        # Update rolling ambient noise estimate (exponential moving average)
        self.ambient_level = AMBIENT_DECAY * self.ambient_level + (1 - AMBIENT_DECAY) * peak

        # Calculate the dynamic threshold: must exceed both
        #   1) The absolute THRESHOLD
        #   2) SPIKE_RATIO times the current ambient level
        dynamic_threshold = max(THRESHOLD, self.ambient_level * SPIKE_RATIO)

        # Show live levels
        bar_len = int(min(peak, 1.0) * 40)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        marker = "  💥" if peak > dynamic_threshold else ""
        print(f"\r🎤 [{bar}] peak={peak:.3f} ambient={self.ambient_level:.3f} thresh={dynamic_threshold:.3f}{marker}", end="", flush=True)

        current_time = time.time()

        if peak > dynamic_threshold and (current_time - self.last_trigger_time) > COOLDOWN:
            self.last_trigger_time = current_time
            print()  # newline before the slap message
            self._play_random_sound()

    def start(self):
        print()
        print("=" * 55)
        print("  🖐  SLAP DETECTOR — Microphone Mode")
        print("=" * 55)
        print()
        print(f"  Threshold:   {THRESHOLD}")
        print(f"  Spike Ratio: {SPIKE_RATIO}x ambient")
        print(f"  Cooldown:    {COOLDOWN}s")
        print(f"  Sample Rate: {SAMPLE_RATE} Hz")
        print()

        # List available input devices
        try:
            device_info = sd.query_devices(kind='input')
            print(f"  🎙  Using input: {device_info['name']}")
        except Exception:
            print("  🎙  Using default input device")

        print()
        print("🎧 Listening for slaps... Slap your laptop lid or clap near the mic!")
        print("   Press Ctrl+C to stop.\n")

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                channels=1,
                dtype='float32',
                callback=self._audio_callback,
            ):
                while True:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n� Stopped cleanly.")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\n💡 Make sure microphone access is granted:")
            print("   System Settings → Privacy & Security → Microphone")
            print("   Enable access for Terminal / your IDE")


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    detector = SlapDetector()
    detector.start()