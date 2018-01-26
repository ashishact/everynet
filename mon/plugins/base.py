from lib.prometheus_client.core import Gauge, Counter

from base_plugin import BasePlugin, NAMESPACE


class System(BasePlugin):
    STAT_FILE = "/proc/stat"

    def __init__(self, config):
        self.cpu = Counter("cpu",
                           "Seconds the cpus spent in each mode.",
                           labelnames=["cpu", "mode"],
                           namespace=NAMESPACE)
        self.intr = Counter('intr',
                            "Total number of interrupts serviced.",
                            namespace=NAMESPACE)
        self.ctxt = Counter('context_switches',
                            "Total number of context switches.",
                            namespace=NAMESPACE)
        self.forks = Counter('forks',
                             "Total number of forks.",
                             namespace=NAMESPACE)
        self.btime = Gauge('boot_time',
                           "Node boot time, in unixtime.",
                           namespace=NAMESPACE)
        self.prun = Gauge('procs_running',
                          "Number of processes in runnable state.",
                          namespace=NAMESPACE)
        self.pblock = Gauge('procs_blocked',
                            "Number of processes blocked waiting for I/O to complete.",
                            namespace=NAMESPACE)

    def collect(self):
        with open(self.STAT_FILE) as f:
            for line in f:
                parts = line.split()

                if parts[0].startswith("cpu"):
                    cpu_fields = ["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal", "guest"]
                    for i in xrange(1, min(len(parts), len(cpu_fields))):
                        self.cpu.labels(parts[0], cpu_fields[i - 1]).set(float(parts[i]))

                elif parts[0].startswith("intr"):
                    self.intr.set(float(parts[1]))
                elif parts[0].startswith("ctxt"):
                    self.ctxt.set(float(parts[1]))
                elif parts[0].startswith("processes"):
                    self.forks.set(float(parts[1]))
                elif parts[0].startswith("btime"):
                    self.btime.set(float(parts[1]))
                elif parts[0].startswith("procs_running"):
                    self.prun.set(float(parts[1]))
                elif parts[0].startswith("procs_blocked"):
                    self.pblock.set(float(parts[1]))


class LoadAvg(BasePlugin):
    LOAD_AVG_FILE = "/proc/loadavg"
    SUBSYSTEM = "loadavg"

    def __init__(self, config):
        self.load1 = Gauge('load1',
                           "Load average from last 1m.",
                           subsystem=self.SUBSYSTEM,
                           namespace=NAMESPACE)
        self.load5 = Gauge('load5',
                           "Load average from last 5m.",
                           subsystem=self.SUBSYSTEM,
                           namespace=NAMESPACE)
        self.load15 = Gauge('load15',
                            "Load average from last 15m.",
                            subsystem=self.SUBSYSTEM,
                            namespace=NAMESPACE)
        self.runnable = Gauge('runnable',
                              "Number of currently runnable kernel scheduling entities",
                              subsystem=self.SUBSYSTEM,
                              namespace=NAMESPACE)
        self.existed = Gauge('exist',
                             "Number of kernel scheduling entities that currently exist on the system.",
                             subsystem=self.SUBSYSTEM,
                             namespace=NAMESPACE)

    def collect(self):
        with open(self.LOAD_AVG_FILE) as f:
            line = f.readline()
            parts = line.split()
            self.load1.set(float(parts[0]))
            self.load5.set(float(parts[1]))
            self.load15.set(float(parts[2]))

            r, e = parts[3].split('/')
            self.runnable.set(float(r))
            self.existed.set(float(e))


class MemInfo(BasePlugin):
    MEM_INFO_FILE = "/proc/meminfo"
    SUBSYSTEM = 'meminfo'

    def __init__(self, config):
        self.metrics = dict()

    def collect(self):
        with open(self.MEM_INFO_FILE) as f:
            for line in f:
                parts = line.split()

                name = parts[0].strip(':'). \
                    replace(r'(', '_'). \
                    replace(')', '').lower()
                value = parts[1]

                if not name in self.metrics:
                    self.metrics[name] = Gauge(name,
                                               name + " from " + self.MEM_INFO_FILE,
                                               subsystem=self.SUBSYSTEM,
                                               namespace=NAMESPACE)

                self.metrics[name].set(float(value))


class Filesystem(BasePlugin):
    MOUNT_FILE = "/proc/mounts"
    SUBSYSTEM = 'filesystem'

    def __init__(self, config):

        import re

        self.exclude = config.get("exclude", "")

        self.mountpoints = []
        with open(self.MOUNT_FILE) as f:
            for line in f:
                parts = line.split()

                mountpoint = parts[1]
                if re.match(self.exclude, mountpoint):
                    continue

                self.mountpoints.append(mountpoint)

        labels = [
            ("size", "Filesystem size in bytes."),
            ("free", "Filesystem free space in bytes."),
            ("avail", "Filesystem space available to non-root users in bytes."),
            ("files", "Filesystem total file nodes."),
            ("files_free", "Filesystem total free file nodes."),
        ]
        self.metrics = dict()
        for name, desc in labels:
            self.metrics[name] = Gauge(name,
                                       desc,
                                       labelnames=["mountpoint"],
                                       subsystem=self.SUBSYSTEM,
                                       namespace=NAMESPACE)

    def collect(self):
        import os

        for mp in self.mountpoints[:]:
            try:
                res = os.statvfs(mp)
            except Exception as e:
                self.mountpoints.remove(mp)

            self.metrics["size"].labels(mp).set(float(res.f_blocks * res.f_bsize))
            self.metrics["free"].labels(mp).set(float(res.f_bfree * res.f_bsize))
            self.metrics["avail"].labels(mp).set(float(res.f_bavail * res.f_bsize))
            self.metrics["files"].labels(mp).set(float(res.f_files))
            self.metrics["files_free"].labels(mp).set(float(res.f_ffree))
