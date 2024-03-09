import sys
sys.path.append('../')
from flask import Flask
import threading
from common.util import generate_id
import subprocess
import requests

# constants
SS_HOST = "0.0.0.0"

node_id = 0

def main(args):
    # 1. start listening
    listening_thread = threading.Thread(target=listen)
    listening_thread.start()
    
    
    # 2. super server callback
    ss_callback_thread = threading.Thread(target=ss_callback)
    ss_callback_thread.start()

def listen() -> None:
    return

    
def ss_callback() -> None:
    url = f"http://{SS_HOST}:8000/ca_wakeup"
    response = requests.get(url, json={})
    # Check if the request was successful
    if response.status_code == 200:
        # Extract the new_node_id from the response JSON
        node_id = response.json()['new_node_id']
        print(f'[CA NODE] received node ID from SS: {node_id}')
    else:
        print("[CA NODE] Request failed with status code:", response.status_code)
    return
   

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])