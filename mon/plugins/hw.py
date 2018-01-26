from os import path
import re
from serial import Serial
import logging

from base_plugin import BasePlugin, NAMESPACE
from lib.prometheus_client import Gauge


class MCU(BasePlugin):
    SUBSYSTEM = 'mcu'
    MCU_FW_VERSION = "1.2"

    import threading

    class MCUThread(threading.Thread):
        def __init__(self, interval, port):
            super(self.__class__, self).__init__()

            self.interval = interval
            self.port = port

            self.metrics = {}
            self.metrics = {
                "status": Gauge("status",
                                "MCU status",
                                subsystem=MCU.SUBSYSTEM,
                                namespace=NAMESPACE,
                                labelnames=["input"]),
                "bq_status": Gauge("bq_status",
                                   "MCU BQ error count",
                                   subsystem=MCU.SUBSYSTEM,
                                   namespace=NAMESPACE),
            }

        def ask(self, command, echo=False):

            if not self.port:
                raise "Serial port not opened"

            for c in command + "\n":
                self.port.write(c)

            data = self.port.read(50)
            reply = map(lambda x: x.strip(), data.split())

            if echo:
                if command in reply[0]:
                    del reply[0]

            result = reply.pop() == "OK"
            return result, reply

        def run(self):
            from time import sleep

            while True:

                try:

                    for cmd in ["poe", "usb", "off", "batbad"]:
                        res, reply = self.ask("status " + cmd)
                        self.metrics["status"].labels(cmd).set(int(reply[0], 16))

                    cmd = "bq status"
                    res, reply = self.ask(cmd)
                    self.metrics["bq_status"].set(len(reply))

                except Exception as e:
                    logging.info("Error while getting metrics from MCU {}".format(e))

                sleep(self.interval)


    def __init__(self, config):
        self.interval = config.get("interval", 30)
        self.port = Serial(**config.get("serial"))
        self.thread = MCU.MCUThread(self.interval, self.port)


    def start_update(self):
        self.thread.daemon = True
        self.thread.start()
