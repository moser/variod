import numpy as np
import matplotlib.pyplot as plt

# controls the length of the pauses between beeps, higher => shorter
PULSE_INTERCEPT = 0.7
# the higher, the steeper the drop/rise of volume at the end/beginning of a beep
PULSE_FACTOR = 2.5


class VarioSynthesizer(object):
    def __init__(self, sample_rate):
        self.frequency_generator = DefaultFrequencyStrategy()
        wave = Wave(sample_rate)
        self.sound_generator = PulsedSoundGen(
            SoundGen(wave), PulseGen(PULSE_INTERCEPT, PULSE_FACTOR, wave))

    def get(self, val, length):
        return self.sound_generator.get(
            self.frequency_generator.freq(val),
            self.frequency_generator.pulse_freq(val),
            length
        )


class DefaultFrequencyStrategy(object):
    a_dur = [
      ('a', 880.0),
      ('gis', 830.609),
      ('fis', 739.989),
      ('e', 659.255),
      ('d', 587.330),
      ('cis', 554.365),
      ('h', 493.883),
      ('a', 440.0),
    ]

    a_moll = [
      ('gis', 415.305),
      ('f', 349.228),
      ('e', 329.628),
      ('d', 293.665),
      #('c', 261.626),
      #('h', 246.942),
      #('a', 220.0),
    ]

    step = 6.0 / len(a_dur)
    _freqs = [
        ((len(a_dur) - idx) * step, tone[1])
        for idx, tone in enumerate(a_dur + a_moll)
    ]

    def freq(self, val):
        for threshold, _freq in self._freqs:
            if val > threshold:
                return _freq
        return self._freqs[-1][1]

    #def freq(self, val):
    #    base = 440
    #    gain = 100
    #    return base + (val ** 0.55 * gain)

    def pulse_freq(self, val):
        if val > 0.0:
            return 2.5 * (
                1.0 - 1.0 / (val ** 2.0 + 1.0)
            ) + 1.8
        else:
            return 1.8


class PulsedSoundGen(object):
    def __init__(self, sound_gen, pulse_gen):
        self.sound_gen = sound_gen
        self.pulse_gen = pulse_gen
        self.last_freq = None

    def get(self, freq, pulse_freq, length):
        """ Creates a numpy array of length containing the samples of a
        pulsed sound. It only changes the sound `freq` when there is a
        a pause (or if the `pulse_freq` is zero). """
        if pulse_freq > 0:
            pulse = self.pulse_gen.get(pulse_freq, length)
            first_zero = np.argmax(pulse == 0)
            if first_zero == 0 and pulse[0] != 0:
                first_zero = length
            if first_zero >= length and self.last_freq is not None:
                # we don't have a pause, maintain old freq
                sound = self.sound_gen.get(self.last_freq, length)
            else:
                # we have a pause, change to new freq on first sample
                # of the pause.
                sound = np.concatenate((
                  self.sound_gen.get(self.last_freq or 0.001, first_zero),
                  self.sound_gen.get(freq, length - first_zero)))
                self.last_freq = freq
            return pulse * sound
        else:
            return self._strict_get(freq, pulse_freq, length)

    # This version changes the sound frequency during a beep, thus causing
    # some sound artifacts.
    def _strict_get(self, freq, pulse_freq, length):
        pulse = self.pulse_gen.get(pulse_freq, length)
        sound = self.sound_gen.get(freq, length)
        return pulse * sound


class PulseGen(object):
    def __init__(self, intercept, factor, wave):
        self.intercept = intercept
        self.factor = factor
        self.wave = wave
        self.phase = 0.0

    def get(self, freq, length):
        if freq > 0:
            vals, self.phase = self.wave.get(freq, length, self.phase)
            return clamp((vals + self.intercept) * self.factor, 0.0, 1.0)
        else:
            self.phase = 0.0
            return np.full((length,), 1.0)


class SoundGen(object):
    def __init__(self, wave):
        self.phase = 0.0
        self.wave = wave

    def get(self, freq, length):
        vals, self.phase = self.wave.get(freq, length, self.phase)
        return vals


class Wave(object):
    def __init__(self, sample_rate):
        self.sample_rate = float(sample_rate)

    def get(self, freq, length, phase):
        per_step = 2 * np.pi / int(self.sample_rate / freq)
        next_phase = np.fmod((length - 1) * per_step + phase, 2 * np.pi)
        return np.sin(np.arange(length) * per_step + phase), next_phase


def clamp(vals, min_val, max_val):
    length = len(vals)
    min_vals = np.full((length,), min_val)
    max_vals = np.full((length,), max_val)
    return np.fmax(np.fmin(vals, max_vals), min_vals)


def main():
    sample_rate = 400
    wave = Wave(sample_rate)
    syn = PulsedSoundGen(SoundGen(wave), PulseGen(PULSE_INTERCEPT, PULSE_FACTOR, wave))
    plt.plot(np.concatenate((syn.get(5, 0.2, sample_rate * 10),
                             syn.get(1, 0.1, sample_rate * 25))))
    plt.savefig("fig.png")

if __name__ == "__main__":
    main()
