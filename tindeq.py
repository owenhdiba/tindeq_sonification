"""Search for, connect to, and communicate with Tindeq progressor.

Connect to the Tindeq Progressor and send commands to control it. The load
data is received and put into queues to be used in other parts of the program.

Use as a context manager:
    aysnc with TindeqProgressor(parent) as tindeq:
            await tindeq.get_batt()
On entry the context manager will search for and connect to the progressor,
and on exit will disconnect. A full example is given at the end of this module.
"""
import struct
import uuid
import asyncio
import queue
from bleak import BleakClient, BleakScanner


class TindeqProgressor:
    """Communicate with Tindeq Progressor device over Bluetooth.

       Send bytes to write UUID to control the device. Current weight or
       rate of force is reported on the notify UUID, these are then pushed
       to a tuple of queues to be used by consumers in other threads.
    """

    response_codes = {"cmd_resp": 0, "weight_measure": 1, "low_pwr": 4}
    cmds = dict(
        TARE_SCALE=0x64,
        START_WEIGHT_MEAS=0x65,
        STOP_WEIGHT_MEAS=0x66,
        START_PEAK_RFD_MEAS=0x67,
        START_PEAK_RFD_MEAS_SERIES=0x68,
        ADD_CALIB_POINT=0x69,
        SAVE_CALIB=0x6A,
        GET_APP_VERSION=0x6B,
        GET_ERR_INFO=0x6C,
        CLR_ERR_INFO=0x6D,
        SLEEP=0x6E,
        GET_BATT_VLTG=0x6F,
    )
    service_uuid = "7e4e1701-1ea6-40c9-9dcc-13d34ffead57"
    write_uuid = "7e4e1703-1ea6-40c9-9dcc-13d34ffead57"
    notify_uuid = "7e4e1702-1ea6-40c9-9dcc-13d34ffead57"

    def __init__(self, queues, queue_function):
        """
        Initializes the instance with queues and function that processes them.

        Args:
            queues:
                tuple of queues that data from the sensor is pushed to
            queue_function:
                function that takes queues, time and weight from `_notify_handler`
                method and pushes the sensor data to the queues. This function
                must have the form:
                    def f(queue1, ..., queueN, time, weight):
                        ...
                where in the function body the data is put into the queues.
        """
        self.queues = queues
        self.queue_function = queue_function
        self.info_struct = struct.Struct("<bb")
        self.data_struct = struct.Struct("<fl")
        self._tare_value = 0.0
        self.client = None
        self.last_cmd = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *excinfo):
        await self.disconnect()

    def _notify_handler(self, _, data):
        """
        Simply pass on payload to correct handler
        """
        data = bytes(data)
        kind, size = self.info_struct.unpack(data[:2])
        if kind == self.response_codes["weight_measure"]:
            # decode data
            for weight, useconds in self.data_struct.iter_unpack(data[2:]):
                now = useconds / 1.0e6
                tared_weight = weight - self._tare_value
                self.queue_function(*self.queues, now, tared_weight)

        elif kind == self.response_codes["cmd_resp"]:
            self._cmd_response(data)
        elif kind == self.response_codes["low_pwr"]:
            print("low power warning")
        else:
            raise RuntimeError(f"unknown msg kind {kind}")

    def _cmd_response(self, value):
        if self.last_cmd == "get_app":
            print(f"FW version : {value[2:].decode('utf-8')}")
        elif self.last_cmd == "get_batt":
            (vdd,) = struct.unpack("<I", value[2:])
            print(f"Battery level = {vdd} [mV]")
        elif self.last_cmd == "get_err":
            try:
                print("Crashlog : {0}".format(value[2:].decode("utf-8")))
            except UnicodeDecodeError:
                pass
        self.last_cmd = None

    async def disconnect(self):
        await self._send_cmd("SLEEP")
        await self.client.disconnect()
        self.client = None

    async def connect(self):
        stop_event = asyncio.Event()
        TARGET_NAME = "Progressor"

        def callback(device, _):
            try:
                name_true = device.name[: len(TARGET_NAME)] == TARGET_NAME
            except (TypeError, AttributeError):
                pass
            else:
                if name_true:
                    stop_event.set()
                    self.client = BleakClient(device.address)
                    print(f'Found "{device.name}" with address {device.address}')

        try:
            async with asyncio.timeout(10):
                async with BleakScanner(callback) as scanner:
                    await stop_event.wait()
        except TimeoutError:
            raise RuntimeError("Could not connect to progressor")

        await self.client.connect()
        success = self.client.is_connected
        if success:
            await self.client.start_notify(
                uuid.UUID(self.notify_uuid), self._notify_handler
            )
        else:
            raise RuntimeError("Could not connect to progressor")
        return success

    def _pack(self, cmd):
        return cmd.to_bytes(2, byteorder="little")

    async def _send_cmd(self, cmd_key):
        if not hasattr(self, "client") or self.client is None:
            return

        await self.client.write_gatt_char(
            uuid.UUID(self.write_uuid), self._pack(self.cmds[cmd_key])
        )

    async def get_batt(self):
        self.last_cmd = "get_batt"
        await self._send_cmd("GET_BATT_VLTG")

    async def get_fw_info(self):
        self.last_cmd = "get_app"
        await self._send_cmd("GET_APP_VERSION")

    async def get_err(self):
        self.last_cmd = "get_err"
        await self._send_cmd("GET_ERR_INFO")

    async def clear_err(self):
        self.last_cmd = None
        await self._send_cmd("CLR_ERR_INFO")

    async def start_logging_weight(self):
        self.last_cmd = None
        await self._send_cmd("START_WEIGHT_MEAS")

    async def stop_logging_weight(self):
        self.last_cmd = None
        await self._send_cmd("STOP_WEIGHT_MEAS")

    async def sleep(self):
        self.last_cmd = None
        await self._send_cmd("SLEEP")

    def tare_mean(self):
        weight_sum = 0
        samples = 0
        while self.queues[0].qsize() > 0:
            weight_sum += self.queues[0].get()
            samples += 1
        return weight_sum / samples

    async def soft_tare(self):
        """
        Calibrate the device by taking average of weights over one-second
        window.
        """
        _saved_queue_function = self.queue_function
        _saved_queues = self.queues

        def tare_queue_function(tare_queue, _, weight):
            tare_queue.put(weight)

        self.queues = (queue.Queue(),)
        self.queue_function = tare_queue_function
        await self.start_logging_weight()
        await asyncio.sleep(1)
        await self.stop_logging_weight()
        # this next sleep is essential. It takes some time
        # before the sensor receives the notification.
        # and in the meantime we don't want the last few lines
        # to execute.
        await asyncio.sleep(1)
        self._tare_value = self.tare_mean()
        self.queues = _saved_queues
        self.queue_function = _saved_queue_function


