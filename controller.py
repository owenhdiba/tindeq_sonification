import asyncio
import tornado
from states import *
from bokeh.plotting import figure
from bokeh.layouts import row, column
from bokeh.models import Button, Slider, Div, Band, Whisker, ColumnDataSource

class Controller():
    def __init__(self, sensor, audio, plot_queue, audio_queue, timer_queue):
        self.sensor = sensor
        self.audio = audio
        self.plot_queue = plot_queue
        self.audio_queue = audio_queue
        self.timer_queue = timer_queue
        self.state = IdleState
        self.active_time = 7
        self.rest_time = 120
        self.target_load = 10
        self.sets = 6
        self.completed = 0
        self.countdown = 10
        self.div = Div(
            text=f'00:{self.countdown:02d}',
            styles={
                "font-size": "500%",
                "color": "white",
                "background-color": "orange",
                "text-align": "center",
            },
        )
        self.counter_slider = Slider(start=0, end=self.sets,
                            value=self.completed,
                            step=1, title="Completed Sets", disabled=True)
        self.doc = None
    def remove_callback(self):
        self.doc.remove_periodic_callback(self.callback)
    def make_document(self, doc):
        self.doc = doc
        io_loop = tornado.ioloop.IOLoop.current()
        io_loop.add_callback(connect_from_doc, self, self.sensor)
        source = ColumnDataSource(data=dict(x=[], y=[]))
        fig = figure(width=600, height=400, title="Real-time Data",
                     x_axis_label="Time (s)",
                     y_axis_label="Load (kg)"
                     )
        fig.line(x="x", y="y", source=source)
        doc.title = "Tindeq Sonification"

        active_slider = Slider(start=4, end=20,
                                    value=self.active_time,
                                    step=1, title="Active Time (s)")
        rest_slider = Slider(start=10, end=180,
                                  value=self.rest_time,
                                  step=10, title="Rest Time (s)")
        target_slider = Slider(start=1, end=100,
                                    value=self.target_load,
                                    step=1, title="Target Load (kg)")
        set_slider = Slider(start=1, end=20,
                            value=self.sets,
                            step=1, title="Sets")

        btn = Button(label="Searching for device...", disabled=True)
        def onclick():
            for widget in widgets:
                widget.disabled = True
            self.active = True
            self.active_time = active_slider.value
            self.rest_time = rest_slider.value
            self.target_load = target_slider.value
            self.audio.set_target(self.target_load)
            self.sets = set_slider.value
            duration = ((self.rest_time + self.active_time)
                      * self.sets + self.countdown)
            self.duration = duration
            self.counter_slider.end = self.sets
            io_loop = tornado.ioloop.IOLoop.current()
            io_loop.add_callback(
                main, self.sensor, self.audio, self.audio_queue,
                self.timer_queue, duration
            )
            self.callback = doc.add_periodic_callback(update, 50)
            doc.add_next_tick_callback(
                lambda: btn.update(label="Running")
            )
        btn.on_click(onclick)
        self.btn = btn

        widgets = [btn, active_slider, rest_slider,
                   target_slider, set_slider, self.counter_slider]
        widget_column = column(*widgets, self.div)
        first_row = row(widget_column, fig)
        doc.add_root(column(first_row, sizing_mode="stretch_both"))

        def update():
            X = []
            Y = []
            while self.plot_queue.qsize() > 0:
                x, y = self.plot_queue.get()
                X.append(x)
                Y.append(y)
            source.stream({"x": X, "y": Y})
            self.state.update(self)



async def connect_from_doc(controller, sensor):
    try:
        await sensor.connect()
    except Exception as err:
        controller.doc.add_next_tick_callback(
            lambda: controller.btn.update(label="Connect failed.")
        )
        print("Connection Failed ... check Tindeq and restart server")
    else:
        await asyncio.sleep(1)
        controller.doc.add_next_tick_callback(
            lambda: controller.btn.update(label="Connection successful")
        )
        await asyncio.sleep(1)
        controller.doc.add_next_tick_callback(
            lambda: controller.btn.update(label="Run", disabled=False)
        )

async def main(sensor, audio, sound_queue, timer_queue, duration):
    await sensor.soft_tare()
    with audio.play_audio(sound_queue, timer_queue) as stream:
        await sensor.start_logging_weight()
        await asyncio.sleep(duration)
        await sensor.stop_logging_weight()
        stream.stop()