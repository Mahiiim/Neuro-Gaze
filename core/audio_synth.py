"""
core/audio_synth.py
-------------------
100% Offline Audio Synthesis Engine for Neuro-Gaze.
Uses `sounddevice` and `numpy` to generate zero-latency, overlapping tones
and ambient soundscapes (Rain, Waves, Wind, Fire) via a real-time mixer.
"""

import math
import threading
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from utils.logger import get_logger
log = get_logger(__name__)


class AudioSynth:
    """
    Polyphonic, real-time audio synthesizer.
    Runs a single sounddevice OutputStream callback and mixes active sound generators.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.channels = 2
        self._lock = threading.Lock()
        self._voices = []
        self._ambient_voices = {}  # name -> voice map
        self._stream = None

        if sd is None:
            log.warning("sounddevice module not found. AudioSynth disabled.")
            return

        try:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()
            log.info("AudioSynth started (sample_rate=%d)", self.sample_rate)
        except Exception as e:
            log.error("Failed to start AudioSynth stream: %s", e)
            self._stream = None

    def close(self):
        """Cleanly close the audio stream."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            log.info("AudioSynth stopped.")

    def _audio_callback(self, outdata: np.ndarray, frames: int, time, status):
        if status:
            log.debug("AudioSynth status: %s", status)
        
        # Initialize output buffer to zero
        outdata.fill(0.0)
        
        with self._lock:
            active_voices = []
            # Process one-shot voices
            for voice in self._voices:
                samples = voice.generate(frames, self.sample_rate)
                if samples is not None and len(samples) > 0:
                    # Mix into output
                    # Expand mono to stereo if needed
                    if samples.ndim == 1:
                        samples = np.column_stack((samples, samples))
                    outdata[:len(samples)] += samples
                    active_voices.append(voice)
            self._voices = active_voices
            
            # Process continuous ambient voices
            for name, voice in self._ambient_voices.items():
                samples = voice.generate(frames, self.sample_rate)
                if samples is not None and len(samples) > 0:
                    if samples.ndim == 1:
                        samples = np.column_stack((samples, samples))
                    outdata[:len(samples)] += samples

        # Hard clip to prevent distortion
        np.clip(outdata, -1.0, 1.0, out=outdata)

    def stop_all_voices(self):
        """Immediately stop all active oscillators and ambient sounds."""
        with self._lock:
            self._voices.clear()
            self._ambient_voices.clear()

    def _add_voice(self, voice):
        if self._stream is None:
            return
        with self._lock:
            self._voices.append(voice)

    # -------------------------------------------------------------------------
    # Public API - Tones & Effects
    # -------------------------------------------------------------------------

    def play_tone(self, freq: float, type_: str = 'sine', duration: float = 0.2, volume: float = 0.08, decay: str = 'linear'):
        """Generic tone generator matching the Web Audio API example."""
        self._add_voice(_ToneVoice(freq, type_, duration, volume, decay))
        
    def sweep_tone(self, start_freq: float, end_freq: float, duration: float, volume: float = 0.08):
        """Smoothly glides from start_freq to end_freq over duration."""
        self._add_voice(_SweepToneVoice(start_freq, end_freq, duration, volume))

    def card_flip(self):
        """Triangle wave blip for card hover/flip."""
        self.play_tone(420, 'triangle', 0.12, 0.05)

    def card_match(self):
        """Two-tone sine chime for successful match."""
        self.play_tone(523.25, 'sine', 0.15, 0.08)  # C5
        
        # Second tone delayed
        def _second_tone():
            self.play_tone(659.25, 'sine', 0.3, 0.08)  # E5
        threading.Timer(0.12, _second_tone).start()

    def card_mismatch(self):
        """Low double tone for mismatch."""
        self.play_tone(300, 'sine', 0.15, 0.08)
        def _second_tone():
            self.play_tone(250, 'sine', 0.2, 0.08)
        threading.Timer(0.15, _second_tone).start()

    def bubble_water_pop(self):
        """Water-drop like tone for bubble pop."""
        self._add_voice(_BubbleWaterPopVoice(volume=0.12))

    def bomb_blast(self):
        """Deep synthesized explosion sound."""
        self._add_voice(_BombBlastVoice(volume=0.3))

    def chime_note(self, freq: float):
        """Sine wave chime with exponential decay for the Pentatonic Harp."""
        self._add_voice(_ToneVoice(freq, 'sine', duration=0.8, volume=0.1, decay='exponential'))

    def ui_click(self):
        """Soft click for general UI interactions."""
        self.play_tone(800, 'sine', 0.05, 0.05)

    def sequence_tone(self, freq: float):
        """Tone for Simon Sequence game."""
        self.play_tone(freq, 'sine', 0.4, 0.1)

    def victory_fanfare(self):
        """Rising 4-note victory fanfare."""
        self.play_tone(523.25, 'sine', 0.2, 0.08)  # C5
        threading.Timer(0.14, lambda: self.play_tone(659.25, 'sine', 0.2, 0.08)).start()  # E5
        threading.Timer(0.28, lambda: self.play_tone(783.99, 'sine', 0.2, 0.08)).start()  # G5
        threading.Timer(0.42, lambda: self.play_tone(1046.50, 'sine', 0.6, 0.08)).start() # C6

    def defeat_fanfare(self):
        """Descending 3-note defeat fanfare."""
        self.play_tone(392.00, 'triangle', 0.2, 0.08)  # G4
        threading.Timer(0.3, lambda: self.play_tone(349.23, 'triangle', 0.2, 0.08)).start()  # F4
        threading.Timer(0.6, lambda: self.play_tone(311.13, 'triangle', 0.6, 0.08)).start()  # Eb4

    def core_hit(self):
        """High pitch dual chime for bullseye."""
        self.play_tone(880, 'triangle', 0.2, 0.05)
        threading.Timer(0.1, lambda: self.play_tone(1174.66, 'sine', 0.3, 0.05)).start()

    def ring_hit(self):
        """Medium chime for ring hit."""
        self.play_tone(587.33, 'sine', 0.15, 0.08)

    def miss(self):
        """Low sawtooth buzz for miss."""
        self.play_tone(140, 'sawtooth', 0.2, 0.08, decay='exponential')

    # -------------------------------------------------------------------------
    # Public API - Ambient Mixer
    # -------------------------------------------------------------------------

    def set_ambient(self, track: str, enabled: bool):
        """Toggle a continuous ambient track ('rain', 'waves', 'wind', 'fire')."""
        with self._lock:
            if enabled and track not in self._ambient_voices:
                if track == 'rain':
                    self._ambient_voices[track] = _RainVoice(volume=0.04)
                elif track == 'waves':
                    self._ambient_voices[track] = _WavesVoice(volume=0.08)
                elif track == 'wind':
                    self._ambient_voices[track] = _WindVoice(volume=0.06)
                elif track == 'fire':
                    self._ambient_voices[track] = _FireVoice(volume=0.05)
                log.info("AudioSynth: ambient %s ON", track)
            elif not enabled and track in self._ambient_voices:
                # Add a rapid fade-out voice instead of cutting immediately
                # For simplicity, we just remove it here
                del self._ambient_voices[track]
                log.info("AudioSynth: ambient %s OFF", track)


