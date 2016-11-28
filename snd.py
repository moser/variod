import time
import struct as _struct

import numpy as np
import pyaudio as _pyaudio

import pulse

SAMPLE_RATE = 44100
PA_FORMAT = _pyaudio.paInt16
MAX_SAMPLE = 2 ** 15 - 1  # max of signed short
PACK_FORMAT = "<h"  # little endian signed short, see struct docs

freq = 440.0
sound_gen = pulse.SoundGen(pulse.Wave(SAMPLE_RATE))

def callback(in_data, frame_count, time_info, status):
    samples = sound_gen.get(freq, frame_count)
    return ("".join((_struct.pack(PACK_FORMAT, x) for x in samples * MAX_SAMPLE)),
            _pyaudio.paContinue)

audio = _pyaudio.PyAudio()
stream = audio.open(format=PA_FORMAT,
                              channels=1,
                              rate=SAMPLE_RATE,
                              output=True,
                              frames_per_buffer=int(SAMPLE_RATE * 0.05),
                              stream_callback=callback)
stream.start_stream()

x = [
  ('a', 880.0),
  ('gis', 830.609),
  ('fis', 739.989),
  ('e', 659.255),
  ('d', 587.330),
  ('cis', 554.365),
  ('h', 493.883),
  ('a', 440.0),
]

z = [
  ('a', 440.0),
  ('gis', 415.305),
  ('f', 349.228),
  ('e', 329.628),
  ('d', 293.665),
  ('c', 261.626),
  ('h', 246.942),
  ('a', 220.0),
]

for y in reversed(x):
    print y
    freq = y[1]
    time.sleep(0.8)

for y in x:
    print y
    freq = y[1]
    time.sleep(0.8)

for y in reversed(z):
    print y
    freq = y[1]
    time.sleep(0.8)

for y in z:
    print y
    freq = y[1]
    time.sleep(0.8)

