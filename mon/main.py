#!/usr/bin/python

import json
import time
import logging
import argparse
import signal
import sys

from plugins import plugins
from plugins.base_plugin import BasePlugin

from lib.http import start_http_server

classes = {cls.__name__.lower(): cls for cls in BasePlugin.__subclasses__()}

def signal_handler(_signo, _stack_frame):
    logging.info("Exited by signal {}".format(_signo))
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Prometheus node exporter.')
    parser.add_argument('--config', default="config.json", help='config file to parse')
    parser.add_argument('--bind', default=":9090", help='address to bind')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.DEBUG)

    try:
        with open(args.config) as json_data_file:
            global_config = json.load(json_data_file)
    except Exception as e:
        logging.fatal("Bad json config. {}".format(e))
        exit()


    for name, config in global_config["plugins"].items():
        if not name in classes:
            logging.error("Plugin {} not found! skipped...".format(name))
            continue
        try:
            plugin = classes[name](config)
            plugins.append(plugin)
            logging.info("Plugin {}".format(name))
        except Exception as e:
            logging.error("Exception in {} while initialisation {}".format(name, e))


    for plugin in plugins:
        try:
            plugin.start_update()
        except Exception as e:
            logging.error("Exception {} in plugin {} on starting update".format(e, plugin.__class__.__name__))

    address, port = args.bind.split(":")
    start_http_server(int(port), address)

