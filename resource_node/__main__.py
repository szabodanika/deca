import sys
sys.path.append('../')
from flask import Flask
from flask import request
import threading
from common.util import generate_id
import subprocess
import requests
import random
import time
import setproctitle
import common.system_constants as system_constants

HOST = "0.0.0.0"
PORT = 0
NAME = ""
CAPABILITIES = {}
SIMULATED_DELAY_MS = 500

node_id = -1

# Flask app required for listening to incoming HTTP requests
app = Flask(__name__)

# simulated states
sim_state = {
    'switch' : False,
    'sensor' : random.randint(19,24)
}

def main(args):
    try:
        global PORT
        global NAME
        global CAPABILITIES

        setproctitle.setproctitle(f'DECA - SA NODE {node_id} (Python)')

        PORT = args[1]
        NAME = args[3]
        CAPABILITIES = [args[5]]
        print(f'[SA NODE {node_id}] {NAME} starting on {HOST}:{PORT} with capabilities {CAPABILITIES}')

        # 1. start listening
        listening_thread = threading.Thread(target=listen)
        listening_thread.start()
        
        
        # 2. super server callback
        ss_callback_thread = threading.Thread(target=ss_callback)
        ss_callback_thread.start()
    except KeyboardInterrupt:
        sys.exit(1)
    
def listen() -> None:
    global switch_on
    global sensor_reading
    # remove most of the annoying flask logs
    import logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    log.setLevel(logging.ERROR)
    app.logger.disabled = True

    @app.route("/shutdown")
    def shutdown():
        exit()

    @app.route("/sensor_read")
    def sensor_read():
        print(f'[SA NODE {node_id}] {NAME} performing sensor_read')
        time.sleep(SIMULATED_DELAY_MS/1000) 
        return {
            'value' : sim_state['sensor']
        }
    
    @app.route("/actuator_switch")
    def actuator_switch():
        time.sleep(SIMULATED_DELAY_MS/1000) 
        data = request.json
        print(f'[SA NODE {node_id}] {NAME} performing actuator_switch => {data["actuator_switch"]}')

        sim_state['switch'] = data['actuator_switch']
        return {
            'value' : sim_state['switch']
        }

    app.run(port=PORT)
    
    return

    
def ss_callback() -> None:
    global node_id
    url = f"http://{system_constants.SS_HOST}:{system_constants.SS_PORT}/register_resource"
    response = requests.get(url, json={
        'host' : HOST,
        'port' : PORT,
        'capabilities' : CAPABILITIES,
        'name' : NAME
    })


    # Check if the request was successful
    if response.status_code == 200:
        # Extract the new_node_id from the response JSON
        node_id = response.json()['new_node_id']
        setproctitle.setproctitle(f'DECA - SA NODE {node_id} (Python)')
        print(f'[SA NODE {node_id}] received node ID from SS: {node_id}')
    else:
        print("[SA NODE {node_id}] Request failed with status code:", response.status_code)
    return
   

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])