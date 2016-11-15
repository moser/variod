import collections as _collections
import math as _m
import struct as _struct
import threading as _threading
import time as _time

import alsaaudio as _a

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
BASE_FREQ_POS = 400  # BASE frequency for positive TE values in Hz
BASE_FREQ_NEG = 400  # BASE frequency for negative TE values in Hz
FREQ_GAIN_POS = 100
FREQ_GAIN_NEG = -30

STF_DEADBAND_LOW = -2.5  
STF_DEADBAND_HIGH = 2.5  # DEADBAND: Vario remains silent for DEADBAND_LOW < STF value < DEADBAND_HIGH 
STF_PULSE_LENGTH = 12288 # LENGTH of PULSE (PAUSE) for positive values, in samples
STF_PULSE_LENGTH_GAIN = 0.2 # PULSES get shorter with higher values
STF_PULSE_DUTY = 2.6 # Pulse duty cycle 2*PI == 100%
STF_PULSE_RISE = 0.1 # Timing for rising edge of pulse (Fade-In)
STF_PULSE_FALL = 0.1 # Timing for falling edge of pulse (Fade-Out)
STF_BASE_FREQ_POS = 400   # BASE frequency for positive STF values in Hz
STF_BASE_FREQ_NEG = 400  # BASE frequency for negative STF values in Hz
STF_FREQ_GAIN_POS = 30
STF_FREQ_GAIN_NEG = 0.1

# PCM constants
SAMPLE_RATE = 44100
MAX_VOL = 100.0

# Encodings: Those need to match
PCM_FORMAT = _a.PCM_FORMAT_U8  # little endian signed short
MAX_SAMPLE = 2 ** 7 - 1  # max of signed short
#PACK_FORMAT = "<h"  # little endian signed short, see struct docs


def main():
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
    comm = adict(
        config=config,
        audio_value=0.0,
        audio_mode="vario",
        volume=50.0,
    )
    sound_thread = _threading.Thread(target=sound_main, args=(comm,))
    sound_thread.daemon = True
    sound_thread.start()

    if SIM:
        for i in range(100):
            _time.sleep(1)
            comm.audio_value = _m.sin(float(i) / 8.0) * 4.5
    else:
        import socket as _socket
        # TODO accept connection on 4353 (sensord)
        # connect to 4352 (xcsoar)
        # read data from sensord
        # forward data to xcsoar
        # parse nmea
        # update vals
        # read commands from xcsoar
        # parse & execute commands


# TODO implement STF logic


def sound_main(comm):
    pcm = _a.PCM(mode=_a.PCM_NORMAL)
    pcm.setchannels(1)
    pcm.setrate(SAMPLE_RATE)
    pcm.setformat(PCM_FORMAT)
    period = 0.2  # sec the signal stays the same
    synthesizer = Synthesizer(comm.config[comm.audio_mode])

    wrote = 0
    iteration_took = period
    sound_started = _time.time()
    # TODO `wrote` will overflow, reset from time to time
    while True:
        iteration_started = _time.time()
        target_time = iteration_started + iteration_took + 2 * period
        frames = int(SAMPLE_RATE * (target_time - sound_started) - wrote)
        if frames > 0:
            pcm.write(synthesizer.synthesize(comm.audio_value, frames))
        wrote += frames
        iteration_took = _time.time() - iteration_started
        _time.sleep(min(period - iteration_took, 0.0001))
        iteration_took = _time.time() - iteration_started


class Synthesizer(object):  # TODO test
    def __init__(self, config):
        self.volume = 50.0
        self.phase_ptr = self.pulse_phase_ptr = 0.0
        self.config = config

    def synthesize(self, val, n_frames):
        scale = MAX_SAMPLE / MAX_VOL * self.volume

        phase_ptr, pulse_phase_ptr = self.phase_ptr, self.pulse_phase_ptr
        config = self.config

        _triangle = triangle
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

        if val > 0.5:
            pulse_freq = (
                _float(SAMPLE_RATE) /
                (config.pulse_length / min(3, _m.sqrt(val) * config.pulse_length_gain)))
        else:
            pulse_freq = (
                _float(SAMPLE_RATE) / _float(config.pulse_length * 2))

        _two_pi_sample_rate = two_pi / SAMPLE_RATE
        if val >= 0:
            freq = config.base_freq_pos + (_m.sqrt(val) * config.freq_gain_pos)
            buff = (
                _pulse_syn(_float(j) * _two_pi_sample_rate
                           * pulse_freq + pulse_phase_ptr)
                * _triangle(_float(j) * _two_pi_sample_rate
                            * freq + phase_ptr)
                * scale
                for j in xrange(n_frames)
            )
        else:
            freq = config.base_freq_pos + (1.0 - val * config.freq_gain_neg)
            buff = (
                _triangle(_float(j) * _two_pi_sample_rate * freq + phase_ptr)
                * scale
                for j in xrange(n_frames)
            )

        phase = _float(n_frames - 1) * _two_pi_sample_rate
        self.phase_ptr = _m.fmod(phase * freq + phase_ptr, two_pi);
        self.pulse_phase_ptr = _m.fmod(phase * pulse_freq + pulse_phase_ptr,
                                       two_pi);

        return "".join((chr(int(x) + 127) for x in buff))


def triangle(phase):
    pi, two_pi = _m.pi, _m.pi * 2.0
    phase = _m.fmod(phase, two_pi)
    if phase < pi:
        return (phase - pi / 2) * 2 / pi
    else:
        return 1 - (phase - pi) * 2 / pi


class adict(dict):
    """ small and hacky attrdict implementation """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


if __name__ == "__main__":
    main()
