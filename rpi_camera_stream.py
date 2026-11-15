#!/usr/bin/env python3
"""
Raspberry Pi Live Camera Streamer for Home Assistant
Supports both official Raspberry Pi Camera Modules (CSI ribbon) and USB Webcams.
Serves a low-latency MJPEG live stream over HTTP.
"""

import io
import time
from http import server
import socketserver

PORT = 8000

# Try importing PiCamera2 (Raspberry Pi OS Bookworm/Bullseye with CSI ribbon camera)
# Fallback to OpenCV (cv2) for standard USB webcams
USE_PICAMERA = False
try:
    from picamera2 import Picamera2
    USE_PICAMERA = True
    print("[CAMERA] Detected Raspberry Pi Camera Module (picamera2)")
except ImportError:
    import cv2
    print("[CAMERA] picamera2 not found; using OpenCV (cv2) for USB Webcam")


PAGE = """\
<html>
<head><title>Raspberry Pi Live Stream</title></head>
<body style="background:#111;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
<img src="stream.mjpg" style="max-width:100%;max-height:100%;border-radius:8px;" />
</body>
</html>
"""


class StreamingOutput(object):
    def __init__(self):
        self.frame = None

    def set_frame(self, frame_bytes):
        self.frame = frame_bytes


output = StreamingOutput()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    frame = output.frame
                    if frame is not None:
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                    time.sleep(0.04)  # ~25 FPS
            except Exception as e:
                pass
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def capture_loop():
    import threading

    def worker():
        if USE_PICAMERA:
            picam2 = Picamera2()
            config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
            picam2.configure(config)
            picam2.start()
            import cv2
            while True:
                img = picam2.capture_array()
                # Encode as JPEG
                ret, jpeg = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if ret:
                    output.set_frame(jpeg.tobytes())
                time.sleep(0.03)
        else:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)

            while True:
                success, frame = cap.read()
                if success:
                    ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    if ret:
                        output.set_frame(jpeg.tobytes())
                time.sleep(0.03)

    t = threading.Thread(target=worker, daemon=True)
    t.start()


if __name__ == '__main__':
    capture_loop()
    address = ('0.0.0.0', PORT)
    server = StreamingServer(address, StreamingHandler)
    print(f"[STREAM] Camera stream running at: http://0.0.0.0:{PORT}/stream.mjpg")
    print(f"[STREAM] View in browser at: http://<RASPBERRY_PI_IP>:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping camera stream...")

