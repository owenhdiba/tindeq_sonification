"""Represents the state of the isometric exercise protocol.

State classes represent the state of the protocol i.e. whether we are in
an active or rest portion of the protocol. Each class has an `update` method
which calculates the time elapsed since its creation, and updates the text
that represents the timer in the Bokeh Document accordingly. When the timer
exceeds the State's duration the `end` method is called which replaces the
Bokeh document state with a new state.

The Bokeh document starts as an `IdleState`. The first time the update callback
is called, the document state is replaced with a `CountDownState`. When this
state ends, the document state cycles between `Active State`s and
`RestState`s until the test is completed.
"""
from abc import ABC, abstractmethod
import time


class IdleState:
    @staticmethod
    def update(controller):
        controller.state = CountDownState(10)


class State(ABC):
    """
    Base class for states.

    Attributes:
        duration: The duration of the state in seconds.
        start_time: The time the state is created.
    """
    color = None

    def __init__(self, duration):
        self.duration = duration
        self.start_time = time.time()

    def update(self, controller):
        """
        Updates the timer text of the Controller object.

        Args:
            controller: Controller object.
        """
        elapsed = time.time() - self.start_time
        mins, seconds = divmod(self.duration - elapsed, 60)
        controller.div.text = f'{int(mins):02d}:{int(seconds):02d}'
        controller.div.styles["background-color"] = controller.state.color
        if elapsed > self.duration:
            self.end(controller)

    @abstractmethod
    def end(self, controller):
        """
        Called when the time has surpassed the State's duration. Replaces
        the Controller's state.

        Args:
            controller: Controller object.
        """
        pass


class CountDownState(State):
    color = 'orange'

    def end(self, controller):
        controller.state = ActiveState(controller.active_time)
        if controller.timer_queue.full():
            controller.timer_queue.get()
        controller.timer_queue.put(True)


class RestState(State):
    color = 'red'

    def end(self, controller):
        if controller.sets == 0:
            controller.div.text = '00:00'
            controller.remove_callback()
            controller.doc.add_next_tick_callback(
                lambda: controller.btn.update(label="Protocol complete.")
            )
            controller.remove_callback()
        else:
            controller.state = ActiveState(controller.active_time)
            if controller.timer_queue.full():
                controller.timer_queue.get()
            controller.timer_queue.put(True)


class ActiveState(State):
    color = 'green'

    def end(self, controller):
        controller.sets -= 1
        controller.completed += 1
        controller.doc.add_next_tick_callback(
            lambda: controller.counter_slider.update(
                value=controller.completed
            )
        )
        controller.state = RestState(controller.rest_time)
        if controller.timer_queue.full():
            controller.timer_queue.get()
        controller.timer_queue.put(False)
