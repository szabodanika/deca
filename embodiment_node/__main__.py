import sys
sys.path.append('../')
from flask import Flask
import threading
from common.util import generate_id, current_time_in_ms
import subprocess
import requests
from flask import request
from flask import Flask
import setproctitle
import time
import common.system_constants as system_constants
import random

# constants
HOST = "0.0.0.0"
PORT = ""

CAPABILITIES = []

node_id = -1
ca_node = {}
resource_registry = {}
mutex_timestamp = None

# Flask app required for listening to incoming HTTP requests
app = Flask(__name__)

def main(args):
    try:
        global PORT
        global CAPABILITIES

        setproctitle.setproctitle(f'DECA - E NODE {node_id} (Python)')

        PORT = args[1]
        CAPABILITIES = args[3:]
        print(f'[E NODE {node_id}] Starting on {HOST}:{PORT} with capabilities {CAPABILITIES}')
            
        # 1. send service_request
        service_request()

        # 2. contact assigned CA server
        ca_handshake()

        # 3. begin using CA based on provided simulated behaviour
        sim_behaviour()

        # 4. tell CA that we're done
        disconnect_from_ca()
    except KeyboardInterrupt:
        sys.exit(1)
 
def listen() -> None:
    # remove most of the annoying flask logs
    import logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    log.setLevel(logging.ERROR)
    app.logger.disabled = True

    # This is where the mutex requests come in
    @app.route("/mutex")
    def mutex():
        global mutex_timestamp
        incoming_timestamp = request.json

        if(mutex_timestamp != None):
            if(mutex_timestamp['id'] == incoming_timestamp['id']):
                if(mutex_timestamp['time'] <= incoming_timestamp['time']):
                    # wait until our mutex lock is not needed anymore
                    while(mutex_timestamp != None):
                        # prevent going bananas on the cpu
                        time.sleep(1)

        return {
            'response': 'ok'
        }
    
    @app.route("/shutdown")
    def shutdown():
        exit()

    app.run(port=PORT)
    
    return


def service_request() -> None:
    global node_id
    global ca_node
    global resource_registry

    url = f"http://{system_constants.SS_HOST}:{system_constants.SS_PORT}/service_request"
    response = requests.get(url, json={
        'host' : HOST,
        'port' : PORT
    })

    # Check if the request was successful
    if response.status_code == 200:
        # Extract the new_node_id from the response JSON
        node_id = response.json()['id']
        ca_host = response.json()['host']
        ca_port = response.json()['port']
        resource_registry = response.json()['resource_registry']
        
        setproctitle.setproctitle(f'DECA - E NODE {node_id} (Python)')

        ca_node = {
            'host': ca_host,
            'port': ca_port,
        }

        print(f'[E NODE {node_id}] received node ID from SS: {node_id}')
        print(f'[E NODE {node_id}] received assigned CA\'s address from SS: {ca_host}:{ca_port}')
    else:
        print(f'[E NODE {node_id}] Request service_request failed with status code:', response.status_code)
    return


def ca_handshake():
    global ca_node
    print(f'[E NODE {node_id}] initiating handshake with CA {ca_node}')
    url = f"http://{ca_node['host']}:{ca_node['port']}/handshake"
    response = requests.get(url, json={
        'capabilities': CAPABILITIES,
        'host': HOST,
        'port': PORT,
        'id': node_id,
    })

    # Check if the request was successful
    if response.status_code == 200:
        ca_node['id'] = response.json()['id']
        print(f'[E NODE {node_id}] handshake done with CA {ca_node["id"]}')
    else:
        print(f'[E NODE {node_id}] Request ca_handshake failed with status code:', response.status_code)
    
    return 


def update_registry() -> None:
    global node_registry
    global resource_registry
    url = f"http://{system_constants.SS_HOST}:{system_constants.SS_PORT}/get_nodes"
    response = requests.get(url, json={})
    # Check if the request was successful
    if response.status_code == 200:
        # Extract the new_node_id from the response JSON
        node_registry = response.json()['ca_registry']
        resource_registry = response.json()['resource_registry']
    else:
        print(f'[CA NODE {node_id}] Request update_registry failed with status code:', response.status_code)
    return

def send_user_input(input: str):
    global ca_node
    url = f"http://{ca_node['host']}:{ca_node['port']}/user_input"
    response = requests.get(url, json={
        'input': input,
    })

    # Check if the request was successful
    if response.status_code == 200:
        print(f'[E NODE {node_id}] exchange with CA {ca_node["id"]}: IN: {input}   OUT: {response.json()}')
        return response.json()
    else:
        print(f'[E NODE {node_id}] Request failed with status code:', response.status_code)
    

    return 

# Tell CA that they can go back to idle state because we're done here
def disconnect_from_ca():
    global ca_node
    url = f"http://{ca_node['host']}:{ca_node['port']}/goodbye"
    response = requests.get(url, json={})

    # Check if the request was successful
    if response.status_code == 200:
        print(f'[E NODE {node_id}] disconnected from CA {ca_node["id"]}')
    else:
        print(f'[E NODE {node_id}] Request failed with status code:', response.status_code)
    
    ca_node = {}

    return 
   
# SIMULATED USER BEHAVIOUR
# Because we don't have actual people to use the embodiments, they will be programmed to behave a certain way.
def sim_behaviour():
    for _ in range (3):
        time.sleep(random.randint(0,5) / 10)

        if(random.randint(0,1) == 1):
            send_user_input('Hello!')

        time.sleep(random.randint(0,5) / 10)

        if(random.randint(0,1) == 1):
            send_user_input('How are you?')

    pass

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])