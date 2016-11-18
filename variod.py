import math as _m
#import struct as _struct
import socket as _socket
import time as _time

import numpy as np
import pyaudio as _pyaudio

# TODO logging

SIM = True

# vario defaults
DEADBAND_LOW = -0.0
DEADBAND_HIGH = 0.0  # DEADBAND: Vario remains silent for DEADBAND_LOW < TE value < DEADBAND_HIGH
PULSE_LENGTH = 11288  # LENGTH of PULSE (PAUSE) for positive TE values, in samples
PULSE_LENGTH_GAIN = 1  # PULSES get shorter with higher TE values
PULSE_DUTY = 2.6  # Pulse duty cycle 2*PI == 100%
PULSE_RISE = 0.3  # Timing for rising edge of pulse (Fade-In)
PULSE_FALL = 0.3  # Timing for falling edge of pulse (Fade-Out)
BASE_FREQ_POS = 440  # BASE frequency for positive TE values in Hz
BASE_FREQ_NEG = 440  # BASE frequency for negative TE values in Hz
FREQ_GAIN_POS = 100
FREQ_GAIN_NEG = -30

STF_DEADBAND_LOW = -2.5  
STF_DEADBAND_HIGH = 2.5  # DEADBAND: Vario remains silent for DEADBAND_LOW < STF value < DEADBAND_HIGH 
STF_PULSE_LENGTH = 12288 # LENGTH of PULSE (PAUSE) for positive values, in samples
STF_PULSE_LENGTH_GAIN = 0.2 # PULSES get shorter with higher values
STF_PULSE_DUTY = 2.6 # Pulse duty cycle 2*PI == 100%
STF_PULSE_RISE = 0.1 # Timing for rising edge of pulse (Fade-In)
STF_PULSE_FALL = 0.1 # Timing for falling edge of pulse (Fade-Out)
STF_BASE_FREQ_POS = 440   # BASE frequency for positive STF values in Hz
STF_BASE_FREQ_NEG = 440  # BASE frequency for negative STF values in Hz
STF_FREQ_GAIN_POS = 30
STF_FREQ_GAIN_NEG = 0.1

# PCM constants
SAMPLE_RATE = 44100
MAX_VOL = 100.0

# Encodings: Those need to match
PA_FORMAT = _pyaudio.paUInt8
MAX_SAMPLE = 2 ** 7 - 1  # max of signed short
#PACK_FORMAT = "<B"  # little endian signed short, see struct docs


def get_config():
    # TODO accept config from a file
    config = adict(
        vario=adict(
            deadband_low=DEADBAND_LOW,
            deadband_high=DEADBAND_HIGH,
            pulse_length=PULSE_LENGTH,
            pulse_length_gain=PULSE_LENGTH_GAIN,
            pulse_duty=PULSE_DUTY,
            pulse_rise=PULSE_RISE,
            pulse_fall=PULSE_FALL,
            base_freq_pos=BASE_FREQ_POS,
            base_freq_neg=BASE_FREQ_NEG,
            freq_gain_pos=FREQ_GAIN_POS,
            freq_gain_neg=FREQ_GAIN_NEG,
        ),
        stf=adict(
            deadband_low=STF_DEADBAND_LOW,
            deadband_high=STF_DEADBAND_HIGH,
            pulse_length=STF_PULSE_LENGTH,
            pulse_length_gain=STF_PULSE_LENGTH_GAIN,
            pulse_duty=STF_PULSE_DUTY,
            pulse_rise=STF_PULSE_RISE,
            pulse_fall=STF_PULSE_FALL,
            base_freq_pos=STF_BASE_FREQ_POS,
            base_freq_neg=STF_BASE_FREQ_NEG,
            freq_gain_pos=STF_FREQ_GAIN_POS,
            freq_gain_neg=STF_FREQ_GAIN_NEG,
        ),
    )
    return config

