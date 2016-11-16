import math as _m
#import struct as _struct
import socket as _socket
import time as _time

import pyaudio as _pyaudio

# TODO logging

SIM = True

# PCM constants
SAMPLE_RATE = 9600
MAX_VOL = 100.0

# vario defaults
DEADBAND_LOW = -0.0
DEADBAND_HIGH = 0.0  # DEADBAND: Vario remains silent for DEADBAND_LOW < TE value < DEADBAND_HIGH
PULSE_LENGTH = SAMPLE_RATE / 4  # LENGTH of PULSE (PAUSE) for positive TE values, in samples
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
STF_PULSE_LENGTH = SAMPLE_RATE / 4 # LENGTH of PULSE (PAUSE) for positive values, in samples
STF_PULSE_LENGTH_GAIN = 0.2 # PULSES get shorter with higher values
STF_PULSE_DUTY = 2.6 # Pulse duty cycle 2*PI == 100%
STF_PULSE_RISE = 0.1 # Timing for rising edge of pulse (Fade-In)
STF_PULSE_FALL = 0.1 # Timing for falling edge of pulse (Fade-Out)
STF_BASE_FREQ_POS = 440   # BASE frequency for positive STF values in Hz
STF_BASE_FREQ_NEG = 440  # BASE frequency for negative STF values in Hz
STF_FREQ_GAIN_POS = 30
STF_FREQ_GAIN_NEG = 0.1

# Encodings: Those need to match
PA_FORMAT = _pyaudio.paUInt8
MAX_SAMPLE = 2 ** 7 - 1  # max of signed short
#PACK_FORMAT = "<B"  # little endian signed short, see struct docs


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

    vario = Vario(config)
    audio = _pyaudio.PyAudio()

    # find device
    device_name = "convert"
    for index in range(audio.get_device_count()):
        desc = audio.get_device_info_by_index(index)
        if desc["name"] == device_name:
            device = index
            print desc
            break

    stream = audio.open(format=PA_FORMAT,
                        channels=1,
                        rate=SAMPLE_RATE,
                        output=True,
                        output_device_index=index,
                        frames_per_buffer=int(SAMPLE_RATE * 0.5),
                        stream_callback=vario.callback)
    stream.start_stream()

    if SIM:
        i = 0
        while stream.is_active():
            _time.sleep(1)
            vario.audio_value = _m.sin(float(i) / 8.0) * 4.5
            print vario.audio_value
            i += 1
    else:
        pass
        # TODO accept connection on 4353 (sensord)
        # connect to 4352 (xcsoar)
        # read data from sensord
        # forward data to xcsoar
        # parse nmea
        # update vals
        # read commands from xcsoar
        # parse & execute commands

    stream.stop_stream()
    stream.close()
    audio.terminate()


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

        _float, _fmod, _sin = float, _m.fmod, _m.sin
        two_pi = _m.pi * 2.0
        _two_pi_sample_rate = two_pi / SAMPLE_RATE

        # TODO extract into generating function
        rise, fall, duty = (config.pulse_rise, config.pulse_fall, config.pulse_duty)
        def _pulse_syn(phase):
            phase = _fmod(phase, two_pi);
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

        if val >= 0:
            freq = config.base_freq_pos + (_m.sqrt(val) * config.freq_gain_pos)
            freqx = freq * _two_pi_sample_rate
            pulse_freqx = pulse_freq * _two_pi_sample_rate
            buff = (
                _pulse_syn(j * pulse_freqx + pulse_phase_ptr)
                * _sin(j * freqx + phase_ptr)
                * scale
                + MAX_SAMPLE
                for j in
                (_float(j) for j in xrange(n_frames))
            )
        else:
            freq = config.base_freq_pos + (1.0 - val * config.freq_gain_neg)
            freqx = freq * _two_pi_sample_rate
            buff = (
                _sin(j * freqx + phase_ptr)
                * scale
                + MAX_SAMPLE
                for j in
                (_float(j) for j in xrange(n_frames))
            )

        phase = _float(n_frames - 1) * _two_pi_sample_rate
        self.phase_ptr = _fmod(phase * freq + phase_ptr, two_pi);
        self.pulse_phase_ptr = _fmod(phase * pulse_freq + pulse_phase_ptr,
                                     two_pi);
        return (int(x) for x in buff)


class adict(dict):
    """ small and hacky attrdict implementation """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


if __name__ == "__main__":
    main()
