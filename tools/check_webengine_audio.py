"""Optional Qt WebEngine playback probe; requires PyQt6 and PyQt6-WebEngine."""

import argparse
from functools import partial
import html
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread
import time

from PyQt6.QtCore import QTimer, QUrl, QT_VERSION_STR
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineCore import QWebEnginePage


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def probe(sources):
    if len(sources) != 1:
        raise ValueError("Probe one source per process; Qt WebEngine cannot safely restart between cases")
    app = QApplication(["webengine-audio-probe"])
    page = QWebEnginePage()
    results = []
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            for index, source in enumerate(sources):
                if source.startswith("https://"):
                    media = source
                else:
                    path = Path(source)
                    media = f"clip-{index}{path.suffix}"
                    (directory / media).write_bytes(path.read_bytes())
                name = f"case-{index}.html"
                (directory / name).write_text('<!doctype html><audio controls preload="none" src="' + html.escape(media, quote=True) + '"></audio>')
                timer = QTimer()
                started = time.monotonic()
                state = {"qt": QT_VERSION_STR, "case": index, "source": source}

                def receive(value):
                    if not value:
                        return
                    state.update(json.loads(value))
                    if state.get("error") or state.get("time", 0) > 0.2 or time.monotonic() - started > 10:
                        state["passed"] = not state.get("error") and state.get("time", 0) > 0.2
                        timer.stop()
                        app.quit()

                def poll():
                    page.runJavaScript('''JSON.stringify((function(){
                      var a=document.querySelector('audio');
                      return a?{time:a.currentTime,error:a.error&&a.error.code,message:a.error&&a.error.message,ready:a.readyState,
                        aac:a.canPlayType('audio/mp4; codecs="mp4a.40.2"'),mp3:a.canPlayType('audio/mpeg')}:{};
                    })())''', receive)

                def loaded(ok):
                    page.runJavaScript("document.querySelector('audio').play().catch(function(){})")

                page.loadFinished.connect(loaded)
                timer.timeout.connect(poll)
                timer.start(100)
                page.setUrl(QUrl(f"http://127.0.0.1:{server.server_port}/{name}"))
                app.exec()
                timer.stop()
                page.loadFinished.disconnect(loaded)
                results.append(state)
        finally:
            server.shutdown()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="One local clip or direct HTTPS preview URL")
    args = parser.parse_args()
    result = probe([args.source])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if all(item["passed"] for item in result) else 1)