def main():
    config = get_config()
    vario_system = VarioSystem(config)
    i = 0
    while True:
        _time.sleep(1)
        vario_system.vario.audio_value = _m.sin(float(i) / 8.0) * 4.5
        print vario_system.vario.audio_value
        i += 1

class VarioSystem(object):
    def __init__(self, config):
        self.vario = Vario(config)
        self.audio = _pyaudio.PyAudio()
        self.stream = self.audio.open(format=PA_FORMAT,
                                      channels=1,
                                      rate=SAMPLE_RATE,
                                      output=True,
                                      frames_per_buffer=int(SAMPLE_RATE * 0.1),
                                      stream_callback=self.vario.callback)
        self.stream.start_stream()


    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()


# TODO implement STF logic


class Vario(object):
    def __init__(self, config):
        self.config = config
        self.audio_value = 0.0
        self.volume = 50.0
        self._audio_mode = "vario"
        self.synth = Synthesizer(config[self._audio_mode])

    def set_audio_mode(self, val):
        self._audio_mode = val
        self.synth.config = self.config[val]

    def callback(self, in_data, frame_count, time_info, status):
        samples = self.synth.synthesize(self.audio_value, frame_count,
                                        self.volume)
        #return ("".join((_struct.pack(PACK_FORMAT, x) for x in samples)),
        #        _pyaudio.paContinue)
        return ("".join((chr(x) for x in samples)), _pyaudio.paContinue)


class Synthesizer(object):  # TODO test
    def __init__(self, config):
        self.phase_ptr = self.pulse_phase_ptr = 0.0
        self.config = config

    def synthesize(self, val, n_frames, volume):
        scale = MAX_SAMPLE / MAX_VOL * volume

        phase_ptr, pulse_phase_ptr = self.phase_ptr, self.pulse_phase_ptr
        config = self.config

        _float = float
        two_pi = _m.pi * 2.0

        # TODO extract into generating function
        rise, fall, duty = (config.pulse_rise, config.pulse_fall, config.pulse_duty)
        def _pulse_syn(phase):
            phase = _m.fmod(phase, two_pi);
            if phase < rise:
                return min(1.0, phase / rise)
            elif phase < rise + duty:
                return 1.0
            elif phase < rise + duty + fall:
                return max(0.0, 1.0 - ((phase - rise - duty) / fall))
            else:
                return 0.0
        _pulse_syn_vec = np.vectorize(_pulse_syn)

        if val > 0.5:
            pulse_freq = (
                _float(SAMPLE_RATE) /
                (config.pulse_length / min(3, _m.sqrt(val) * config.pulse_length_gain)))
        else:
            pulse_freq = (
                _float(SAMPLE_RATE) / _float(config.pulse_length * 2))

        if val >= 0:
            freq = config.base_freq_pos + (_m.sqrt(val) * config.freq_gain_pos)
            buff = (
                _pulse_syn_vec(
                    np.arange(n_frames)
                    * two_pi / SAMPLE_RATE * pulse_freq + pulse_phase_ptr)
                * np.sin(np.arange(n_frames) * two_pi / SAMPLE_RATE * freq + phase_ptr)
                * scale + MAX_SAMPLE
            )
        else:
            freq = config.base_freq_pos + (1.0 - val * config.freq_gain_neg)
            buff = (
                np.sin(np.arange(n_frames) * two_pi / SAMPLE_RATE * freq + phase_ptr)
                * scale + MAX_SAMPLE
            )

        phase = _float(n_frames - 1) * two_pi / SAMPLE_RATE
        self.phase_ptr = _m.fmod(phase * freq + phase_ptr, two_pi);
        self.pulse_phase_ptr = _m.fmod(phase * pulse_freq + pulse_phase_ptr,
                                       two_pi);
        return (int(x) for x in buff)


class adict(dict):
    """ small and hacky attrdict implementation """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


if __name__ == "__main__":
    main()
