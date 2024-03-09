import subprocess
import signal
import os

def main(args):

    processes = []

    super_server = [
        "python",
        "../super_server/__main__.py",
        ]
    processes.append(subprocess.Popen(super_server))

    resource1 = [
        "python",
        "../resource_node/__main__.py",
        ]
    processes.append(subprocess.Popen(resource1))

    resource2 = [
        "python",
        "../resource_node/__main__.py",
        ]
    processes.append(subprocess.Popen(resource2))

    input("press any key to stop")

    for p in processes:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)



if __name__ == '__main__':
    import sys
    main(sys.argv[1:])