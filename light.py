import numpy as np

class Light:
    def __init__(self, position, color):
        self.position = np.array(position, dtype=np.float32)
        self.color = np.array(color, dtype=np.float32)