if __name__ == "__main__":
    '''Example usage of the class. The `example` coroutine uses the async 
    context manager to connect to the Progressor, then sends it a series of 
    commands. The `printer` function is run in another thread and 
    receives weight data via `print_queue`, then prints the time and weight.
    '''
    async def example(print_queue, queue_func):
        loop = asyncio.get_running_loop()
        async with TindeqProgressor((print_queue,), queue_func) as tindeq:
            await tindeq.get_batt()
            await asyncio.sleep(0.5)
            await tindeq.get_fw_info()
            await asyncio.sleep(0.5)
            await tindeq.get_err()
            await asyncio.sleep(0.5)
            await tindeq.clear_err()
            await asyncio.sleep(0.5)
            await tindeq.soft_tare()

            try:
                async with asyncio.timeout(2):
                    await asyncio.gather(
                        loop.run_in_executor(None, printer,
                                             print_queue),
                        tindeq.start_logging_weight()
                    )
            except TimeoutError:
                print_queue.put_nowait("end")
                print("Done!")


    def printer(print_queue):
        while True:
            try:
                vals = print_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                if vals == 'end':
                    break
                print(vals)


    print_queue = queue.Queue()


    def queue_func(print_queue, read_time, read_weight):
        print_queue.put_nowait((read_time, read_weight))


    asyncio.run(example(print_queue, queue_func))
