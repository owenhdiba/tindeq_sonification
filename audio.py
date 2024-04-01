import sounddevice as sd
import numpy as np
import sys


class Audio:
    """Sonification of the Tindeq data.

    Creates audio stream which plays white noise with an amplitude
    proportional to how close the current Progressor weight reading is to
    a target weight.

    Attributes:
        target: The target load.
    """

    def __init__(self):
        self.target = 1.
        self.threshold = 0.1
        self.load = 0.
        self.freq = 500.
        self.start_idx = 0
        self.active = False

    def set_target(self, target):
        self.target = target

    def play_audio(self, load_queue, timer_queue):
        """Returns audio stream.

        Args:
            load_queue: Queue of weight data
            timer_queue: Queue of timer data
        Returns:
            Audio stream.
        """
        samplerate = (sd.query_devices(1, 'output')['default_samplerate'])

        def callback(outdata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            t = (self.start_idx + np.arange(frames)) / samplerate
            t = t.reshape(-1, 1)

            if timer_queue.full():
                self.active = timer_queue.get_nowait()
            if not self.active:
                outdata[:] = np.zeros(t.shape)
            else:
                if not load_queue.empty():
                    self.load = load_queue.get_nowait()
                self.gen_sine(outdata, frames, t, time)

        stream = sd.OutputStream(device=1, channels=1, callback=callback,
                                 samplerate=samplerate, blocksize=200, latency='low')
        return stream

    @staticmethod
    def white_noise(frames):
        return np.random.randn(frames)

    def gen_sine(self, outdata, frames, t, _):
        y = self.load
        sine_wave = 0.2 * np.sin(2 * np.pi * self.freq * t)

        scale_factor = abs(self.target - y) / self.target
        # if latest data is within threshold of target play pure tone
        if self.target - self.threshold < y < self.target + self.threshold:
            outdata[:] = sine_wave
        # else play noisy pure tone with amplitude
        # proportional to error
        else:
            noisy_wave = scale_factor * self.white_noise(len(t)).reshape(-1, 1)
            noisy_wave += sine_wave
            outdata[:] = noisy_wave

        self.start_idx += frames
