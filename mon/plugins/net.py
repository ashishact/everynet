import os
import re
import logging

from base_plugin import BasePlugin, NAMESPACE
from lib.prometheus_client import Gauge


class NetDev(BasePlugin):
    INTERFACE_PATH = "/sys/class/net"
    NET_DEV_FILE = "/proc/net/dev"
    SUBSYSTEM = 'netdev'

    def __init__(self, config):
        self.exclude = config.get('exclude', '')
        self.metrics = dict()

        self.names = ["rx_bytes", "rx_packets", "rx_errs", "rx_drop", "rx_fifo",
                      "rx_frame", "rx_compressed", "rx_multicast",
                      "tx_bytes", "tx_packets", "tx_errs", "tx_drop",
                      "tx_fifo", "tx_colls", "tx_carrier", "tx_compressed"]
        for name in self.names:
            self.metrics[name] = Gauge(name,
                                       name + " from " + self.NET_DEV_FILE,
                                       subsystem=self.SUBSYSTEM,
                                       namespace=NAMESPACE,
                                       labelnames=["device"])
        self.metrics["carrier"] = Gauge("carrier",
                                        "Cable existence",
                                        subsystem=self.SUBSYSTEM,
                                        namespace=NAMESPACE,
                                        labelnames=["device"])

    def collect(self):
        with open(self.NET_DEV_FILE) as f:
            f.readline()
            f.readline()

            for line in f:
                parts = line.split()

                iface = parts[0].strip(':')
                if re.match(self.exclude, iface):
                    continue

                for i in xrange(0, len(self.names)):
                    value = parts[i + 1]
                    self.metrics[self.names[i]].labels(iface).set(float(value))

                cable_exists = open(os.path.join(self.INTERFACE_PATH, iface, "carrier")).read()
                self.metrics["carrier"].labels(iface).set(float(cable_exists))


class Ping(BasePlugin):
    class PingTarget(object):

        import threading

        class PingThread(threading.Thread):
            def __init__(self, interval, host, timeout, metric):
                super(self.__class__, self).__init__()
                self.interval = interval
                self.host = host
                self.timeout = timeout
                self.metric = metric

            def run(self):
                from time import sleep
                import lib.ping as ping

                while True:
                    res_timeout = float(self.timeout)
                    try:
                        timeout = ping.do_one(self.host, self.timeout)
                        if timeout is not None:
                            res_timeout = timeout
                    except Exception as e:
                        logging.info("Error while ping {}, {}".format(self.host, e))
                    finally:
                        self.metric.labels(self.host).set(res_timeout * 1000)  # ms

                    sleep(self.interval)

        def __init__(self, config, metric):
            self.host = config.get('address')
            self.timeout = config.get('timeout', 1)
            self.interval = config.get('interval', 5)
            self.metric = metric

        def start_update(self):
            self.thread = Ping.PingTarget.PingThread(self.interval, self.host, self.timeout, self.metric)
            self.thread.daemon = True
            self.thread.start()

    def __init__(self, config):
        self.metric = Gauge("ping",
                            "Ping to host",
                            namespace=NAMESPACE,
                            labelnames=["host"])

        self.configs = config.get('targets')
        self.targets = []
        for config in self.configs:
            self.targets.append(Ping.PingTarget(config, self.metric))

    def start_update(self):
        for target in self.targets:
            target.start_update()


class NetDevExists(BasePlugin):
    INTERFACE_PATH = "/sys/class/net"
    SUBSYSTEM = 'netdev'

    def __init__(self, config):

        self.interfaces = config.get('interfaces')

        self.metric = Gauge("exists",
                            "Interface existence",
                            subsystem=self.SUBSYSTEM,
                            namespace=NAMESPACE,
                            labelnames=["device"])

    def collect(self):
        dirs = os.listdir(self.INTERFACE_PATH)

        for ask_iface in self.interfaces:
            exists = False

            for dir_iface in dirs:
                if re.match(ask_iface, dir_iface):
                    exists |= True
                    break

            self.metric.labels(ask_iface).set(float(exists))
