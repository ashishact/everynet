import logging
import socket

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from lib.prometheus_client import generate_latest, core
import threading
from lib.prometheus_client.exposition import CONTENT_TYPE_LATEST

from plugins import plugins

class MetricsRequestHandler(BaseHTTPRequestHandler):

    get_handlers = dict()

    def do_GET(self):
        if self.path in self.get_handlers:
            self.get_handlers[self.path](self)
        else:
            self.send_response(404)

    def log_message(self, format, *args):
        return

    @classmethod
    def route(cls, path):
        def decorator(handler):
            cls.get_handlers[path] = handler
            return handler
        return decorator


class TimeoutHTTPServer(HTTPServer):

    def get_request(self):
        sock, addr = self.socket.accept()
        sock.settimeout(5)
        return (sock, addr)


def start_http_server(port, addr=''):
    httpd = TimeoutHTTPServer((addr, port), MetricsRequestHandler)
    httpd.socket.settimeout(15)
    httpd.serve_forever()


def gzip_encode(content):
    import StringIO
    import gzip
    out = StringIO.StringIO()
    f = gzip.GzipFile(fileobj=out, mode='w', compresslevel=5)
    f.write(content)
    f.close()
    return out.getvalue()


def collect_all():
    for plugin in plugins:
        try:
            plugin.collect()
        except Exception as e:
            logging.error("Exception {} in {} while collecting".format(str(e), str(plugin.__class__.__name__)))


@MetricsRequestHandler.route("/metrics")
def metrics_handler(request):
    request.send_response(200)

    request.send_header('Content-Type', CONTENT_TYPE_LATEST)
    request.send_header("Content-Encoding", "gzip")
    request.end_headers()

    collect_all()

    content = generate_latest(core.REGISTRY)
    content = gzip_encode(content)

    request.wfile.write(content)


