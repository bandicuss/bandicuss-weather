"""Main-thread acquisition display with an isolated, sequential network worker."""
import os
import queue
import shutil
import sys
import threading
import time

FPS = 12
PRODUCTS = ('METAR', 'TAF', 'NWS ALERTS')


class _Cancelled(BaseException):
    pass


class TerminalRenderer:
    """Own only the alternate screen and cursor; leave input/signal modes intact."""
    def __init__(self, station):
        from bandicuss_horizon import frame
        self.frame = frame
        self.station = station
        self.started = time.monotonic()
        self.active = False

    def open(self):
        self.active = True  # Also restore after a partially written escape sequence.
        sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[2J')
        sys.stdout.flush()

    def draw(self, state):
        columns, rows = shutil.get_terminal_size()
        if columns < 97 or rows < 23:
            raise RuntimeError('Terminal too small for Horizon Observatory')
        sys.stdout.write(self.frame(time.monotonic() - self.started, state,
                                    self.station, columns, rows))
        sys.stdout.flush()

    def close(self):
        if self.active:
            try:
                sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l')
                sys.stdout.flush()
            finally:
                self.active = False


def _animation_enabled():
    columns, rows = shutil.get_terminal_size()
    return (sys.stdout.isatty() and sys.stdin.isatty()
            and columns >= 97 and rows >= 23
            and 'NO_COLOR' not in os.environ
            and not os.environ.get('BANDICUSS_NO_ANIMATION')
            and os.environ.get('TERM') != 'dumb')


def run_acquisition(station, acquire):
    """Call acquire(report) in a worker; render each event and animate while waiting.

    report(index, status) is the worker's only connection to the UI. The worker
    must not print, read input, or manipulate the terminal. No simulated stages,
    request time limits, minimum display time, or additional requests live here.
    Ctrl-C cancels future stages; an in-flight request keeps its existing timeout.
    """
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Acquisition display must run on the main thread')
    events = queue.Queue()
    cancelled = threading.Event()
    renderer = None
    state = ['PENDING'] * 3
    last_text = None

    def report(index, status):
        if cancelled.is_set():
            raise _Cancelled()
        events.put(('status', (index, status)))

    def worker():
        try:
            result = acquire(report)
        except _Cancelled:
            return
        except BaseException as error:
            events.put(('error', error))
        else:
            events.put(('result', result))

    def close_renderer():
        nonlocal renderer
        current, renderer = renderer, None
        if current is not None:
            try:
                current.close()
            except Exception:
                pass  # A broken output stream must not discard weather data.

    def draw():
        nonlocal last_text
        if renderer is not None:
            try:
                renderer.draw(tuple(state))
                return
            except Exception:
                close_renderer()
        snapshot = tuple(state)
        if snapshot != last_text:
            last_text = snapshot
            try:
                print(station + ' / ' + ' / '.join(
                    f'{name}: {status}' for name, status in zip(PRODUCTS, state)))
            except Exception:
                pass

    try:
        try:
            if _animation_enabled():
                renderer = TerminalRenderer(station)
                renderer.open()
        except Exception:
            close_renderer()
        draw()
        threading.Thread(target=worker, name='weather-acquisition', daemon=True).start()
        while True:
            try:
                kind, payload = events.get(timeout=1 / FPS)
            except queue.Empty:
                draw()
                continue
            if kind == 'status':
                index, status = payload
                state[index] = status
                draw()
            elif kind == 'error':
                raise payload
            else:
                return payload
    finally:
        cancelled.set()
        close_renderer()
