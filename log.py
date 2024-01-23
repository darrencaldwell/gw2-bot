import time

class LogObject:
    def __init__(self, name):
        self.name = name
        self.t0 = time.time()

    def __enter__(self):
        print("Starting "+ self.name + "...")


    def __exit__(self, *args):
        print("Finished " + self.name + ", took " + str(time.time() - self.t0)[:3] + " seconds")
