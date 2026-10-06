"""Offline acquisition, approved artwork, worker isolation, and terminal checks."""
import io
import re
import sys
import threading
import unittest
from unittest.mock import Mock, patch

import bandicuss_acquisition as acquisition
import bandicuss_horizon as horizon
import weather

METAR = {'lat': 38.85, 'lon': -77.04, 'rawOb': 'test METAR'}
TAF = {'rawTAF': 'test TAF'}


class RecordingRenderer:
    def __init__(self, station):
        self.station = station
        self.states = []
        self.closed = False
        self.threads = []

    def open(self):
        self.threads.append(threading.get_ident())

    def draw(self, state):
        self.threads.append(threading.get_ident())
        self.states.append(state)

    def close(self):
        self.threads.append(threading.get_ident())
        self.closed = True


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.no_network = patch('urllib.request.urlopen', side_effect=AssertionError('Live network forbidden'))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)


class AcquisitionTests(OfflineTests):
    def run_flow(self, metar=METAR, taf=TAF, alerts=(), include_alerts=True):
        order = []
        worker_threads = []
        renderer = RecordingRenderer('KDCA')
        def operation(name, value):
            def call(*args):
                order.append(name)
                worker_threads.append(threading.get_ident())
                if isinstance(value, BaseException):
                    raise value
                return value
            return call
        output = io.StringIO()
        with patch.object(acquisition, '_animation_enabled', return_value=True), \
             patch.object(acquisition, 'TerminalRenderer', return_value=renderer), \
             patch.object(weather, 'fetch_metar', side_effect=operation('metar', metar)), \
             patch.object(weather, 'fetch_taf', side_effect=operation('taf', taf)), \
             patch.object(weather, 'fetch_nws_alerts', side_effect=operation('alerts', alerts)), \
             patch.object(weather, 'pause') as pause, \
             patch('sys.stdout', output):
            result = weather.load_station('KDCA', include_alerts=include_alerts)
        self.assertTrue(renderer.closed)
        self.assertTrue(all(t == threading.get_ident() for t in renderer.threads))
        self.assertTrue(all(t != threading.get_ident() for t in worker_threads))
        self.assertEqual(pause.call_count, int(metar is None or isinstance(metar, Exception)))
        return result, renderer.states, order, output.getvalue()

    def test_success_order_events_and_data(self):
        alerts = [{'properties': {'event': 'test'}}]
        result, states, order, output = self.run_flow(alerts=alerts)
        self.assertEqual(order, ['metar', 'taf', 'alerts'])
        self.assertEqual(result, (METAR, TAF, 1, alerts))
        self.assertIs(result[0], METAR)
        self.assertIs(result[1], TAF)
        self.assertIs(result[3], alerts)
        self.assertEqual(states, [
            ('PENDING', 'PENDING', 'PENDING'),
            ('ACQUIRING', 'PENDING', 'PENDING'),
            ('ACQUIRED', 'PENDING', 'PENDING'),
            ('ACQUIRED', 'ACQUIRING', 'PENDING'),
            ('ACQUIRED', 'ACQUIRED', 'PENDING'),
            ('ACQUIRED', 'ACQUIRED', 'CHECKING'),
            ('ACQUIRED', 'ACQUIRED', 'CHECKED')])
        self.assertEqual(output, '')

    def test_zero_alerts_is_checked(self):
        result, states, order, _ = self.run_flow(alerts=[])
        self.assertEqual(result, (METAR, TAF, 0, []))
        self.assertEqual(states[-1], ('ACQUIRED', 'ACQUIRED', 'CHECKED'))

    def test_optional_unavailable_and_failure_continue(self):
        for taf, alerts, expected in (
            (None, [], ('ACQUIRED', 'UNAVAILABLE', 'CHECKED')),
            (TimeoutError('taf timeout'), [], ('ACQUIRED', 'FAILED', 'CHECKED')),
            (TAF, TimeoutError('nws timeout'), ('ACQUIRED', 'ACQUIRED', 'FAILED')),
            (None, ValueError('invalid json'), ('ACQUIRED', 'UNAVAILABLE', 'FAILED')),
        ):
            with self.subTest(expected=expected):
                result, states, order, _ = self.run_flow(taf=taf, alerts=alerts)
                self.assertEqual(order, ['metar', 'taf', 'alerts'])
                self.assertEqual(states[-1], expected)
                self.assertIs(result[0], METAR)
                self.assertEqual(result[1], None if taf is None or isinstance(taf, Exception) else TAF)
                self.assertEqual(result[2:], (None, []) if isinstance(alerts, Exception) else (0, []))

    def test_metar_failure_or_unavailable_skips_following_products(self):
        for metar, status, message in (
            (None, 'UNAVAILABLE', 'No METAR data found for KDCA.'),
            (TimeoutError('metar timeout'), 'FAILED', 'Unable to retrieve METAR data.'),
        ):
            with self.subTest(status=status):
                result, states, order, output = self.run_flow(metar=metar)
                self.assertEqual(result, (None, None, None, []))
                self.assertEqual(order, ['metar'])
                self.assertEqual(states[-1], (status, 'SKIPPED', 'SKIPPED'))
                self.assertIn(message, output)
                if status == 'FAILED':
                    self.assertIn('metar timeout', output)

    def test_missing_coordinates_skips_alert_request(self):
        for metar in ({}, {'lat': None, 'lon': 0}, {'lat': 0}):
            result, states, order, _ = self.run_flow(metar=metar)
            self.assertEqual(order, ['metar', 'taf'])
            self.assertEqual(states[-1], ('ACQUIRED', 'ACQUIRED', 'SKIPPED'))
            self.assertEqual(result, (metar, TAF, None, []))

    def test_legacy_two_item_return_and_alert_count(self):
        result, states, order, _ = self.run_flow(include_alerts=False)
        self.assertEqual(result, (METAR, TAF))
        self.assertEqual(order, ['metar', 'taf'])
        with patch.object(weather, 'fetch_nws_alerts', return_value=[]):
            self.assertEqual(weather.get_alert_count(METAR), (0, []))
        with patch.object(weather, 'fetch_nws_alerts', side_effect=TimeoutError()):
            self.assertEqual(weather.get_alert_count(METAR), (None, []))

    def test_existing_request_timeouts_and_parsing_unchanged(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'[{"rawOb": "test"}]'
        with patch('urllib.request.urlopen', return_value=response) as urlopen:
            self.assertEqual(weather.fetch_metar('KDCA'), {'rawOb': 'test'})
            self.assertEqual(urlopen.call_args.kwargs['timeout'], 12)
            weather.fetch_taf('KDCA')
            self.assertEqual(urlopen.call_args.kwargs['timeout'], 12)
            response.read.return_value = b'{"features": []}'
            self.assertEqual(weather.fetch_nws_alerts(38.85, -77.04), [])
            self.assertEqual(urlopen.call_args.kwargs['timeout'], 15)

    def test_dashboard_refresh_and_station_change_preserve_data(self):
        second = {'lat': 1, 'lon': 2}
        third = {'lat': 3, 'lon': 4}
        loads = [(METAR, TAF, 0, []), (second, None, None, []), (third, TAF, 1, ['alert'])]
        with patch.object(weather, 'load_station', side_effect=loads) as load, \
             patch.object(weather, 'draw_v4_dashboard') as draw, \
             patch('builtins.input', side_effect=['r', 's', 'kbwi', 'q']):
            self.assertEqual(weather.weather_menu('KDCA'), 'KBWI')
        self.assertEqual([c.args for c in load.call_args_list], [('KDCA',), ('KDCA',), ('KBWI',)])
        self.assertTrue(all(c.kwargs == {'include_alerts': True} for c in load.call_args_list))
        self.assertEqual([c.args for c in draw.call_args_list], [('KDCA', METAR, 0), ('KDCA', second, None), ('KBWI', third, 1)])

    def test_failed_refresh_or_change_keeps_existing_dashboard(self):
        for commands in (['r', 'q'], ['s', 'KXXX', 'q']):
            with self.subTest(commands=commands), \
                 patch.object(weather, 'load_station', side_effect=[(METAR, TAF, 0, []), (None, None, None, [])]), \
                 patch.object(weather, 'draw_v4_dashboard') as draw, \
                 patch('builtins.input', side_effect=commands):
                self.assertEqual(weather.weather_menu('KDCA'), 'KDCA')
                self.assertEqual([c.args for c in draw.call_args_list], [('KDCA', METAR, 0)] * 2)


class WorkerSafetyTests(OfflineTests):
    def test_animation_continues_during_blocked_request(self):
        entered = threading.Event()
        release = threading.Event()
        renderer = RecordingRenderer('KDCA')
        original_draw = renderer.draw
        def draw(state):
            original_draw(state)
            if entered.is_set() and len(renderer.states) >= 5:
                release.set()
        renderer.draw = draw
        def acquire(report):
            report(0, 'ACQUIRING')
            entered.set()
            if not release.wait(3):
                raise AssertionError('Animation froze during request')
            report(0, 'ACQUIRED')
            return 'data'
        with patch.object(acquisition, '_animation_enabled', return_value=True), \
             patch.object(acquisition, 'TerminalRenderer', return_value=renderer):
            self.assertEqual(acquisition.run_acquisition('KDCA', acquire), 'data')
        self.assertGreaterEqual(renderer.states.count(('ACQUIRING', 'PENDING', 'PENDING')), 3)
        self.assertTrue(renderer.closed)

    def test_renderer_failures_do_not_repeat_or_break_acquisition(self):
        for method in ('open', 'draw', 'close'):
            with self.subTest(method=method):
                renderer = RecordingRenderer('KDCA')
                setattr(renderer, method, Mock(side_effect=RuntimeError('renderer failed')))
                calls = []
                def acquire(report):
                    calls.append('request')
                    report(0, 'ACQUIRED')
                    return 'weather'
                with patch.object(acquisition, '_animation_enabled', return_value=True), \
                     patch.object(acquisition, 'TerminalRenderer', return_value=renderer), \
                     patch('sys.stdout', io.StringIO()):
                    self.assertEqual(acquisition.run_acquisition('KDCA', acquire), 'weather')
                self.assertEqual(calls, ['request'])

    def test_renderer_import_failure_falls_back(self):
        with patch.object(acquisition, '_animation_enabled', return_value=True), \
             patch.object(acquisition, 'TerminalRenderer', side_effect=ImportError('missing artwork')), \
             patch('sys.stdout', io.StringIO()):
            self.assertEqual(acquisition.run_acquisition('KDCA', lambda report: 'weather'), 'weather')

    def test_missing_runner_module_preserves_weather_acquisition(self):
        with patch.dict(sys.modules, {'bandicuss_acquisition': None}), \
             patch.object(weather, 'fetch_metar', return_value=METAR), \
             patch.object(weather, 'fetch_taf', return_value=TAF), \
             patch.object(weather, 'fetch_nws_alerts', return_value=[]):
            self.assertEqual(weather.load_station('KDCA', include_alerts=True), (METAR, TAF, 0, []))

    def test_completion_does_not_depend_on_clock_or_minimum_duration(self):
        renderer = RecordingRenderer('KDCA')
        def acquire(report):
            for index in range(3):
                report(index, 'CHECKED' if index == 2 else 'ACQUIRED')
            return 'weather'
        with patch.object(acquisition, '_animation_enabled', return_value=True), \
             patch.object(acquisition, 'TerminalRenderer', return_value=renderer), \
             patch.object(acquisition.time, 'monotonic', return_value=0):
            self.assertEqual(acquisition.run_acquisition('KDCA', acquire), 'weather')
        self.assertEqual(renderer.states[-1], ('ACQUIRED', 'ACQUIRED', 'CHECKED'))

    def test_worker_exception_propagates_after_cleanup(self):
        renderer = RecordingRenderer('KDCA')
        def fail(report):
            raise RuntimeError('worker failed')
        with patch.object(acquisition, '_animation_enabled', return_value=True), \
             patch.object(acquisition, 'TerminalRenderer', return_value=renderer):
            with self.assertRaisesRegex(RuntimeError, 'worker failed'):
                acquisition.run_acquisition('KDCA', fail)
        self.assertTrue(renderer.closed)

    def test_interrupt_restores_terminal_and_cancels_later_requests(self):
        blocked = threading.Event()
        release = threading.Event()
        stopped = threading.Event()
        renderer = RecordingRenderer('KDCA')
        calls = []
        def draw(state):
            renderer.states.append(state)
            if blocked.is_set():
                raise KeyboardInterrupt()
        renderer.draw = draw
        def acquire(report):
            try:
                report(0, 'ACQUIRING')
                calls.append('metar')
                blocked.set()
                if not release.wait(3):
                    raise AssertionError('Test did not release request')
                report(0, 'ACQUIRED')
                calls.append('taf')
            finally:
                stopped.set()
        try:
            with patch.object(acquisition, '_animation_enabled', return_value=True), \
                 patch.object(acquisition, 'TerminalRenderer', return_value=renderer):
                with self.assertRaises(KeyboardInterrupt):
                    acquisition.run_acquisition('KDCA', acquire)
        finally:
            release.set()
        self.assertTrue(stopped.wait(3))
        self.assertEqual(calls, ['metar'])
        self.assertTrue(renderer.closed)

    def test_terminal_writes_only_on_main_and_cleanup_after_frame_error(self):
        class Output(io.StringIO):
            def __init__(self):
                super().__init__()
                self.threads = []
            def write(self, value):
                self.threads.append(threading.get_ident())
                return super().write(value)
        for failure in (None, RuntimeError('bad frame')):
            output = Output()
            with self.subTest(failure=failure), \
                 patch.object(acquisition, '_animation_enabled', return_value=True), \
                 patch.object(acquisition.shutil, 'get_terminal_size', return_value=(97, 23)), \
                 patch.object(horizon, 'frame', side_effect=failure, return_value='frame'), \
                 patch('sys.stdout', output):
                self.assertEqual(acquisition.run_acquisition('KDCA', lambda report: 'data'), 'data')
            text = output.getvalue()
            self.assertIn('\x1b[?1049h\x1b[?25l', text)
            self.assertIn('\x1b[0m\x1b[?25h\x1b[?1049l', text)
            self.assertTrue(all(t == threading.get_ident() for t in output.threads))

    def test_disabled_redirected_small_and_dumb_terminals(self):
        stdin, stdout = Mock(), Mock()
        stdin.isatty.return_value = stdout.isatty.return_value = True
        for size, env, tty, expected in (
            ((97, 23), {}, True, True),
            ((96, 23), {}, True, False),
            ((97, 22), {}, True, False),
            ((97, 23), {'NO_COLOR': ''}, True, False),
            ((97, 23), {'BANDICUSS_NO_ANIMATION': '1'}, True, False),
            ((97, 23), {'TERM': 'dumb'}, True, False),
            ((97, 23), {}, False, False),
        ):
            with self.subTest(size=size, env=env, tty=tty), \
                 patch.dict('os.environ', env, clear=True), \
                 patch.object(acquisition.shutil, 'get_terminal_size', return_value=size), \
                 patch('sys.stdin', stdin), patch('sys.stdout', stdout):
                stdout.isatty.return_value = tty
                self.assertEqual(acquisition._animation_enabled(), expected)
        output = io.StringIO()
        with patch.object(acquisition, '_animation_enabled', return_value=False), patch('sys.stdout', output):
            self.assertEqual(acquisition.run_acquisition('KDCA', lambda report: 'weather'), 'weather')
        self.assertIn('METAR: PENDING / TAF: PENDING / NWS ALERTS: PENDING', output.getvalue())
        self.assertNotIn('\x1b', output.getvalue())

    def test_resize_restores_alternate_screen_and_continues(self):
        output = io.StringIO()
        with patch.object(acquisition, '_animation_enabled', return_value=True), \
             patch.object(acquisition.shutil, 'get_terminal_size', side_effect=[(97, 23), (80, 20)]), \
             patch.object(horizon, 'frame', return_value='frame'), patch('sys.stdout', output):
            def acquire(report):
                report(0, 'ACQUIRED')
                return 'weather'
            self.assertEqual(acquisition.run_acquisition('KDCA', acquire), 'weather')
        self.assertIn('\x1b[?1049l', output.getvalue())
        self.assertIn('METAR: ACQUIRED', output.getvalue())


class ArtworkTests(OfflineTests):
    def test_checking_cannot_add_column(self):
        for seconds in (0, 8, 9, 12, 13, 30):
            first = horizon.landscape(seconds, ('ACQUIRED', 'ACQUIRED', 'CHECKING'), receiver=horizon.radar_dish)
            second = horizon.landscape(seconds, ('ACQUIRED', 'ACQUIRED', 'CHECKED'), receiver=horizon.radar_dish)
            self.assertEqual(first, second)

    def test_all_statuses_visible_without_wrapping_at_uconsole_size(self):
        escape = re.compile(r'\x1b\[([0-9;]*)([A-Za-z])')
        for status in horizon.STYLES:
            for station in ('KBWI', 'A' * 200, 'BAD\x1b[2J'):
                rendered = horizon.frame(9, (status,) * 3, station, 97, 23)
                cells = [[' '] * 97 for _ in range(23)]
                x = y = i = 0
                while i < len(rendered):
                    match = escape.match(rendered, i)
                    if match:
                        if match[2] == 'H':
                            y, x = (int(v) - 1 for v in match[1].split(';'))
                        i = match.end()
                        continue
                    self.assertTrue(0 <= x < 96 and 0 <= y < 23, (status, x, y))
                    cells[y][x] = rendered[i]
                    x += 1
                    i += 1
                lines = [''.join(row) for row in cells]
                self.assertIn('METAR', lines[18])
                self.assertIn('TAF', lines[18])
                self.assertIn('NWS ALERTS', lines[18])
                self.assertEqual(lines[19].count(status), 3)
                self.assertNotIn('16 SECOND', rendered)
                self.assertNotIn('DEMO DATA', rendered)


if __name__ == '__main__':
    unittest.main()
