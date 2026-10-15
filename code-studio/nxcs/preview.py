"""Live Preview: local static server bound to 127.0.0.1 only (never exposed externally)."""
import functools, http.server, socket, threading


class Preview:
    def __init__(self, root, port=0):
        self.log = []
        outer = self

        class H(http.server.SimpleHTTPRequestHandler):
            def log_message(self, fmt, *a):
                outer.log.append(fmt % a)
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=root))
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start(); return "http://127.0.0.1:%d/" % self.port

    def stop(self):
        self.httpd.shutdown(); self.httpd.server_close()

    def port_open(self):
        with socket.socket() as s:
            s.settimeout(1); return s.connect_ex(("127.0.0.1", self.port)) == 0
