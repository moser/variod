""" Experiments with numpy """

import numpy as np
import matplotlib.pyplot as plt

SAMPLE_RATE = 44100

def pulsed(freq):
    length = int(np.pi * 2 * SAMPLE_RATE / freq)
    return np.fmax(
      np.fmin(np.full((length,), 1.0),
              (np.sin(np.arange(length) / float(SAMPLE_RATE) * freq) + 0.8) * 3),
      np.full((length,), 0.0))

def sound(freq):
    length = int(np.pi * 2 * SAMPLE_RATE / freq)
    return np.sin(np.arange(length) / float(SAMPLE_RATE) * freq)

def repeat(seq, n_frames, offset=0):
    seqlen = len(seq)
    offset = offset % seqlen
    middle = (n_frames - seqlen + offset) / seqlen
    rest = (n_frames - seqlen + offset) % seqlen
    print seqlen, offset, middle, rest
    if middle >= 0:
        x = np.concatenate((seq[offset:], np.tile(seq, middle), seq[:rest]))
    else:
        x = seq[offset:offset+rest]
    print len(x), n_frames, offset
    return x

def samples(freq, n_frames, offset=0):
    return repeat(sound(freq), n_frames, offset)\
            * repeat(pulsed(max(1, 30)), n_frames, offset)

plt.plot(np.concatenate((samples(90, 8500), samples(490, 8000, 8500))))

plt.savefig("fig.png")
