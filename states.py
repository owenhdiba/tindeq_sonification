from abc import ABC, abstractmethod
import time
class IdleState:
    @staticmethod
    def update(controller):
        controller.state = CountDownState(10)

class State(ABC):
    color = None
    def __init__(self, duration):
        self.duration = duration
        self.start_time = time.time()
    def update(self, controller):
        elapsed = time.time() - self.start_time
        mins, seconds = divmod(self.duration-elapsed, 60)
        controller.div.text = f'{int(mins):02d}:{int(seconds):02d}'
        controller.div.styles["background-color"] = controller.state.color
        if elapsed > self.duration:
            self.end(controller)
    @abstractmethod
    def end(self, document):
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
                lambda: controller.btn.update(label="Protocol complete")
            )
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