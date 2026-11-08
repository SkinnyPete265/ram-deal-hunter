#!/usr/bin/env python3
"""Serve the read-only dashboard locally and trigger price scans."""
import json
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from monitor import run

ROOT=Path(__file__).resolve().parent
LOCK=threading.Lock()
STATUS={"running":False,"completed_at":None,"last_error":None}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/"docs"),**kwargs)
    def reply(self,status,body):
        data=json.dumps(body).encode()
        self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(data)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if urlsplit(self.path).path=="/api/status":
            self.reply(200,dict(STATUS));return
        return super().do_GET()
    def do_POST(self):
        if urlsplit(self.path).path!="/api/scan": self.reply(404,{"error":"Not found"});return
        host=self.headers.get("Host","");origin=self.headers.get("Origin","")
        if host not in ("127.0.0.1:8765","localhost:8765") or (origin and origin not in ("http://127.0.0.1:8765","http://localhost:8765")):
            self.reply(403,{"error":"Origin forbidden"});return
        if not start(): self.reply(409,{"error":"Already scanning"});return
        self.reply(202,{"started":True})

def scan():
    try: run(); STATUS["last_error"]=None
    except Exception as e: STATUS["last_error"]=str(e)[:300]
    finally:
        STATUS["completed_at"]=time.time()
        STATUS["running"]=False
        LOCK.release()

def start():
    if not LOCK.acquire(blocking=False): return False
    STATUS["running"]=True
    threading.Thread(target=scan,daemon=True).start()
    return True

def schedule():
    while True:
        start()
        time.sleep(1800)

if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",8765),Handler)
    threading.Thread(target=schedule,daemon=True).start()
    print("Dashboard: http://127.0.0.1:8765",flush=True)
    threading.Timer(0.5,lambda:webbrowser.open("http://127.0.0.1:8765")).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
