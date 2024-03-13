import sys
sys.path.append('../')
from flask import Flask
import threading
from common.util import generate_id, current_time_in_ms
import common.system_constants as system_constants
import subprocess
import requests
from flask import Flask, request
import time
import setproctitle
import random

HOST = "0.0.0.0"

PORT = 0

# ms of delay when handling user input
SIMULATED_DELAY_MS = 500

# begin using resources after this many MS 
USE_RESOURCES_DELAY_MS = 5_000

MUTEX_TIMEOUT_MS = 1_000

node_id = -1
embodiment_node = {}
resource_registry = {}
node_registry = {}
mutex_timestamp = None

# Flask app required for listening to incoming HTTP requests
app = Flask(__name__)

# TODO: still not everyone seems to get their mutex locks that try to get it
# also not every node seems to want to perform SA action at the end? like 5/8?

def main(args):
    try:
        global PORT
        PORT = args[3]
        print(f'[CA NODE {node_id}] Starting on {HOST}:{PORT}')
        setproctitle.setproctitle(f'DECA - CA NODE {node_id} (Python)')

        # 1. start listening
        listening_thread = threading.Thread(target=listen)
        listening_thread.start()
        
        # 2. super server callback
        ss_callback()

        # 3. access resource automatically (normally a human would prompt this)
        use_resources_thread = threading.Thread(target=use_resources)
        use_resources_thread.start()
        

    except KeyboardInterrupt:
        sys.exit(1)


def listen() -> None:
    global embodiment_node
    global mutex_timestamp
    global node_id

    # remove most of the annoying flask logs
    import logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    log.setLevel(logging.ERROR)
    app.logger.disabled = True

    # this is where a newly started EN checks in
    @app.route("/handshake")
    def handshake():
        data = request.json


        # Extract the new_node_id from the response JSON
        embodiment_node['id'] = data['id']
        embodiment_node['capabilities'] = data['capabilities']
        embodiment_node['host'] = data['host']
        embodiment_node['port'] = data['port']

        print(f'[CA NODE {node_id}] hands shaken with {embodiment_node}')
        

        return {
            'id': node_id
        }
    
     
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
                        # print(f'[CA NODE {node_id}] still locked on {mutex_timestamp["id"]}, sorry!')
                        # prevent going bananas on the cpu
                        time.sleep(1)

        return {
            'response': 'ok'
        }
    
    # this is where the embodiment sends the user input
    @app.route("/user_input")
    def user_input():
        data = request.json

        response = handle_user_input(data['input'])      

        return response
    
    # this is where the EN says they don't need this CA anymore and we can go back to idle
    @app.route("/goodbye")
    def goodbye():
        global embodiment_node
        
        print(f'[CA NODE {node_id}] disconnected from embodiment node {embodiment_node["id"]}')
        embodiment_node = {}
        # we do this in async of course so we can still respond to the request
        threading.Thread(target=ss_go_idle).start()
        return {}
    
    @app.route("/shutdown")
    def shutdown():
        exit()
    
    app.run(port=PORT)
    
    return


# SIMULATED USER BEHAVIOUR
def use_resources():

    # 1. update registry before we can decide what to use
    # again this is something that's only needed because we don't have humans
    # to go push buttons and whatever
    update_registry()
    for _ in range (10):
        time.sleep(USE_RESOURCES_DELAY_MS/1000)
        for _, r in resource_registry.items():
            switch_action = 'True'
            if(random.randint(0,2) == 1):
                switch_action = 'False'

            time.sleep(random.randint(0,5) / 10)

            if(random.randint(0,1) == 1):
                if 'actuator_switch' in r['capabilities']:
                    access_resource(r, 'actuator_switch', switch_action)

            time.sleep(random.randint(0,5) / 10)

            if(random.randint(0,1) == 1):
                if 'sensor_read' in r['capabilities']:
                    access_resource(r, 'sensor_read')

# This is where the CA takes the input text, acts based on it and gives some response.
# Normally it would connect to a Rasa chatbot server for example but for now it will be kept simple for the proof of concept
def handle_user_input(input: str):

    time.sleep(SIMULATED_DELAY_MS/1000)
    # prepare empty response
    response = {
        'text' : '',
        'image' : '',
    }

    # use the appropriate chatbots based on the embodiment capabilities
    if 'text_out' in embodiment_node['capabilities']:
        response['text']= f'Thanks for saying {input}',
    if 'image_out' in embodiment_node['capabilities']:
        response['image']= "https://...jpg"
    
    return response

