import sys
sys.path.append('../')
from flask import Flask
import threading
from common.util import generate_id
import subprocess

# system constants
CAPACITY = 8
MIN_STANDBY_CA = 2
PORT = 8000
CA_HOST = '0.0.0.0'
CA_PORTS = range(PORT+1, PORT + CAPACITY + 1)
CAPABILITIES = [
    # capability to switch something on and off
    # state is a boolean ('true' or 'false')
    {
        'name': 'switch',
        'params': ['state']
    },
    # capability to read value (e.g. temperature sensor)
    {
        'name': 'read',
        'params': []
    }
]

# no CA or resource nodes registered yet
ca_registry  = []
sa_registry  = []

# all nodes are offline initially
statuses =  {}

# Flask app required for listening to incoming HTTP requests
app = Flask(__name__)

def main(args) -> None:

    # 1. start listening for requests
    listening_thread = threading.Thread(target=listen)
    listening_thread.start()
    
    
    # 2. start up MIN_STANDBY_CA servers (offline -> idle)
    initialising_ca_servers_thread = threading.Thread(target=init_ca_servers)
    initialising_ca_servers_thread.start()

    return


def listen() -> None:
    # this is where a resource registers itself
    @app.route("/register_resource")
    def register_resource():
        new_node_id = generate_id()
        sa_registry.append(new_node_id)
        return {
            'new_node_id': new_node_id
            }
    
    # this is where a newly started EN checks in
    @app.route("/ca_wakeup")
    def ca_wakeup():
        new_node_id = generate_id()
        # set the status of this node to idle 
        statuses[new_node_id] = 'online'
        # add this node to the registry
        ca_registry.append(new_node_id)    
        return {
            'new_node_id': new_node_id
            }
    
    # this is where an EN can say they finished their service request
    # and return to idle state
    @app.route("/ca_idle")
    def ca_idle():
        return ""
    
    # this is where a newly started EN checks in
    @app.route("/service_request")
    def service_request():
        return ""
    
    # this is where a newly started EN checks in
    @app.route("/status")
    def status():
        return f'statuses: {statuses}\nca_registry: {ca_registry}\nsa_registry: {sa_registry}'
      
    app.run(port=PORT)
    
    return

def init_ca_servers() -> None:
    for i in range(MIN_STANDBY_CA):
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

# brings a CA from idle to online state 
def assign_ca(index: int) -> None:
    return

# brings a CA from online to idle state
def unassign_ca(index: int) -> None:
    return

# brings a CA from idle to offline state
def shutdown_ca(index: int) -> None:
    return

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])