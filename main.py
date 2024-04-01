"""
Run the Bokeh server, connect to the Tindeq Progressor, generate and play
sonified data from Progressor.

"""

import queue
from audio import Audio
from tindeq import TindeqProgressor
from controller import Controller
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
import tornado


# Controls how data is put into the queues.
def queue_function(plot_queue, sound_queue, sensor_time, sensor_weight):
    if sound_queue.full():
        sound_queue.get_nowait()
    sound_queue.put_nowait(sensor_weight)
    plot_queue.put_nowait((sensor_time, sensor_weight))


# Create the TindeqProgressor, Controller, and Audio objects and
# the queues that are used to share data between them.
audio = Audio()
plot_queue = queue.Queue()
audio_queue = queue.Queue(maxsize=1)
timer_queue = queue.Queue(maxsize=1)
sensor = TindeqProgressor((plot_queue, audio_queue), queue_function)
controller = Controller(sensor, audio, plot_queue, audio_queue, timer_queue)

apps = {"/": Application(FunctionHandler(controller.make_document))}
server = Server(apps, port=5006)
server.start()

io_loop = tornado.ioloop.IOLoop.current()
print("Opening Bokeh application on http://localhost:5006/")
io_loop.add_callback(server.show, "/")
io_loop.start()
