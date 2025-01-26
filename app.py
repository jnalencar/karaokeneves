import subprocess
import os

def start_service(service_name, script_name):
    service_path = os.path.join('services', service_name, script_name)
    return subprocess.Popen(['python', service_path])

if __name__ == '__main__':
    services = [
        ('web_interface', 'main.py'),
        ('music_queue', 'main.py'),
        ('video_player', 'main.py'),
        ('entry_screen', 'main.py')
    ]

    processes = []
    for service_name, script_name in services:
        process = start_service(service_name, script_name)
        processes.append(process)

    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()