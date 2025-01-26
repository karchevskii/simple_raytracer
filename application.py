import glfw
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
from fragment_shader import FRAGMENT_SHADER
from vertex_shader import VERTEX_SHADER
from utils import mouse_callback
from camera import Camera
from light import Light

class Application:
    def __init__(self, width=800, height=600, title=""):
        self.width = width
        self.height = height
        self.title = title
        self.camera = Camera(position=[-1.5, 0.0, -2.0])
        self.lastX = width / 2
        self.lastY = height / 2
        self.first_mouse = True

        self.init_window()
        self.init_buffers()
        self.init_shaders()
        self.init_lights()
        self.main_loop()

    def init_window(self):
        if not glfw.init():
            raise Exception("GLFW initialization failed")

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)

        self.window = glfw.create_window(self.width, self.height, self.title, None, None)
        if not self.window:
            glfw.terminate()
            raise Exception("Failed to create GLFW window")

        glfw.make_context_current(self.window)
        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)

        glfw.set_cursor_pos_callback(self.window, mouse_callback)
        glfw.set_window_user_pointer(self.window, self)

    def init_buffers(self):
        vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0,
        ], dtype=np.float32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    def init_shaders(self):
        self.shader = compileProgram(
            compileShader(VERTEX_SHADER, GL_VERTEX_SHADER),
            compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
        )
        glUseProgram(self.shader)

        position = glGetAttribLocation(self.shader, "position")
        glEnableVertexAttribArray(position)
        glVertexAttribPointer(position, 2, GL_FLOAT, GL_FALSE, 0, None)

        self.resolution_loc = glGetUniformLocation(self.shader, "resolution")
        self.time_loc = glGetUniformLocation(self.shader, "time")
        self.camera_pos_loc = glGetUniformLocation(self.shader, "camera_pos")
        self.camera_dir_loc = glGetUniformLocation(self.shader, "camera_dir")

        glBindVertexArray(0)

    def init_lights(self):
        self.lights = [
            Light(position=[5.0, 5.0, -10.0], color=[0.4, 0.4, 0.4]),
            Light(position=[-5.0, 100.0, 0.0], color=[0.3, 0.5, 0.5]),
            Light(position=[0.0, 5.0, 0.0], color=[0.5, 0.5, 0.5]),
            Light(position=[-5.0, 5.0, 0.0], color=[0.2, 0.2, 0.1]),
            Light(position=[0.0, 5.0, 0.0], color=[0.3, 0.1, 1.0]),
        ]
        self.light_uniforms = []
        for i in range(len(self.lights)):
            position_loc = glGetUniformLocation(self.shader, f"lights[{i}].position")
            color_loc = glGetUniformLocation(self.shader, f"lights[{i}].color")
            self.light_uniforms.append((position_loc, color_loc))

    def main_loop(self):
        while not glfw.window_should_close(self.window):
            glfw.poll_events()
            self.process_input()

            current_time = glfw.get_time()
            self.update_lights(current_time)

            glClear(GL_COLOR_BUFFER_BIT)

            glUseProgram(self.shader)
            glBindVertexArray(self.vao)

            glUniform2f(self.resolution_loc, self.width, self.height)
            glUniform1f(self.time_loc, current_time)
            glUniform3f(self.camera_pos_loc, *self.camera.position)
            glUniform3f(self.camera_dir_loc, *self.camera.direction)

            for i, light in enumerate(self.lights):
                pos_loc, col_loc = self.light_uniforms[i]
                glUniform3f(pos_loc, *light.position)
                glUniform3f(col_loc, *light.color)

            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
            glBindVertexArray(0)

            glfw.swap_buffers(self.window)

        self.cleanup()

    def update_lights(self, time):
        self.lights[0].position[0] = 5.0 * np.cos(time)
        self.lights[0].position[2] = 5.0 * np.sin(time)

    def process_input(self):
        self.camera.process_keyboard(self.window)
        if glfw.get_key(self.window, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(self.window, True)

    def cleanup(self):
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(1, [self.vbo])
        glfw.terminate()
