import glfw

def mouse_callback(window, xpos, ypos):
    app = glfw.get_window_user_pointer(window)
    if app.first_mouse:
        app.lastX = xpos
        app.lastY = ypos
        app.first_mouse = False

    xoffset = xpos - app.lastX
    yoffset = app.lastY - ypos
    app.lastX = xpos
    app.lastY = ypos

    app.camera.process_mouse_movement(xoffset, yoffset)