# -----------------------------------------------------------------------------
# Voice Generators (DSP)
# -----------------------------------------------------------------------------

class _ToneVoice:
    """Basic oscillator with linear or exponential decay envelope."""
    def __init__(self, freq: float, type_: str, duration: float, volume: float, decay: str = 'linear'):
        self.freq = freq
        self.type = type_
        self.duration = duration
        self.volume = volume
        self.decay = decay
        self.phase = 0.0
        self.frame_idx = 0

    def generate(self, frames: int, sr: int) -> np.ndarray:
        total_frames = int(self.duration * sr)
        if self.frame_idx >= total_frames:
            return None  # Finished
            
        rem = total_frames - self.frame_idx
        n = min(frames, rem)
        
        t = (self.frame_idx + np.arange(n)) / sr
        phase = 2 * np.pi * self.freq * t
        
        if self.type == 'sine':
            wave = np.sin(phase)
        elif self.type == 'triangle':
            wave = 2 * np.abs(2 * (t * self.freq - np.floor(t * self.freq + 0.5))) - 1
        elif self.type == 'square':
            wave = np.sign(np.sin(phase))
        else:
            wave = np.sin(phase)

        # Envelope
        progress = (self.frame_idx + np.arange(n)) / total_frames
        if self.decay == 'exponential':
            env = np.exp(-5 * progress)  # Rapid decay
        else:
            env = 1.0 - progress  # Linear decay
            
        # Quick attack to avoid pop
        attack_frames = int(0.01 * sr)
        for i in range(n):
            idx = self.frame_idx + i
            if idx < attack_frames:
                env[i] *= (idx / attack_frames)

        self.frame_idx += n
        return wave * env * self.volume

