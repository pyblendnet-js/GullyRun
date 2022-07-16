'''
    Controls:
        Move:
            Forward - W
            Backwards - S

        Strafe:
            Up - up arrow
            Down - down arrow
            Left - A
            Right - D

        Rotate:
            Left - Q
            Right - E

        Zoom:
            In - X
            Out - Z
            
        Roll:
            Left - left arrow
            Right - right arrow

    adopted by: Alex Zakrividoroga - see modernGl example of the same name
    adapted by Robert Parker
'''

import numpy as np
from pyrr import matrix33, Matrix44, Quaternion, Vector3, vector

import moderngl

class Camera():
    _dt = 0.1
    _zoom_step = 0.01
    _move_vertically = 0.01
    _move_horizontally = 0.01
    _rotate_horizontally = 0.1
    _rotate_vertically = 0.1
    _droll = 0.001

    _z_near = 0.01
    _z_far = 100
    _camera_dist = -40.0    
    _down = Vector3([0.0, -1.0, 0.0])
    _forward = Vector3([0.0, 0.0, 1.0])
    _right = Vector3([1.0, 0.0, 0.0])
        

    def __init__(self, ratio):
        self._ratio = ratio
        self.resetProjection()
        self.resetLookat()
        
    def setDist(self,dist):
        self._camera_dist = -dist
        self._camera_position = Vector3([0.0, 0.0, self._camera_dist])
        self.resetProjection()
        self.build_look_at()
    #enddef
        
    def resetProjection(self):    
        self._field_of_view_degrees = 60.0
        self.build_projection()
    #enddef

    def resetLookat(self):
        self._offset = Vector3([0.0, 0.0, self._camera_dist])
        self._camera_position = Vector3([0.0, 0.0, self._camera_dist])
        self._camera_front = Vector3([0.0, 0.0, 1.0])
        self._camera_up = Vector3([0.0, 1.0, 0.0])
        self._cameras_target = (self._camera_position + self._camera_front)
        self.build_look_at()
    #enddef
 
    def lookatBelow(self):
        print("Look below")
        self._camera_position -= self._offset
        self._offset = self._down*self._camera_dist
        self._camera_position += self._offset
        #rint(self._camera_position)
        self._camera_front = self._down
        self._camera_up = self._forward
        self._cameras_target = (self._camera_position + self._camera_front)
        self.build_look_at()  
    #enddef

    def lookatForward(self):
        self._camera_position -= self._offset
        self._offset = self._forward*self._camera_dist
        self._camera_position += self._offset
        self._camera_front = self._forward
        self._camera_up = self._down*-1.0
        self._cameras_target = (self._camera_position + self._camera_front)
        self.build_look_at()  
    #enddef

    def lookatRight(self):
        self._camera_position -= self._offset
        self._offset = self._right*self._camera_dist
        self._camera_position += self._offset
        self._camera_front = self._right
        self._camera_up = self._down*-1.0
        self._cameras_target = (self._camera_position + self._camera_front)
        self.build_look_at()  
    #enddef

    def zoom_in(self):
        self._field_of_view_degrees = self._field_of_view_degrees - self._zoom_step*self._dt
        self.build_projection()
    #enddef

    def zoom_out(self):
        self._field_of_view_degrees = self._field_of_view_degrees + self._zoom_step*self._dt
        self.build_projection()
    #enddef

    def move_forward(self):
        self._camera_position = self._camera_position + self._camera_front * self._move_horizontally*self._dt
        self.build_look_at()

    def move_backwards(self):
        self._camera_position = self._camera_position - self._camera_front * self._move_horizontally*self._dt
        self.build_look_at()
    #enddef

    def strafe_left(self):
        self._camera_position = self._camera_position - vector.normalize(self._camera_front ^ self._camera_up) * self._move_horizontally*self._dt
        self.build_look_at()

    def strafe_right(self):
        self._camera_position = self._camera_position + vector.normalize(self._camera_front ^ self._camera_up) * self._move_horizontally*self._dt
        self.build_look_at()
    #enddef

    def strafe_up(self):
        self._camera_position = self._camera_position + self._camera_up * self._move_vertically*self._dt
        self.build_look_at()
    #enddef

    def strafe_down(self):
        self._camera_position = self._camera_position - self._camera_up * self._move_vertically*self._dt
        self.build_look_at()
    #enddef

    def rotate_left(self):
        rotation = Quaternion.from_y_rotation(2 * float(self._rotate_horizontally*self._dt) * np.pi / 180)
        self._camera_front = rotation * self._camera_front
        self.build_look_at()
    #enddef

    def rotate_right(self):
        rotation = Quaternion.from_y_rotation(-2 * float(self._rotate_horizontally*self._dt) * np.pi / 180)
        self._camera_front = rotation * self._camera_front
        self.build_look_at()
    #enddef

    def rotate_up(self):
        rotation = Quaternion.from_x_rotation(2 * float(self._rotate_vertically*self._dt) * np.pi / 180)
        self._camera_front = rotation * self._camera_front
        self.build_look_at()
    #enddef

    def rotate_down(self):
        rotation = Quaternion.from_x_rotation(-2 * float(self._rotate_vertically*self._dt) * np.pi / 180)
        self._camera_front = rotation * self._camera_front
        self.build_look_at()
    #enddef

    def roll_left(self):
      mat = matrix33.create_from_axis_rotation(self._camera_front,self._droll*self._dt)
      self._camera_up = matrix33.apply_to_vector(mat,self._camera_up)   
      self.build_look_at()
    #enddef

    def roll_right(self):
      mat = matrix33.create_from_axis_rotation(self._camera_front,-self._droll *self._dt)
      self._camera_up = matrix33.apply_to_vector(mat,self._camera_up)   
      self.build_look_at()
    #enddef

    def build_look_at(self):
        self._cameras_target = (self._camera_position + self._camera_front)
        self.mat_lookat = Matrix44.look_at(
            self._camera_position,
            self._cameras_target,
            self._camera_up)
    #enddef

    def build_projection(self):
        self.mat_projection = Matrix44.perspective_projection(
            self._field_of_view_degrees,
            self._ratio,
            self._z_near,
            self._z_far)
    #enddef

    def setPos(self, pos, forward, up):
        #print("Before:",self._camera_position)
        self._camera_position -= self._offset
        #print("Without:",self._camera_position)
        self._camera_position = Vector3([pos.x,pos.y,pos.z])
        #print("Moveto:",self._camera_position)
        self._camera_front = Vector3([forward.x,forward.y,forward.z])
        self._camera_front.normalize()
        self._offset = self._camera_front*self._camera_dist
        self._camera_position += self._offset
        #print("After:",self._camera_position)
        self._camera_up = up   
        self.build_look_at()
    #enddef

