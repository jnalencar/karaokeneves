import unittest
from unittest.mock import patch

import app


class ApplicationSupervisorTests(unittest.TestCase):
    @patch('app.subprocess.Popen')
    def test_start_service_uses_project_module_and_active_python(self, popen):
        process = object()
        popen.return_value = process

        result = app.start_service('music_queue', 'main.py')

        self.assertIs(result, process)
        expected_options = {}
        if app.os.name == 'nt':
            expected_options['creationflags'] = (
                app.subprocess.CREATE_NEW_PROCESS_GROUP
            )
        popen.assert_called_once_with(
            [app.sys.executable, '-m', 'services.music_queue.main'],
            cwd=app.ROOT,
            **expected_options,
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

        self.assertTrue(all(
            process.send_signal.called or process.terminate.called
            for process in processes[1:]
        ))

    def test_missing_service_fails_explicitly(self):
        with self.assertRaises(FileNotFoundError):
            app.start_service('missing', 'main.py')


if __name__ == '__main__':
    unittest.main()