class _SweepToneVoice:
    """Oscillator that glides from start_freq to end_freq smoothly."""
    def __init__(self, start_freq: float, end_freq: float, duration: float, volume: float):
        self.start_freq = start_freq
        self.end_freq = end_freq
        self.duration = duration
        self.volume = volume
        self.frame_idx = 0

    def generate(self, frames: int, sr: int) -> np.ndarray:
        total_frames = int(self.duration * sr)
        if self.frame_idx >= total_frames:
            return None
            
        rem = total_frames - self.frame_idx
        n = min(frames, rem)
        
        t = (self.frame_idx + np.arange(n)) / sr
        
        # Linear frequency sweep formula:
        # phi(t) = 2 * pi * (f0 * t + (f1 - f0) / (2 * T) * t^2)
        c = (self.end_freq - self.start_freq) / (2 * self.duration)
        phase = 2 * np.pi * (self.start_freq * t + c * (t ** 2))
        
        wave = np.sin(phase)
        
        # Simple envelope to prevent pops
        progress = (self.frame_idx + np.arange(n)) / total_frames
        env = np.ones_like(wave)
        
        attack_frames = int(0.1 * sr)
        for i in range(n):
            idx = self.frame_idx + i
            if idx < attack_frames:
                env[i] = idx / attack_frames
            elif idx > total_frames - attack_frames:
                env[i] = (total_frames - idx) / attack_frames

        self.frame_idx += n
        return wave * env * self.volume


class _BubbleWaterPopVoice:
    """Rising sine wave for a bubble pop effect (450Hz to 900Hz)."""
    def __init__(self, volume: float):
        self.duration = 0.08
        self.volume = volume
        self.frame_idx = 0
        self.start_freq = 450
        self.end_freq = 900

    def generate(self, frames: int, sr: int) -> np.ndarray:
        total_frames = int(self.duration * sr)
        if self.frame_idx >= total_frames:
            return None
            
        rem = total_frames - self.frame_idx
        n = min(frames, rem)
        
        t = (self.frame_idx + np.arange(n)) / sr
        
        # Frequency rises exponentially
        freqs = self.start_freq * (self.end_freq / self.start_freq) ** (t / self.duration)
        phase = 2 * np.pi * np.cumsum(freqs) / sr + (self.frame_idx / sr)
        
        wave = np.sin(phase)
        progress = (self.frame_idx + np.arange(n)) / total_frames
        env = np.exp(-6 * progress)
        
        self.frame_idx += n
        return wave * env * self.volume


class _BombBlastVoice:
    """Filtered white noise explosion effect."""
    def __init__(self, volume: float):
        self.duration = 0.5
        self.volume = volume
        self.frame_idx = 0
        self.last_val = 0.0
        self.start_cutoff = 800
        self.end_cutoff = 30

    def generate(self, frames: int, sr: int) -> np.ndarray:
        total_frames = int(self.duration * sr)
        if self.frame_idx >= total_frames:
            return None
            
        rem = total_frames - self.frame_idx
        n = min(frames, rem)
        
        white = np.random.uniform(-1, 1, n)
        out = np.zeros(n)
        
        t = (self.frame_idx + np.arange(n)) / sr
        
        # Cutoff sweeps exponentially from 800 down to 30
        cutoffs = self.start_cutoff * (self.end_cutoff / self.start_cutoff) ** (t / self.duration)
        
        dt = 1.0 / sr
        alphas = dt / (1.0 / (2 * np.pi * cutoffs) + dt)
        
        val = self.last_val
        for i in range(n):
            val = val + alphas[i] * (white[i] - val)
            out[i] = val
        self.last_val = val
        
        progress = (self.frame_idx + np.arange(n)) / total_frames
        env = np.exp(-6 * progress)
        
        self.frame_idx += n
        return out * env * self.volume * 5.0


