import random


def generate_id() -> int:
  return random.randint(0, 2**16)
  