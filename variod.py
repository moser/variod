import math as _m
import struct as _struct
import socket as _socket
import time as _time

import numpy as np
import pyaudio as _pyaudio

import pulse

# TODO logging

SIM = True

# controls the length of the pauses between beeps, higher => shorter
PULSE_INTERCEPT = 0.3
# the higher, the steeper the drop/rise of volume at the end/beginning of a beep
PULSE_FACTOR = 2.5

# PCM constants
SAMPLE_RATE = 44100
MAX_VOL = 100.0

# Encodings: Those need to match
PA_FORMAT = _pyaudio.paInt16
MAX_SAMPLE = 2 ** 15 - 1  # max of signed short
PACK_FORMAT = "<h"  # little endian signed short, see struct docs


def main():
    vario_system = VarioSystem()
    i = 0
    while True:
        _time.sleep(0.01)
        vario_system.vario.audio_value = _m.sin(float(i) / 550.0) * 5.5
        print vario_system.vario.audio_value
        i += 1

class VarioSystem(object):
    def __init__(self):
        self.vario = Vario()
        self.audio = _pyaudio.PyAudio()
        self.stream = self.audio.open(format=PA_FORMAT,
                                      channels=1,
                                      rate=SAMPLE_RATE,
                                      output=True,
                                      frames_per_buffer=int(SAMPLE_RATE * 0.2),
                                      stream_callback=self.vario.callback)
        self.stream.start_stream()


    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()


# TODO implement STF logic


class Vario(object):
    def __init__(self):
        self.audio_value = 0.0
        self.volume = 95.0
        self._audio_mode = "vario"
        self.synth = Synthesizer()

    def callback(self, in_data, frame_count, time_info, status):
        samples = self.synth.synthesize(self.audio_value, frame_count,
                                        self.volume)
        return ("".join((_struct.pack(PACK_FORMAT, x) for x in samples)),
                _pyaudio.paContinue)


class Synthesizer(object):  # TODO test
    def __init__(self):
        self.x = pulse.VarioSynthesizer(SAMPLE_RATE)

    def synthesize(self, val, n_frames, volume):
        scale = volume / MAX_VOL * MAX_SAMPLE
        return (int(x) for x in self.x.get(val, n_frames) * scale)


class adict(dict):
    """ small and hacky attrdict implementation """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


if __name__ == "__main__":
    main()