def grid(size, steps):
    print(np.linspace(-size, size, steps))
    u = np.repeat(np.linspace(-size, size, steps), 2)
    print(u)
    v = np.tile([-size, size], steps)
    print(v)
    w = np.zeros(steps * 2)
    print(w)
    print(np.dstack([u, v, w]))
    return np.concatenate([np.dstack([u, v, w]), np.dstack([v, u, w])])
#enddef

import moderngl_window as mglw
    
class cameraWindow(mglw.WindowConfig):
    gl_version = (3, 3)
    window_size = (1280, 720)
    aspect_ratio = 16 / 9
    resizable = True
    title = "Simple Camera Example"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera = Camera(self.aspect_ratio)
        #rint(dir(self.wnd.keys))
        '''['A', 'ACTION_PRESS', 'ACTION_RELEASE', 'B', 'BACKSLASH', 'BACKSPACE', 'C', 'CAPS_LOCK', 'COMMA', 'D', 'DELETE', 'DOWN', 'E', 'END', 'ENTER', 'EQUAL', 'ESCAPE', 'F', 'F1', 'F10', 'F11', 'F12', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'G', 'H', 'HOME', 'I', 'INSERT', 'J', 'K', 'L', 'LEFT', 'LEFT_BRACKET', 'M', 'MINUS', 'N', 'NUMBER_0', 'NUMBER_1', 'NUMBER_2', 'NUMBER_3', 'NUMBER_4', 'NUMBER_5', 'NUMBER_6', 'NUMBER_7', 'NUMBER_8', 'NUMBER_9', 'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4', 'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 'NUMPAD_9', 'O', 'P', 'PAGE_DOWN', 'PAGE_UP', 'PERIOD', 'Q', 'R', 'RIGHT', 'RIGHT_BRACKET', 'S', 'SEMICOLON', 'SLASH', 'SPACE', 'T', 'TAB', 'U', 'UP', 'V', 'W', 'X', 'Y', 'Z','''
        
        self.states = {
            self.wnd.keys.W: False,     # forward
            self.wnd.keys.S: False,     # backwards
            self.wnd.keys.UP: False,    # rotate Up
            self.wnd.keys.DOWN: False,  # rotate Down
            self.wnd.keys.LEFT: False,  # rotate left
            self.wnd.keys.RIGHT: False, # rotate right
            self.wnd.keys.A: False,     # strafe left
            self.wnd.keys.D: False,     # strafe right
            self.wnd.keys.Q: False,     # roll left
            self.wnd.keys.E: False,     # roll right
            self.wnd.keys.R: False,     # strafe Up
            self.wnd.keys.F: False,     # strafe Down
            self.wnd.keys.Z: False,     # zoom in
            self.wnd.keys.X: False,     # zoom out
        }

    def move_camera(self,dt):
        self.camera._dt = dt
        if self.states.get(self.wnd.keys.W):
            self.camera.move_forward()

        if self.states.get(self.wnd.keys.S):
            self.camera.move_backwards()

        if self.states.get(self.wnd.keys.UP):
            self.camera.rotate_up()

        if self.states.get(self.wnd.keys.DOWN):
            self.camera.rotate_down()

        if self.states.get(self.wnd.keys.LEFT):
            self.camera.rotate_left()
            
        if self.states.get(self.wnd.keys.RIGHT):
            self.camera.rotate_right()

        if self.states.get(self.wnd.keys.A):
            self.camera.strafe_left()

        if self.states.get(self.wnd.keys.D):
            self.camera.strafe_right()

        if self.states.get(self.wnd.keys.R):
            self.camera.strafe_up()

        if self.states.get(self.wnd.keys.F):
            self.camera.strafe_down()

        if self.states.get(self.wnd.keys.Q):
            self.camera.roll_left()

        if self.states.get(self.wnd.keys.E):
            self.camera.roll_right()

        if self.states.get(self.wnd.keys.Z):
            self.camera.zoom_in()

        if self.states.get(self.wnd.keys.X):
            self.camera.zoom_out()
            
    def setCameraPos(self, pos, forward, up):
      self.camera.setPos(pos, forward, up)
      
    def resetCamera(self):
        self.camera.resetProjection()
        self.camera.resetLookat()
    #enddef      

    def key_event(self, key, action, modifiers):
        keys = self.wnd.keys
        if action == self.wnd.keys.ACTION_PRESS:
          if key == keys.C:
            self.camera.resetLookat()
          elif key == keys.NUMPAD_1:
            self.camera.lookatForward()
          elif key == keys.NUMPAD_3:
            self.camera.lookatRight()
          elif key == keys.NUMPAD_7:
            self.camera.lookatBelow()
          #endif
        #endif
        if key not in self.states:
            print(key, action)
            return
        #endif    

        if action == self.wnd.keys.ACTION_PRESS:
            self.states[key] = True
        else:
            self.states[key] = False
        #endif    


class PerspectiveProjection(cameraWindow):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prog = self.ctx.program(
            vertex_shader='''
                #version 330

                uniform mat4 Mvp;

                in vec3 in_vert;

                void main() {
                    gl_Position = Mvp * vec4(in_vert, 1.0);
                }
            ''',
            fragment_shader='''
                #version 330

                out vec4 f_color;

                void main() {
                    f_color = vec4(0.1, 0.1, 0.1, 1.0);
                }
            ''',
        )

        self.mvp = self.prog['Mvp']
        self.vbo = self.ctx.buffer(grid(15, 10).astype('f4'))
        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert')


    def render(self, time, frame_time):
        self.move_camera(frame_time)

        self.ctx.clear(1.0, 1.0, 1.0)
        self.ctx.enable(moderngl.DEPTH_TEST)

        self.mvp.write((self.camera.mat_projection * self.camera.mat_lookat).astype('f4'))
        self.vao.render(moderngl.LINES)


if __name__ == '__main__':
    PerspectiveProjection.run()
