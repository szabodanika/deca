import sys
sys.path.append('../')
from flask import Flask
import threading
from common.util import generate_id
import subprocess
from flask import request
import time
import os 
import signal
import setproctitle
import math
import atexit

# system constants
CAPACITY = 8
MIN_STANDBY_CA = 2
# how many CAs to start up at a time
CA_INCREMENTS = 2
MIN_IDLE_CA = 2

# check if we need to shut down idle nodes every x seconds
CHECK_SHUTDOWN_NEEDED_DELAY_SEC = 5

# default port if not specified with argument
PORT = 8000
HOST = '0.0.0.0'
CA_HOST = '0.0.0.0'
CA_PORTS = list(range(PORT+1, PORT + CAPACITY + 1))

# ca nodes register themselves here
# all nodes are offline initially
ca_registry =  {}
# embodiment registry
e_registry =  {}
# sa nodes register themselves here
resource_registry =  {}
# system processes of the CAs - we keep them around so we can also stop them
ca_processes = {}

# Flask app required for listening to incoming HTTP requests
app = Flask(__name__)

processes_started = 0
processes_shutdown = 0

node_id = generate_id()

def exit_handler():
    print("[SS NODE] Terminating CA processes before exiting")
    # stop all CA processes before exiting
    shutdown_all_ca_servers()

atexit.register(exit_handler)

def main(args) -> None:
    try:
        global HOST
        global PORT
        global CAPACITY
        global MIN_STANDBY_CA
        global CA_INCREMENTS
        global CA_PORTS
        global MIN_IDLE_CA

        HOST = args[1]
        PORT = int(args[3])
        CAPACITY = int(args[5])
        MIN_STANDBY_CA = int(args[7])
        CA_INCREMENTS = int(args[9])
        CA_PORTS = list(range(PORT+1, PORT + CAPACITY + 1))
        MIN_IDLE_CA = int(args[11])

        print(f'[SS NODE] Starting on {HOST}:{PORT}. It will use ports {PORT}-{PORT + CAPACITY + 1}')

        setproctitle.setproctitle(f'DECA - SS NODE {node_id} (Python)')

        

        # 1. start listening for requests
        listening_thread = threading.Thread(target=listen)
        listening_thread.start()
            
        # 2. start up MIN_STANDBY_CA servers (offline -> idle)
        initialising_ca_servers_thread = threading.Thread(target=init_starting_ca_servers)
        initialising_ca_servers_thread.start()

         # 3. start up periodic idle count checker
        check_shutdown_needed_thread = threading.Thread(target=check_shutdown_needed)
        check_shutdown_needed_thread.start()
    except KeyboardInterrupt:
        sys.exit(1)

      

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
    @app.route("/get_nodes")
    def get_nodes():
        return {
            'ca_registry': ca_registry,
            'resource_registry': resource_registry,
        }
    
    # this is where a newly started EN checks in
    @app.route("/ca_wakeup")
    def ca_wakeup():
        global ca_registry

        data = request.json
        host = data.get('host')
        port = data.get('port')
        new_node_id = generate_id()

        # assign id in registry too
        for i, ca in ca_registry.items():
            if(int(ca['port']) == int(port)):
                ca_registry[i]['id'] = new_node_id
                print(f'[SS NODE] CA node came to idle: {ca_registry[i]}')

        
        return {
            'new_node_id': new_node_id,
            'resource_registry': resource_registry
            }
    
    # this is where an EN can say they finished their service request
    # and return to idle state
    @app.route("/ca_idle")
    def ca_idle():
        data = request.json
        id = data['id']
        
        for i, ca in ca_registry.items():
            if(ca['id'] == id):
                ca_registry[i]['status'] = 'idle'
        
        return {}
    
    # this is where a newly started EN checks in
    # we just give it the contact details for one of the idle nodes

    @app.route("/service_request")
    def service_request():
        if(status_count('online') == CAPACITY):
            # we reached capacity
            return {
                'error': 'server capacity reached'
            }
        
        elif(status_count('idle') < MIN_IDLE_CA):
            # only one idle left, but there is more capacity so we can 
            # start up more CAs
            print("[SS NODE] starting up more CA servers")
            init_ca_servers(count = CA_INCREMENTS)

        # let's give the embodiment a node ID
        new_node_id = generate_id()

        data = request.json
        host = data.get('host')
        port = data.get('port')

        # set the status of this node to idle 
        e_registry[new_node_id] = {
            'id' : new_node_id,
            'host' : host,
            'port' : port
        }

        # select correct CA node
        assigned_ca = get_first_idle_ca()

        print(f'[SS NODE] assigned CA {assigned_ca} to EN {new_node_id}')

        # mark assigned CA as online
        for i, ca in ca_registry.items():
            if(ca['id'] == assigned_ca['id']):
                ca_registry[i]['status'] = 'online'

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
    # make sure we shut down as many as CAPACITY allows for
    if(status_count('online')  + status_count('idle') + count > CAPACITY):
        count = CAPACITY - status_count('online')

    # start them
    for i in range(status_count('idle') + status_count('online'), status_count('idle') + status_count('online') + count):
        init_ca(i)

