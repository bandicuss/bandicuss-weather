"""Non-interactive checks for Pixel startup integration and terminal safety."""
import io
import os
import re
import unittest
from unittest.mock import Mock, patch

import bandicuss_intro as intro
import weather


class IntroTests(unittest.TestCase):
    def test_frames_fit_fullscreen_without_wrapping(self):
        escape = re.compile(r'\x1b\[([0-9;]*)([A-Za-z])')
        for columns, rows in [(79, 24), (97, 27), (158, 40)]:
            for seconds in (0, 0.95, 2, 4, 6, 7.9):
                pixels, scene = intro.frame_at(seconds)
                frame = intro.ansi_frame(pixels, scene, columns, rows)
                x = y = i = 0
                while i < len(frame):
                    match = escape.match(frame, i)
                    if match:
                        if match[2] == 'H':
                            y, x = (int(v) - 1 for v in match[1].split(';'))
                        i = match.end()
                        continue
                    self.assertTrue(0 <= x < columns - 1)
                    self.assertTrue(0 <= y < rows)
                    x += 1
                    i += 1

    def test_redirected_output_skips(self):
        output = io.StringIO()
        with patch.object(intro.sys, 'stdout', output):
            intro.play_intro()
        self.assertEqual(output.getvalue(), '')

    def test_terminal_cleanup_on_skip_error_and_interrupt(self):
        import select
        import termios
        import tty
        for failure in (None, RuntimeError('render failed'), KeyboardInterrupt()):
            with self.subTest(failure=failure):
                output = io.StringIO()
                output.isatty = lambda: True
                stdin = Mock()
                stdin.isatty.return_value = True
                stdin.fileno.return_value = 123
                with patch.dict(os.environ, {}, clear=True), \
                     patch.object(intro.sys, 'stdout', output), \
                     patch.object(intro.sys, 'stdin', stdin), \
                     patch.object(intro.shutil, 'get_terminal_size', return_value=(97, 27)), \
                     patch.object(termios, 'tcgetattr', return_value=['original']), \
                     patch.object(termios, 'tcsetattr') as restore, \
                     patch.object(termios, 'tcflush') as flush, \
                     patch.object(tty, 'setcbreak'), \
                     patch.object(select, 'select', return_value=([stdin], [], [])), \
                     patch.object(intro.os, 'read', return_value=b' '), \
                     patch.object(intro, 'ansi_frame', side_effect=failure, return_value='frame'):
                    if failure:
                        with self.assertRaises(type(failure)):
                            intro.play_intro()
                    else:
                        intro.play_intro()
                        flush.assert_called_once_with(123, termios.TCIFLUSH)
                    restore.assert_called_once_with(123, termios.TCSADRAIN, ['original'])
                self.assertTrue(output.getvalue().endswith('\x1b[0m\x1b[?25h\x1b[?1049l'))

    def test_animation_failure_does_not_block_station_flow(self):
        events = []
        with patch.object(intro, 'play_intro', side_effect=RuntimeError('failure')), \
             patch.object(weather.console, 'print'), \
             patch.object(weather.console, 'clear'), \
             patch.object(weather, 'draw_startup_screen', side_effect=lambda s: events.append(('selection', s))), \
             patch('builtins.input', return_value='kbwi'), \
             patch.object(weather, 'weather_menu', side_effect=lambda s: events.append(('weather', s))):
            weather.main()
        self.assertEqual(events, [('selection', weather.DEFAULT_STATION), ('weather', 'KBWI')])

    def test_startup_uses_pixel_and_preserves_interrupt(self):
        with patch.object(intro, 'play_intro') as play:
            weather.startup_animation()
            play.assert_called_once_with()
        with patch.object(intro, 'play_intro', side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                weather.startup_animation()


if __name__ == '__main__':
    unittest.main()
