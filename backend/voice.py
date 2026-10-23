"""Small local speech segmenter for 16 kHz mono PCM16 microphone frames."""

from array import array
from collections import deque
from math import sqrt


class Segmenter:
    def __init__(self):
        self.pre = deque(maxlen=3)
        self.buffer = bytearray()
        self.active = False
        self.silent_seconds = 0.0

    def feed(self, pcm):
        if not pcm or len(pcm) % 2 or len(pcm) > 16384:
            return False, None
        samples = array("h")
        samples.frombytes(pcm)
        rms = sqrt(sum(sample * sample for sample in samples) / len(samples))
        duration = len(samples) / 16000
        speaking = rms >= 550
        started = False
        if speaking and not self.active:
            self.active = True
            started = True
            self.buffer = bytearray(b"".join(self.pre))
            self.pre.clear()
        if self.active:
            self.buffer.extend(pcm)
            self.silent_seconds = 0 if speaking else self.silent_seconds + duration
            if self.silent_seconds >= 0.7 or len(self.buffer) >= 16_000 * 2 * 15:
                result = bytes(self.buffer)
                self.buffer.clear()
                self.active = False
                self.silent_seconds = 0
                return started, result if len(result) >= 16_000 * 2 * 0.35 else None
        else:
            self.pre.append(pcm)
        return started, None
