import sounddevice as sd
import numpy as np
import queue

#white noise
def white(N):
	return np.random.randn(N)

class Audio():
	def __init__(self):
		self.target = 1.
		self.threshold = 0.1
		self.load = 1.
		self.freq = 500.
		self.start_idx = 0
		self.active = False
	def play_audio(self, load_queue, timer_queue):
		samplerate = sd.query_devices(1, 'output')['default_samplerate']

		def callback(outdata, frames, time, status):
			if status:
				print(status, file=sys.stderr)
			t= (self.start_idx + np.arange(frames)) / samplerate
			t = t.reshape(-1, 1)

			if timer_queue.full():
				self.active = timer_queue.get_nowait()
			if self.active == False:
				outdata[:] = np.zeros(t.shape)
			else:
				if not load_queue.empty():
					self.load = load_queue.get_nowait()
				self.gen_sine(outdata, frames, t, time)
			'''

			if not load_queue.empty():
				self.load = load_queue.get_nowait()
				self.load_hist.append(self.load)
			
			self.gen_sine(outdata, frames, t, time)
			'''
		stream = sd.OutputStream(device=1, channels=1, callback=callback,
							 samplerate=samplerate, blocksize = 200, latency='low')
		return stream

	def gen_sine(self, outdata, frames, t, time):
		y = self.load
		sine_wave = 0.2 * np.sin(2 * np.pi * self.freq * t)

		scale_factor = abs(self.target - y) / self.target
		# if latest data is within threshold of target play pure tone
		if y > self.target - self.threshold and y < self.target + self.threshold:
			outdata[:] = sine_wave
		# else play noisy pure tone with amplitude
		# proportional to error
		else:
			noisy_wave = scale_factor * white(len(t)).reshape(-1,1)
			noisy_wave += sine_wave
			outdata[:] = noisy_wave

		self.start_idx += frames

	def set_target(self, target):
		self.target = target