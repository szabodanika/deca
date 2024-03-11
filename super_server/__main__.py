import sys
sys.path.append('../')
from flask import Flask
import threading
from common.util import generate_id
import subprocess
from flask import request

# system constants
CAPACITY = 8
MIN_STANDBY_CA = 2
# how many CAs to start up at a time
CA_INCREMENTS = 2
# default port if not specified with argument
PORT = 8000
HOST = '0.0.0.0'
CA_HOST = '0.0.0.0'
CA_PORTS = list(range(PORT+1, PORT + CAPACITY + 1))

# ca nodes register themselves here
# all nodes are offline initially
ca_registry =  {}
# sa nodes register themselves here
resource_registry =  {}

# Flask app required for listening to incoming HTTP requests
app = Flask(__name__)

def main(args) -> None:

    PORT = args[1]
    print(f'[SS NODE] Starting on {HOST}:{PORT}')

    # 1. start listening for requests
    listening_thread = threading.Thread(target=listen)
    listening_thread.start()
    
    
    # 2. start up MIN_STANDBY_CA servers (offline -> idle)
    initialising_ca_servers_thread = threading.Thread(target=init_starting_ca_servers)
    initialising_ca_servers_thread.start()

    return


def listen() -> None:

    # remove most of the annoying flask logs
    import logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    log.setLevel(logging.ERROR)
    app.logger.disabled = True

    # this is where a resource registers itself
    @app.route("/register_resource")
    def register_resource():
        new_node_id = generate_id()
        data = request.json
        host = data.get('host')
        port = data.get('port')
        capabilities = data.get('capabilities')
        name = data.get('name')
        resource_registry[new_node_id] = {
            'id' : new_node_id,
            'host' : host,
            'port' : port,
            'capabilities' : capabilities,
            'name' : name
        }
        return {
            'new_node_id': new_node_id
            }
    
    # gives the list of resources that have been registered
    @app.route("/get_resources")
    def get_resources():
        return resource_registry
    
    # this is where a newly started EN checks in
    @app.route("/ca_wakeup")
    def ca_wakeup():
        data = request.json
        host = data.get('host')
        port = data.get('port')
        new_node_id = generate_id()
        # set the status of this node to idle 
        ca_registry[new_node_id] = {
            'status' : 'idle',
            'id' : new_node_id,
            'host' : host,
            'port' : port
        }
        print(f'[SS NODE] CA node came to idle: {ca_registry[new_node_id]}')

        return {
            'new_node_id': new_node_id,
            'resource_registry': resource_registry
            }
    
    # this is where an EN can say they finished their service request
    # and return to idle state
    @app.route("/ca_idle")
    def ca_idle():
        return ""
    
    # this is where a newly started EN checks in
    # we just give it the contact details for one of the idle nodes

    @app.route("/service_request")
    def service_request():
        if(status_count('online') == CAPACITY):
            # we reached capacity
            return {
                'error': 'server capacity reached'
            }
        
        elif(status_count('idle') == 1 & status_count('online') < CAPACITY -1):
            # only one idle left, but there is more capacity so we can 
            # start up more CAs
            print("[SS NDOE] starting up more CA servers")
            init_ca_servers(count = CA_INCREMENTS)

        # let's give the embodiment a node ID
        new_node_id = generate_id()
        
        # select correct CA node
        assigned_ca = get_first_idle_ca()

        # mark assigned CA as online
        ca_registry[assigned_ca['id']]['status'] = 'online'

        return {
            'host': assigned_ca['host'],
            'port': assigned_ca['port'],
            'id': new_node_id,
            'resource_registry': resource_registry
        }
    
    # for developer to check SS status
    @app.route("/status")
    def status():
        return f'ca_registry: {ca_registry}\nresource_registry: {resource_registry}'
      

    @app.route("/shutdown")
    def shutdown():
        exit()

    app.run(port=PORT)
    
    return

def init_starting_ca_servers() -> None:
    init_ca_servers(MIN_STANDBY_CA)

def init_ca_servers(count = MIN_STANDBY_CA) -> None:
    # make sure we only start up as much as CAPACITY allows for
    if(status_count('online') + count > CAPACITY):
        count = CAPACITY - status_count('online')

    # start them
    for i in range(status_count('idle') + status_count('online'), status_count('idle') + status_count('online') + count):
        init_ca(i)
    

# brings a CA from offline to idle state
# this is only step 1/2. Step 2/2 will be the CA sending a 
# request to ca_wakeup and then it will get an ID and
# the SS's internal state of the CA will be updated
def init_ca(index: int) -> None:
    print(f'[SUPER SERVER] starting up CA {index}')
    command = ["python",
                "../conversational_agent_node/__main__.py",
                "--ip", CA_HOST, 
                "--port", str(CA_PORTS[index])]
    
    subprocess.Popen(command)
    return

# brings a CA from idle to offline state
def shutdown_ca(index: int) -> None:
    return

# silly utility functions

def status_count(status: str) -> int:
    count = 0
    for s in ca_registry.values():
        if s['status'] == status:
            count += 1
    return count

def get_first_idle_ca() -> int:
    for s in ca_registry.values():
        if s['status'] == 'idle':
            return s
    return None

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])