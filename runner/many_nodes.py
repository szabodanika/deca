import subprocess
import signal
import os
import time
import atexit
import setproctitle
import sys

try:
    STARTING_PORT = 25565
    SS_HOST = '0.0.0.0'

    # Be careful with scale above 10
    SCALE = 2

    # Based on initial testing, less than 50ms leads to errors already -> nodes need time to start up
    SLEEP_BETWEEN_STEPS_MS = 200

    RESOURCE_TYPE_1_COUNT = 2 * SCALE
    RESOURCE_TYPE_2_COUNT = 2 * SCALE
    EMBODIMENT_TYPE_1_COUNT = 3 * SCALE
    EMBODIMENT_TYPE_2_COUNT = 3 * SCALE
    SS_CAPACITY = 20 * SCALE
    SS_MIN_STANDBY_CA = 4 * SCALE
    SS_INCREMENTS = 4 * SCALE
    MIN_IDLE_CA = 2 * SCALE


    setproctitle.setproctitle(f'DECA - runner (Python)')

    # 0. clear terminal
    os.system('clear')
    
    print(f'[RUNNER] Starting... Press CTRL + C to terminate all processes.')

    time.sleep(1)
    

    # 1. begin starting up nodes
    processes = []


    super_server = [
        "python",
        "../super_server/__main__.py",
        "--host",
        SS_HOST,
        "--port",
        str(STARTING_PORT),
        "--capacity",
        str(SS_CAPACITY),
        "--min_standby_ca",
        str(SS_MIN_STANDBY_CA),
        "--ca_increments",
        str(SS_INCREMENTS),
        "--min_idle_ca",
        str(MIN_IDLE_CA),
        ]
    
    processes.append(('Super Server', subprocess.Popen(super_server)))

    # lets give some time for the SS to set up
    time.sleep(SLEEP_BETWEEN_STEPS_MS/1000)
    print("##########################################################")
    print("############## FINISHED STARTING UP SS, STARTING UP RESOURCES NEXT")
    print("##########################################################")
    # remember that SS will use up this many ports
    STARTING_PORT += SS_CAPACITY

    # start resources
    for i in range(RESOURCE_TYPE_1_COUNT):
        STARTING_PORT += 1
        time.sleep(SLEEP_BETWEEN_STEPS_MS/1000)
        print("############## STARTING RESOURCE TYPE 1, INSTANCE " ,i)

        resource1 = [
            "python",
            "../resource_node/__main__.py",
            "--port",
            str(STARTING_PORT),
            "--name",
            f'Thermometer {i}',
            "--capability",
            "sensor_read"
        ]
        processes.append(("Resource Type1 " + str(i), subprocess.Popen(resource1)))

    for i in range(RESOURCE_TYPE_2_COUNT):
        STARTING_PORT += 1
        time.sleep(SLEEP_BETWEEN_STEPS_MS/1000)
        print("############## STARTING RESOURCE TYPE 2, INSTANCE " ,i)

        resource2 = [
            "python",
            "../resource_node/__main__.py",
            "--port",
            str(STARTING_PORT),
            "--name",
            f'Lamp {i}',
            "--capability",
            "actuator_switch"
            ]
        processes.append(("Resource Type1 " + str(i), subprocess.Popen(resource2)))

    time.sleep(SLEEP_BETWEEN_STEPS_MS/1000)
    print("##########################################################")
    print("############## FINISHED STARTING UP RESOURCES, STARTING UP EMBODIMENTS NEXT")
    print("##########################################################")

    for i in range(EMBODIMENT_TYPE_1_COUNT):
        STARTING_PORT += 1
        time.sleep(SLEEP_BETWEEN_STEPS_MS/1000)
        print("############## STARTING EMBODIMENT TYPE 1, INSTANCE " ,i)

        embodiment1 = [
            "python",
            "../embodiment_node/__main__.py",
            "--port",
            str(STARTING_PORT),
            "--capabilities",
            "text_in",
            "text_out",
        ]
        processes.append(("Embodiment Type1 " + str(i), subprocess.Popen(embodiment1)))

    for i in range(EMBODIMENT_TYPE_2_COUNT):
        STARTING_PORT += 1
        time.sleep(SLEEP_BETWEEN_STEPS_MS/1000)
        print("############## STARTING EMBODIMENT TYPE 2, INSTANCE " ,i)

        embodiment2 = [
            "python",
            "../embodiment_node/__main__.py",
            "--port",
            str(STARTING_PORT),
            "--capabilities",
            "text_in",
            "text_out",
            "image_out",
            ]
        processes.append(("Embodiment Type2 " + str(i), subprocess.Popen(embodiment2)))

    # def exit_handler():
    #     for name, p in processes:
    #         print(f'[RUNNER] Terminating {name}')
    #         p.terminate()

    # atexit.register(exit_handler)

    while(True):
        time.sleep(60)

except KeyboardInterrupt:
        sys.exit(1)