import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')

SERVICES = (
    ('music_queue', 'main.py'),
    ('video_player', 'main.py'),
    ('web_interface', 'main.py'),
    ('entry_screen', 'main.py'),
)


def start_service(service_name, script_name):
    service_path = ROOT / 'services' / service_name / script_name
    if not service_path.is_file():
        raise FileNotFoundError(f'Serviço não encontrado: {service_path}')
    process_options = {}
    if os.name == 'nt':
        process_options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(
        [sys.executable, '-m', f'services.{service_name}.main'],
        cwd=ROOT,
        **process_options,
    )


def stop_services(processes):
    for process in reversed(processes):
        if process.poll() is None:
            if os.name == 'nt':
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                except OSError:
                    process.terminate()
            else:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    processes = []
    try:
        for service_name, script_name in SERVICES:
            process = start_service(service_name, script_name)
            processes.append(process)
            print(f'Serviço iniciado: {service_name}', flush=True)

        while True:
            for (service_name, _), process in zip(SERVICES, processes):
                exit_code = process.poll()
                if exit_code is not None:
                    print(
                        f'O serviço {service_name} foi encerrado '
                        f'(código {exit_code}).',
                        file=sys.stderr,
                    )
                    return 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('\nEncerrando o karaokê...')
        return 0
    finally:
        stop_services(processes)


if __name__ == '__main__':
    raise SystemExit(main())
