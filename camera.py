import numpy as np
import glfw

class Camera:
    def __init__(self, position, yaw=90.0, pitch=0.0, speed=0.1, sensitivity=0.1, direction=[0.0, 0.0, -1.0]):
        self.position = np.array(position, dtype=np.float32)
        self.yaw = yaw
        self.pitch = pitch
        self.speed = speed
        self.sensitivity = sensitivity
        self.direction = np.array(direction, dtype=np.float32)
        self.update_direction()

    def update_direction(self):
        x = np.cos(np.radians(self.yaw)) * np.cos(np.radians(self.pitch))
        y = np.sin(np.radians(self.pitch))
        z = np.sin(np.radians(self.yaw)) * np.cos(np.radians(self.pitch))
        self.direction = np.array([x, y, z], dtype=np.float32)
        self.direction /= np.linalg.norm(self.direction)

    def process_keyboard(self, window):
        right = np.cross(self.direction, [0.0, 1.0, 0.0])
        right /= np.linalg.norm(right)

        if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
            self.position += self.speed * self.direction
        if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
            self.position -= self.speed * self.direction
        if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
            self.position -= self.speed * right
        if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
            self.position += self.speed * right
        if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
            self.position[1] += self.speed
        if glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS:
            self.position[1] -= self.speed

    def process_mouse_movement(self, xoffset, yoffset):
        self.yaw += xoffset * self.sensitivity
        self.pitch += yoffset * self.sensitivity

        self.pitch = max(-89.0, min(89.0, self.pitch))
        self.update_direction()