# -----------------------------------------------------------------------------
# Ambient Generators (DSP)
# -----------------------------------------------------------------------------

class _RainVoice:
    """Pink-ish noise + random high-passed clicks."""
    def __init__(self, volume: float):
        self.volume = volume
        self.last_val = 0.0

    def generate(self, frames: int, sr: int) -> np.ndarray:
        # Brown/Pink noise approximation using a leaky integrator
        white = np.random.uniform(-1, 1, frames)
        out = np.zeros(frames)
        alpha = 0.02
        val = self.last_val
        for i in range(frames):
            val = val + alpha * (white[i] - val)
            out[i] = val
        self.last_val = val
        
        # Add random "drops"
        drops = np.random.uniform(0, 1, frames) > 0.999
        out += drops * np.random.uniform(-1, 1, frames) * 0.5
        
        return out * self.volume * 3.0  # boost due to integration


class _WavesVoice:
    """Low-pass filtered brown noise with slow LFO for wave rushing."""
    def __init__(self, volume: float):
        self.volume = volume
        self.last_val = 0.0
        self.lfo_phase = 0.0

    def generate(self, frames: int, sr: int) -> np.ndarray:
        white = np.random.uniform(-1, 1, frames)
        out = np.zeros(frames)
        alpha = 0.05
        val = self.last_val
        for i in range(frames):
            val = val + alpha * (white[i] - val)
            out[i] = val
        self.last_val = val

        # LFO for wave surge (0.1 Hz)
        t = self.lfo_phase + np.arange(frames) / sr
        lfo = (np.sin(2 * np.pi * 0.1 * t) + 1.0) / 2.0  # 0 to 1
        self.lfo_phase = t[-1] % (1 / 0.1) if frames > 0 else 0

        # Surge envelope shapes the volume
        surge = 0.2 + lfo * 0.8
        return out * surge * self.volume * 2.0


class _WindVoice:
    """Band-passed noise with LFO controlling cutoff frequency."""
    def __init__(self, volume: float):
        self.volume = volume
        self.last_val = 0.0
        self.lfo_phase = 0.0

    def generate(self, frames: int, sr: int) -> np.ndarray:
        white = np.random.uniform(-1, 1, frames)
        out = np.zeros(frames)
        
        t = self.lfo_phase + np.arange(frames) / sr
        # LFO for wind howling (0.05 Hz)
        lfo = (np.sin(2 * np.pi * 0.05 * t) + 1.0) / 2.0
        self.lfo_phase = t[-1] % (1 / 0.05) if frames > 0 else 0
        
        val = self.last_val
        for i in range(frames):
            alpha = 0.02 + lfo[i] * 0.08  # Cutoff changes over time
            val = val + alpha * (white[i] - val)
            out[i] = val
        self.last_val = val

        return out * self.volume * 3.0


class _FireVoice:
    """Low rumbling noise + sharp high frequency clicks (crackles)."""
    def __init__(self, volume: float):
        self.volume = volume
        self.last_val = 0.0

    def generate(self, frames: int, sr: int) -> np.ndarray:
        # Low rumble
        white = np.random.uniform(-1, 1, frames)
        rumble = np.zeros(frames)
        alpha = 0.01
        val = self.last_val
        for i in range(frames):
            val = val + alpha * (white[i] - val)
            rumble[i] = val
        self.last_val = val

        # Crackles
        crackles = np.random.uniform(0, 1, frames) > 0.995
        crackle_noise = crackles * np.random.uniform(-1, 1, frames) * 0.8
        
        return (rumble * 4.0 + crackle_noise) * self.volume
