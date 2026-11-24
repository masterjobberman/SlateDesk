"""Thread-safe transfer telemetry. GPL-2.0-or-later."""
import threading
import time
from collections import deque

class Progress:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            now = self.clock()
            self.state = dict(stage='Ready', detail='Choose your Slate to get started.',
                              connected=False, battery=None, page=0, total=0, received=0,
                              completed=0, advertised=None, started=now, page_started=now,
                              last_data=None, active=False, finished=None, saved=None)
            self.samples = deque()

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def begin_page(self, number, total, advertised=None):
        with self.lock:
            self.state.update(page=number, total=total, received=0, advertised=advertised,
                              page_started=self.clock(), last_data=None)
            self.samples.clear()

    def receive(self, count):
        with self.lock:
            now = self.clock()
            self.state['received'] += count
            self.state['last_data'] = now
            self.samples.append((now, count))
            while self.samples and self.samples[0][0] < now - 5:
                self.samples.popleft()

    def snapshot(self):
        with self.lock:
            s = self.state.copy()
            now = s['finished'] if s['finished'] is not None else self.clock()
            s['elapsed'] = max(0, now - s['started'])
            s['idle'] = max(0, now - (s['last_data'] or s['page_started']))
            s['speed'] = sum(n for t,n in self.samples if t >= now-5) / max(.25,min(5,now-s['page_started']))
            s['stalled'] = s['active'] and s['stage']=='Receiving ink' and s['idle'] >= 5
            # GET_STROKES count is described inconsistently upstream. Never infer a percent.
            s['percent'] = None
            return s

class CancelledError(RuntimeError):
    pass
