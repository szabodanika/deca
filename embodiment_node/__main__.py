import sys
sys.path.append('../')
from flask import Flask
import threading
from common.util import generate_id
import subprocess
import requests
from flask import request
from flask import Flask

# constants
HOST = "0.0.0.0"
SS_HOST = "0.0.0.0"
SS_PORT = "8000"

CAPABILITIES = [
        # can read text in from user
        'text_in',
        # can display text
        'text_out',
]

node_id = -1
ca_node = {}
resource_registry = {}


# Flask app required for listening to incoming HTTP requests
app = Flask(__name__)

def main(args):
    global PORT
    PORT = args[1]
    print(f'[E NODE {node_id}] Starting on {HOST}:{PORT}')
        
    # 1. send service_request
    service_request()

    # 2. contact assigned CA server
    ca_handshake()

    # 3. begin using CA based on provided simulated behaviour
    sim_behaviour()

    # 4. tell CA that we're done
    disconnect_from_ca()
 
def listen() -> None:
    # remove most of the annoying flask logs
    import logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    log.setLevel(logging.ERROR)
    app.logger.disabled = True

    @app.route("/shutdown")
    def shutdown():
        exit()

    app.run(port=PORT)
    
    return


def service_request() -> None:
    global node_id
    global ca_node
    global resource_registry

    url = f"http://{SS_HOST}:8000/service_request"
    response = requests.get(url, json={})

    # Check if the request was successful
    if response.status_code == 200:
        # Extract the new_node_id from the response JSON
        node_id = response.json()['id']
        ca_host = response.json()['host']
        ca_port = response.json()['port']
        resource_registry = response.json()['resource_registry']
        
        ca_node = {
            'host': ca_host,
            'port': ca_port,
        }

        print(f'[E NODE {node_id}] received node ID from SS: {node_id}')
        print(f'[E NODE {node_id}] received assigned CA\'s address from SS: {ca_host}:{ca_port}')
    else:
        print(f'[E NODE {node_id}] Request failed with status code:', response.status_code)
    return


def ca_handshake():
    global ca_node
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
        print(f'[E NODE {node_id}] Request failed with status code:', response.status_code)
    
    return 

# Because we don't have actual people to use the embodiments, they will be programmed to behave a certain way.
def sim_behaviour():
    global ca_node
    pass

# Tell CA that they can go back to idle state because we're done here
def disconnect_from_ca():
    global ca_node
    pass
   

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])