import random
import time
import math

id_counter = -1
# incremantal positive int id
def generate_id() -> int:
  global id_counter
  id_counter += 1
  return id_counter
  
# return current time in millisecods (for timestamping)
def current_time_in_ms():
    return math.floor(time.time() * 1000)