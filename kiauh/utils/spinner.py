import sys
import threading
import time


class Spinner:
    def __init__(self, message="Loading", delay=0.2):
        self.message = f"{message} ..."
        self.delay = delay
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._animate)

    def _animate(self):
        animation = ["◜", "◝", "◞", "◟"]
        while not self._stop_event.is_set():
            for char in animation:
                sys.stdout.write(f"\r{char} {self.message}")
                sys.stdout.flush()
                time.sleep(self.delay)
                if self._stop_event.is_set():
                    break
        sys.stdout.write("\r" + " " * (len(self.message) + 1) + "\r")
        sys.stdout.flush()

    def start(self):
        self._stop_event.clear()
        if not self._thread.is_alive():
            self._thread = threading.Thread(target=self._animate)
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()