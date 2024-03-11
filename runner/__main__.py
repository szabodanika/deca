import subprocess
import signal
import os
import time
def main(args):

    # 0. clear terminal
    os.system('clear')

    # 1. make sure all processes are shut down

    ports = [
        '8000',
        '8001',
        '8002',
        '9000',
        '9001',
        '9002',
        '9003',
        '9004',
    ]

    for p in ports:
        subprocess.Popen([
            "curl",
            f'0.0.0.0:{p}/shutdown',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. start the processes now


    processes = []

    super_server = [
        "python",
        "../super_server/__main__.py",
        "--port",
        "8000"
        ]
    processes.append(subprocess.Popen(super_server))

    # 1000ms delay
    time.sleep(1)

    resource1 = [
        "python",
        "../resource_node/__main__.py",
        "--port",
        "9000",
        "--name",
        "Thermometer",
        "--capability",
        "sensor_read"
        ]
    processes.append(subprocess.Popen(resource1))

    # 1000ms delay
    time.sleep(1)

    resource2 = [
        "python",
        "../resource_node/__main__.py",
        "--port",
        "9001",
        "--name",
        "Lamp",
        "--capability",
        "actuator_switch"
        ]
    processes.append(subprocess.Popen(resource2))

    # 1000ms delay
    time.sleep(1)

    embodiment1 = [
        "python",
        "../embodiment_node/__main__.py",
        "--port",
        "9003",
        ]
    processes.append(subprocess.Popen(embodiment1))

    # 1000ms delay
    time.sleep(1)

    embodiment2 = [
        "python",
        "../embodiment_node/__main__.py",
        "--port",
        "9004",
        ]
    processes.append(subprocess.Popen(embodiment2))

    # 1000ms delay
    time.sleep(1)

    print("press enter to shut down")
    input()

    for p in processes:
        print(f'[RUNNER] terminating process {os.getpgid(p.pid)}')
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)



if __name__ == '__main__':
    import sys
    main(sys.argv[1:])