def check_shutdown_needed() -> None:
    while(True):
        time.sleep(CHECK_SHUTDOWN_NEEDED_DELAY_SEC)
        # shut down CAs if there's too many idle 
        idle = status_count('idle')
        if(idle > MIN_IDLE_CA and idle > MIN_STANDBY_CA):
            shutdown_count = idle - MIN_IDLE_CA
            if(idle - shutdown_count < MIN_STANDBY_CA):
                shutdown_count = idle - MIN_STANDBY_CA
            print(f'[SS NODE] {idle} idle nodes, shutting down {shutdown_count}')
            shutdown_ca_servers(shutdown_count)
            pass
        else:
            print(f'[SS NODE] {status_count("idle")} idle nodes left, not shutting any down yet')

def shutdown_ca_servers(count) -> None:

    # make sure we shut down as many as MIN_STANDBY_CA allows for
    if(status_count('idle') - count < MIN_STANDBY_CA):
        count = status_count('idle') - MIN_STANDBY_CA

    # shut them down
    for i in range(status_count('idle') + status_count('online') -1, status_count('idle') + status_count('online') - count -1 , -1):
        shutdown_ca(i)

def shutdown_all_ca_servers() -> None:
    for _, p in ca_processes.items():
        p.kill()
    

# brings a CA from offline to idle state
# this is only step 1/2. Step 2/2 will be the CA sending a 
# request to ca_wakeup and then it will get an ID and
# the SS's internal state of the CA will be updated
def init_ca(index: int) -> None:
    global processes_started

    command = ["python",
                "../conversational_agent_node/__main__.py",
                "--ip", CA_HOST, 
                "--port", str(CA_PORTS[index])]


    try:
        print("PROBLEMO ", ca_processes[index])
        return
    except Exception as e:
        pass

    ca_processes[index] = subprocess.Popen(command)
    processes_started += 1
    
    print(f'[SS NODE] starting up CA {index+1}/{CAPACITY}, PID {ca_processes[index].pid}, PORT {CA_PORTS[index]}')

    # set the status of this node to idle 
    ca_registry[index] = {
        'id' : '-1',
        'status' : 'idle',
        'host' : CA_HOST,
        'port' : CA_PORTS[index],
    }

    return

def shutdown_ca(index: int) -> None:
    global processes_shutdown
    try:
        print(f'[SS NODE] shutting down CA {index+1}/{CAPACITY} - PID {ca_processes[index].pid}')
        if ca_processes[index].poll() is None:
            # Process is still running
            ca_processes[index].kill()
            processes_shutdown += 1
        else:
            print(f'[SS NODE] Error shutting down CA {index+1}/{CAPACITY}:Process has already terminated.')
        del ca_processes[index]
        del ca_registry[index]
    except Exception as e:
        print(f"[SS NODE] Error shutting down CA {index+1}/{CAPACITY}: {e}")

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