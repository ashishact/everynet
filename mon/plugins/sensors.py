from base_plugin import BasePlugin, NAMESPACE
from lib.prometheus_client import Gauge


class LMSensors(BasePlugin):
    SUBSYSTEM = 'sensors'

    def __init__(self, config):

        import lib.sensors as lmsens
        import re

        exclude_chips = config.get("exclude_chips", "^$")

        lmsens.init()
        self.chips = []
        self.metrics = dict()
        for chip in lmsens.iter_detected_chips():
            chip_name = str(chip).replace('-', '_').lower()
            if re.match(exclude_chips, chip_name):
                continue
            self.chips.append(chip)
            self.metrics[str(chip)] = Gauge(chip_name,
                                            "Values from " + chip_name + " sensor.",
                                            labelnames=["feature", "label"],
                                            subsystem=self.SUBSYSTEM,
                                            namespace=NAMESPACE)

    def collect(self):
        for chip in self.chips:
            for feature in chip:
                self.metrics[str(chip)]. \
                    labels(feature.name, feature.label). \
                    set(float(feature.get_value()))


class Imx28(BasePlugin):
    SUBSYSTEM = 'sensors'

    VOLTAGE_FILE = "/sys/class/power_supply/battery/voltage_now"
    TEMP_RAW_FILE = "/sys/bus/iio/devices/iio:device0/in_temp8_raw"

    def __init__(self, config):

        self.metric = Gauge("imx28",
                            "Values from imx28 sensors",
                            labelnames=["label"],
                            subsystem=self.SUBSYSTEM,
                            namespace=NAMESPACE)

    def collect(self):
        with open(self.VOLTAGE_FILE) as f:
            line = f.readline()
            voltage = float(line) / 1000

        with open(self.TEMP_RAW_FILE) as f:
            raw = float(f.readline())

        temp = (raw - 1075.69) * 0.253

        self.metric.labels("voltage").set(voltage)
        self.metric.labels("cpu_temp").set(temp)