# function to use some of the available resources in the system. 
# in a real system this behaviour would be implemented in or triggered by the actual chatbot
def access_resource(resource, action, param = None):
    global mutex_timestamp

    print(f'[CA NODE {node_id}] performing {action} on {resource["name"]}....')

    result = {
        'success': False,
        'value': None,
    }

    update_registry()

    # 2. contact each node
    obtain_lock_on_resource(resource)

    # 3. use resource
    if(action == 'actuator_switch'):
        url = f"http://{resource['host']}:{resource['port']}/{action}"
        response = requests.get(url, json={
            'actuator_switch': param
        })
        # Check if the request was successful
        if response.status_code == 200:
            # update result
            result['success'] = True
            result['value'] = response.json()
        else:
            print(f'[CA NODE {node_id}] Request {action} failed with status code:', response.status_code)

    elif(action == 'sensor_read'):
        url = f"http://{resource['host']}:{resource['port']}/{action}"
        response = requests.get(url, json={
        })
        # Check if the request was successful
        if response.status_code == 200:
            # update result
            result['success'] = True
            result['value'] = response.json()
        else:
            print(f'[CA NODE {node_id}] Request {action} failed with status code:', response.status_code)

    # 4. remove mutex lock
    mutex_timestamp = None

    print(f'[CA NODE {node_id}] successfully performed {action} on {resource["name"]} result: { result}')

    return result

def update_registry() -> None:
    global node_registry
    global node_id
    global resource_registry

    url = f"http://{system_constants.SS_HOST}:{system_constants.SS_PORT}/get_nodes"
    response = requests.get(url, json={})
    # Check if the request was successful
    if response.status_code == 200:
        # Extract the new_node_id from the response JSON
        node_registry = response.json()['ca_registry']
        
        # obviously we remove this CA from the registry
        self_index = 0
        for index, node in node_registry.items():
            if(int(node_id) == int(node['id'])):
                self_index = index
        del node_registry[self_index]
                
                
        resource_registry = response.json()['resource_registry']
    else:
        print(f'[CA NODE {node_id}] Request update_registry failed with status code:', response.status_code)
    return

# obtain mutual exclusion accessess given resource
def obtain_lock_on_resource(resource) -> bool:
    global node_registry
    global mutex_timestamp

    mutex_timestamp = {
        'id': resource["id"],
        'time': current_time_in_ms()
    }

    ok_counter = 0
    timeout_counter = 0
    timeout_ids = []

    # TODO: continue from here, not everyone seems to receive their mutex locks
    for _, node in node_registry.items():
        url = f'http://{node["host"]}:{node["port"]}/mutex'
        # print(f'[CA NODE {node_id}] Mutex on: {resource["name"]} {_}/{len(node_registry.items())}')
        try:
            # print(f'[CA NODE {node_id}] waiting for {_}/{len(node_registry.items())}')
            response = requests.get(url, json= mutex_timestamp, timeout=(MUTEX_TIMEOUT_MS/1000))
            # Check if the request was successful
            if response.status_code == 200:
                # Extract the new_node_id from the response JSON
                response = response.json()['response']
                if(response == 'ok'):
                    ok_counter += 1
                else:
                    return False
            else:
                print(f'[CA NODE {node_id}] Mutex request failed with status code:', response.status_code)
        except requests.Timeout:
            timeout_counter += 1
            timeout_ids.append(node['id'])
            # print(f'[CA NODE {node_id}] Mutex request timed out at node {node["id"]} for resource {resource["name"]}')
            # Skipping this node')
            pass
        except Exception as e:
            print(f'[CA NODE {node_id}] Mutex request failed on ', node)
            return False
    
    
    print(f'[CA NODE {node_id}] Obtained lock on {resource["name"]}. OKs: {ok_counter} TIMEOUTs: {timeout_counter} (nodes: {timeout_ids})')

    return True

def ss_callback() -> None:
    global node_id
    global resource_registry

    url = f"http://{system_constants.SS_HOST}:{system_constants.SS_PORT}/ca_wakeup"
    response = requests.get(url, json={
        'host' : HOST,
        'port' : PORT
    })
    # Check if the request was successful
    if response.status_code == 200:
        # Extract the new_node_id from the response JSON
        node_id = response.json()['new_node_id']
        resource_registry = response.json()['resource_registry']
        
        setproctitle.setproctitle(f'DECA - CA NODE {node_id} (Python)')

        print(f'[CA NODE {node_id}] received node ID from SS: {node_id}')
    else:
        print(f'[CA NODE {node_id}] Request ss_callback failed with status code:', response.status_code)
    return


def ss_go_idle() -> None:

    try:
        # wait a bit before going idle
        global node_registry
        url = f"http://{system_constants.SS_HOST}:{system_constants.SS_PORT}/ca_idle"
        requests.get(url, json={
            'id': node_id
        })

    except Exception as e:
        print(e)
        pass
        # it's okay if we error out or something, it's just because we're shutting down probably


    return

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])