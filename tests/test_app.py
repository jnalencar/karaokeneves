import unittest
from pathlib import Path
from unittest.mock import patch

import app


class ApplicationSupervisorTests(unittest.TestCase):
    @patch('app.subprocess.Popen')
    def test_start_service_uses_project_path_and_active_python(self, popen):
        process = object()
        popen.return_value = process
        service_path = Path(app.ROOT) / 'services' / 'music_queue' / 'main.py'

        result = app.start_service('music_queue', 'main.py')

        self.assertIs(result, process)
        popen.assert_called_once_with(
            [app.sys.executable, str(service_path)],
            cwd=app.ROOT,
        )

    @patch('app.time.sleep')
    @patch('app.start_service')
    def test_main_stops_other_services_if_a_service_exits(
        self,
        start_service,
        _sleep,
    ):
        processes = [unittest.mock.Mock() for _ in app.SERVICES]
        for process in processes:
            process.poll.return_value = None
        processes[0].poll.return_value = 2
        start_service.side_effect = processes

        self.assertEqual(app.main(), 1)

        self.assertTrue(all(process.terminate.called for process in processes[1:]))

    def test_missing_service_fails_explicitly(self):
        with self.assertRaises(FileNotFoundError):
            app.start_service('missing', 'main.py')


if __name__ == '__main__':
    unittest.main()
