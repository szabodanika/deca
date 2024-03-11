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
SS_HOST = "0.0.0.0"

HOST = "0.0.0.0"
PORT = 0

node_id = -1
embodiment_node = {}
resource_registry = {}

# Flask app required for listening to incoming HTTP requests
app = Flask(__name__)


def main(args):
    global PORT
    PORT = args[3]
    print(f'[CA NODE {node_id}] Starting on {HOST}:{PORT}')

    # 1. start listening
    listening_thread = threading.Thread(target=listen)
    listening_thread.start()
    
    
    # 2. super server callback
    ss_callback_thread = threading.Thread(target=ss_callback)
    ss_callback_thread.start()

def listen() -> None:
    global embodiment_node

    # remove most of the annoying flask logs
    import logging
    log = logging.getLogger('werkzeug')
    # log.disabled = True
    log.setLevel(logging.ERROR)
    # app.logger.disabled = True

    # this is where a newly started EN checks in
    @app.route("/handshake")
    def handshake():
        data = request.json

        # Extract the new_node_id from the response JSON
        embodiment_node['id'] = data['id']
        embodiment_node['capabilities'] = data['capabilities']
        embodiment_node['host'] = data['host']
        embodiment_node['port'] = data['port']
        
        print(f'[CA NODE {node_id}] handshake done with embodiment node {embodiment_node["id"]}')

        return {
            'id': node_id
        }
    
    # this is where the embodiment sends the user input
    @app.route("/user_input")
    def handshake():
        data = request.json

        response = handle_user_input(data['input'])      

        return response
    
    @app.route("/shutdown")
    def shutdown():
        exit()
    
    app.run(port=PORT)
    
    return

# This is where the CA takes the input text, acts based on it and gives some response.
# Normally it would connect to a Rasa chatbot server for example but for now it will be kept simple for the proof of concept
def handle_user_input():

    # prepare empty response
    response = {
        'text' : '',
        'image' : '',
    }

    # use the appropriate chatbots based on the embodiment capabilities
    if 'text_out' in embodiment_node['capabilities']:
        response['text']= "Thanks for your input!",
    if 'image_out' in embodiment_node['capabilities']:
        response['image']= "https://t4.ftcdn.net/jpg/01/66/10/03/360_F_166100342_KbTGIRrnrlwGDZSXSMpH3zfn2dxyTKae.jpg"
    
    return response

def ss_callback() -> None:
    global node_id
    global resource_registry

    url = f"http://{SS_HOST}:8000/ca_wakeup"
    response = requests.get(url, json={
        'host' : HOST,
        'port' : PORT
    })
    # Check if the request was successful
    if response.status_code == 200:
        # Extract the new_node_id from the response JSON
        node_id = response.json()['new_node_id']
        resource_registry = response.json()['resource_registry']
        print(f'[CA NODE {node_id}] received node ID from SS: {node_id}')
    else:
        print(f'[CA NODE {node_id}] Request failed with status code:', response.status_code)
    return
   

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])