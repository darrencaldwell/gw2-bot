import signal
import json
import typing as t
from dataclasses import dataclass

@dataclass
class MutRecord:
    has_been_used: bool
    reset_time: int
    message: str

HAS_BEEN_USED = False

try:
    with open("state.json", "r") as f:
        file_data = json.load(f)
except:
    with open("state.json", "w") as f:
        f.write("")
    file_data = {}

RESET_TIME = int(file_data.get("reset_time", 16))
MESSAGE = file_data.get("msg", "Good morning Connor")

my_mut_record = MutRecord(has_been_used=HAS_BEEN_USED, reset_time=RESET_TIME, message=MESSAGE)

def reset_handler(*args):
    try:
        my_mut_record.has_been_used = False
    except Exception as e:
        print("Could not reset: ", e)

def read_handler(*args):
    try: 
        with open("state.json", "r") as f:
            file_data: t.Dict = json.load(f)
    except:
        file_data = {}
    
    try:
        reset_handler()
        commands = {}
        
        with open("/tmp/edits.json", "r") as f:
            commands = json.load(f)

        
        
        if "reset_time" in commands:
            my_mut_record.reset_time = int(commands["reset_time"])

        if "message" in commands:
            my_mut_record.message = commands["message"]
        
        file_data.update(commands)

        with open("state.json", "w") as f:
            json.dump(file_data, f)
    
    except Exception as e:
        print("Could not update: ", e)

signal.signal(signal.SIGUSR1, reset_handler)
signal.signal(signal.SIGUSR2, read_handler)