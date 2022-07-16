'''
    Renders a traingle that has all RGB combinations
    
    v2 = remove dependancies 
    v3 to v5 used modernGl_window camera window, but this messed with near and far
    v6 = using simple_camera, adapted from modernGl example
    v7 = to add many triangles.
    v8 = using index buffer
    v9 = create triangle strip
    v9b = used reversing triangle strip to avoid cross brace in wire frame mode
    v10 = add pygame gui with text
    v11 = display FPS via pygame gui
    v12 = turn strips into gully
    v13 = turn point trigger
    v14 = vectored turn points
    v15 = auto follow player (Space to pause on/off)
    v16 = introduce normals
    v17 = using corrected indices list from v9b
    v18 = added texture (press T) and fog
    v20 = sphere added
    v21 = sphere to follow track
    v22 = sphere color
    v23 = sphere class
    v24 = sphere shadow
    v25 = mouse move
    v26 = pseudo random track + correct camera follower
    v27 = side force stablility (fail)
    v28 = switch from track acc to track radius for side force calc.
    v29 = show force vector
    v30 = raise sides
    v31 = texture alpha (didn't help to see the ball through the track walls
    v32 = round wall edges
    v33 = tweak controls
    v34 = increase speed for corner cut, traffic lights, time record
    v35 = edge limits + game reset + best time
    v36 = zero G on fly, stoplight colour, no reverse, hint.
    v37 = text subroutine, GET READY, GET SET, GO
    v38 = balance interface
    v39 = more hints
    v40 = adjusted for 4 sensor balance
    v41 = 
    v42 = separate track to object3d class
    v43 = quad for player
    v44 = texture transparency
    v45 = add acc effect on texture height
    v46 = add grid
    v47 = correct edge detect
    v48 = first attempt at columns
    v49 = rh angle columns + track render Y option
    v50 = added down angle dampered
    v51 = player keeps going at the end line
    v52 = free flight after leaving track
    v53 = parafoil, free motion after end of track
    v54 = Limited parafoil to down only, fixed bug in LH side of track
    v55 = Periodic lighting using vertex colors, lowers foil on ground
    v56 = little tweaks
    v57 = show best run ahead of new
    v58 = dampen balance input
    v59 = add shadow foil, tweak best player, add player textures
    v60 = land back on track, fist pump on finish
    v61 = optimise track scan based on height
    v62 = fix better player progress and score display
    v63 = shadow when landing on track
    v64 = fix better self progress check, add track length option, widen ground area, fix title
'''

import numpy as np
import moderngl
from simple_camera import cameraWindow
from pathlib import Path
import math
import pyrr
from pyrr import Vector3, Matrix44
from random import randint

#for pygame
import pygame
from moderngl_window import geometry

#for info function
import json
import moderngl as mgl

def lerp(v1,v2,f):
  return (v2 - v1)*f + v1
#enddef 

def printVec(t,v):
  print(t,"%4.1f,%4.1f,%4.1f"%(v.x,v.y,v.z))
#enddef 

class Sphere():
    def __init__(self, ctx, rad = 0.4, **kwargs):
        self.ctx = ctx
        self.sphere = geometry.sphere(radius=rad)  #radius=0.5, sectors=32, rings=16, normals=True, uvs=True, name: str = None
        self.radius = rad
        shader_source = {
            'vertex_shader': '''
                #version 330

                uniform vec3 pos_offset;
                uniform vec3 scale;
                uniform Projection {
                    uniform mat4 matrix;
                } proj;

                uniform View {
                    uniform mat4 matrix;
                } view;

                in vec3 in_position;
                in vec3 in_normal;

                out vec3 normal;
                out vec3 pos;

                void main() {
                    vec4 p = view.matrix * vec4(in_position*scale + pos_offset, 1.0);
                    gl_Position =  proj.matrix * p;
                    mat3 m_normal = transpose(inverse(mat3(view.matrix)));
                    normal = m_normal * in_normal;
                    pos = p.xyz;
                }
            ''',
            'fragment_shader': '''
                #version 330

                in vec3 normal;
                in vec3 pos;
                uniform vec4 use_color;

                out vec4 f_color;

                void main() {
                    float l = dot(normalize(-pos), normalize(normal));
                    float s = (0.25 + abs(l) * 0.75);
                    f_color = vec4(vec3(use_color)*s,use_color.a);
                }
            ''',
        }
        self.prog1 = self.ctx.program(**shader_source)
        self.sphere_color = self.prog1['use_color']
        self.sphere_color.value = (1.0,1.0,0.0,1.0)
        self.sphere_scale = self.prog1['scale']
        self.sphere_scale.value = (1.0,1.0,1.0)
        self.sphere_offset = self.prog1['pos_offset']
        self.sphere_offset.value = (0, 0, 0)
        self.prog2 = self.ctx.program(**shader_source)
        self.shadow_color = self.prog2['use_color']
        self.shadow_color.value = (0.0,0.0,0.0,1.0)
        self.sphere_scale2 = self.prog2['scale']
        self.sphere_scale2.value = (1.0,0.0,1.0)
        self.shadow_offset2 = self.prog2['pos_offset']
        self.shadow_offset2.value = (0.1, -rad, 0)
        
        self.vao1 = self.sphere.instance(self.prog1)
        self.vao2 = self.sphere.instance(self.prog2)
        proj_uniform1 = self.prog1['Projection']
        view_uniform1 = self.prog1['View']
        proj_uniform2 = self.prog2['Projection']
        view_uniform2 = self.prog2['View']

        self.proj_buffer = self.ctx.buffer(reserve=proj_uniform1.size)
        self.view_buffer = self.ctx.buffer(reserve=view_uniform1.size)

        proj_uniform1.binding = 1
        view_uniform1.binding = 2
        proj_uniform2.binding = 1
        view_uniform2.binding = 2

        self.scope1 = self.ctx.scope(
            self.ctx.fbo,
            enable_only=moderngl.CULL_FACE | moderngl.DEPTH_TEST | moderngl.BLEND,
            uniform_buffers=[
                (self.proj_buffer, 1),
                (self.view_buffer, 2),
            ],
        )

        self.scope2 = self.ctx.scope(
            self.ctx.fbo,
            enable_only=moderngl.CULL_FACE | moderngl.DEPTH_TEST | moderngl.BLEND,
            uniform_buffers=[
                (self.proj_buffer, 1),
                (self.view_buffer, 2),
            ],
        )

    #enddef
    
    def move(self,pos):
        #rotation = Matrix44.from_eulers((time, time, time), dtype='f4')
        translation = Matrix44.from_translation((pos.x, pos.y+self.radius, pos.z), dtype='f4')
        modelview = translation #* rotation
        self.view_buffer.write(modelview)
    #enddef    

    def render(self, proj, time):
        #self.ctx.enable_only(moderngl.CULL_FACE | moderngl.DEPTH_TEST | moderngl.BLEND)
        self.proj_buffer.write(proj.tobytes())  #self.m_proj)
        with self.scope2:
            self.vao2.render(mode=moderngl.TRIANGLES)
        with self.scope1:
            self.vao1.render(mode=moderngl.TRIANGLES)
    #enddef
#endclass

class Object3d:
    def __init__(self, ctx, verts, indis, **kwargs):
        super().__init__(**kwargs)
        
        self.ctx = ctx

        self.prog = self.ctx.program(
            vertex_shader='''
                #version 330
                uniform mat4 Mvp;
                uniform vec3 pos_offset;
                uniform vec3 scale;
                
                in vec3 in_vert;
                in vec3 in_normal;
                in vec2 in_texcoord_0;
                in vec3 in_color;

                out vec3 v_vert;
                out vec3 v_norm;
                out vec2 v_text;
                out vec3 v_color;    // Goes to the fragment shader

                void main() {
                    gl_Position =  Mvp * vec4(in_vert*scale + pos_offset, 1.0);
                    v_vert = in_vert;
                    v_norm = in_normal;
                    v_color = in_color;
                    v_text = in_texcoord_0;
                }
            ''',
            fragment_shader='''
                #version 330
                uniform vec3 Light;
                uniform vec3 CameraPos;
                uniform vec4 FogColor;
                uniform float FogMax;
                uniform float FogMin;
                uniform sampler2D Texture;
                uniform bool UseLight;
                uniform bool UseFog;
                uniform bool ForceFog;
                uniform bool UseTexture;
                uniform float Alpha;

                in vec3 v_vert;
                in vec3 v_norm;
                in vec3 v_color;
                in vec2 v_text;

                out vec4 f_color;
                
                float getFogFactor(float d)
                {
                   if (d>=FogMax) return 1;
                   if (d<=FogMin) return 0;
                   return (d - FogMin) / (FogMax - FogMin);
                }

                void main() {
                    float d = distance(CameraPos, v_vert);
                    float lum = 1.0;
                    if(ForceFog) {
                       f_color = FogColor*1.0;
                       return;
                    }  
                    if (UseLight) {
                      lum = clamp(dot(normalize(Light - v_vert), normalize(v_norm)), 0.0, 1.0) * 0.8 + 0.2;
                    } 
                    if (UseTexture) {
                        vec4 tex = texture(Texture, v_text).rgba;
                        f_color = vec4(clamp(tex.x * (v_color.x + lum),0,1), clamp(tex.y * (v_color.y + lum),0,1), clamp(tex.z * (v_color.z + lum),0,1), tex.w*Alpha);
                    } else {
                        f_color = vec4(v_color * lum, Alpha);
                    }
                    if (UseFog) {
                      float fog = getFogFactor(d);
                      f_color = mix(f_color, FogColor, fog);
                    }  
                }
            ''',
        )
        vertices = np.array(verts,dtype='f4')
        #rint(vertices)
        indices = np.array(indis, dtype='i4')

        self.vbo = self.ctx.buffer(vertices)
        self.ibo = self.ctx.buffer(indices)

        self.mvp = self.prog['Mvp']
        self.scale = self.prog['scale']
        self.scale.value = (1.0,1.0,1.0)
        self.offset = self.prog['pos_offset']
        self.offset.value = (0, 0, 0)

        self.use_light = self.prog['UseLight']
        self.light = self.prog['Light']
        self.camPos = self.prog['CameraPos']
        self.use_fog = self.prog['UseFog']
        self.force_fog = self.prog['ForceFog']
        self.force_fog.value = False
        self.fogColor = self.prog['FogColor']
        self.fogMax = self.prog['FogMax']
        self.fogMin = self.prog['FogMin']
        self.setFog()
        self.use_texture = self.prog['UseTexture']
        self.alpha = self.prog['Alpha']
        self.alpha.value = 1.0
        # We control the 'in_vert' and `in_color' variables
        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                # Map in_vert to the first 3 floats
                # Map in_norm to the next 3 floats
                # Map in_color to the next 3 floats
                (self.vbo, '3f 3f 2f 3f', 'in_vert', 'in_normal', 'in_texcoord_0', 'in_color')
            ], self.ibo
        )
      #endif
    #enddef
    
    def setCamPos(self,pos):  #required for fog distance
        self.light.value = (-20,40,pos.z)
        self.camPos.value = (pos.x,pos.y,pos.z)
    #enddef
    
    def setFog(self,fogColor = (0.,0.,0.,1.), fog_max = 500, fog_min = 100):
        self.fogColor.value = fogColor
        self.fogMax.value = fog_max
        self.fogMin.value = fog_min
    #enddef
    
    def setShadow(self):
        self.fogColor.value = (0.,0.,0.,1.0)
        self.force_fog.value = True
    #endif
    
    def setScale(self,scale):
        self.scale.value = scale
    #enddef
    
    def setAlpha(self,alpha):
      self.alpha.value = alpha
    #enddef
 
    def use(self,lit,fogged,textured):
        self.use_light.value = lit
        self.use_fog.value = fogged
        self.use_texture.value = textured
    #enddef
      
    def render(self,proj,texture=None,render_mode=5):
        if texture != None:
          texture.use()
        self.mvp.write(proj)
        self.vao.render(render_mode)
    #enddef    
    
#endclass

alt_controller = None
background_img = ""
#full_screen = False
track_length = 1000

class GutterRun(cameraWindow):
    gl_version = (3, 3)
    window_size = (1280, 720)
    aspect_ratio = 16 / 9
    resizable = True
    title = "Gutter run"
    #fullscreen = full_screen
    render_mode = 5  #triangle strip
    wire_frame = False
    resource_dir = (Path(__file__)/ '..').absolute()
    last_gui_refresh = 0  #used for reducing gui refresh
    render_cnt = 0   #used to calc FPS
    pause = True 
    player_pos = Vector3([0,0,0])
    player_up = Vector3([0,1,0])  #what is down
    player_vel = Vector3([0,0,0])
    player_progress = 0
    track_pos = []
    track_vel = []
    track_tp = []
    track_edge = []
    track_concave_radius = 10.0
    track_start_pos = 10  #where the run time starts
    textured = True
    lit = True
    fogged = True
    sphere_rad = 1.0
    force = (0,0)
    forward_force_scale = 10.0  #the effect of mouse or platorm on forward speed
    player_tan = (0,1)  #cos and sin of player tough angle
    player_side_vel = 0.0
    player_side = 0  #meaning centre of gutter
    player_forward_vel = 0.0
    track_wall_radius = 10
    inv_quarter = math.pi*0.5 
    player_g = (0,1) 
    radius_multiplier = 1.0  #faster or slower due to radius of turn
    start_time = 0
    end_time = 0
    status = 0
    best_time = 0
    better_by = 0
    player_angle = [0,0,0]  #usually the same as track direction
    down_angle = 0
    render_track = True
    force_status = 0
    end_delay = 10  #how long the score is displayed before reset
    unit_scale = 0.5  #apply to get metres
    acc_to_m2s = 0.25
    rec = []
    best_rec = []
    last_rec_tm = 0
    rec_tm = 0
     
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Point coordinates are put followed by the vec3 color values
        verts = []
        self.camera._z_far = track_length
        self.camera.setDist(20)
        xl = 10  #track width in number of triangles
        
        #create track design
        tps = [] #[(10,10),(40,0),(50,-20),(80,0)]
        tp = 100
        td = 1
        while tp < track_length:
          tp += randint(10,200)
          tr = randint(20,100)
          tps.append((tp,tr*td))
          td = -td  #reverse direction for next bend
        #endwhile
        #tps = [(10,-10),(40,0),(50,10),(80,0)]
        #tps = [(0,10),(40,0),(50,0)]
        
        #build track from design
        drn = math.pi*-0.25  #right edge of track
        dr = drn  #standard right edge
        dln = math.pi*0.25   #left edge of track
        dl = dln  #standard left edge
        ddt = math.pi*0.5*10  #maxium change of edge for 10 radius
        w2 = xl/2
        self.track_gradient = 0.1
        cp = Vector3([0.,0.,0.]) #start position for centreline
        dv = Vector3([0.,-self.track_gradient,1.])  # 1 in 10 fall
        da = Vector3([0.,0.,0.])
        turn_point = cp  #radius around which track turns (none to start with)
        tpi = 0
        tpc = tps[tpi]
        radius = 0
        rc = 1.0
        cr = 0.0
        ddd = 0 #current edge adjust
        for zi in range(track_length): #fraction of track section length
          zc = 0.4+ 0.2*math.sin(zi*3.1415927/100)  #periodic track lighting 0.2 to 0.6
          if radius == 0:  #averange back to standard
            dr = dr*rc + drn*cr 
            dl= dl*rc + dln*cr 
          elif radius > 0:  #left hand turn
            dr = dr*rc + ddd*cr #raise rh side
            dl= dl*rc + dln*cr 
          else:             #right hand turn
            dr = dr*rc + drn*cr 
            dl = dl*rc + ddd*cr  #raise lh side
          #endif
          rc = rc*0.9 + 0.09  #trend to 0.9
          cr = 1.0 - rc
          #rint("zi:",zi,dr,dl)
          dw = dl - dr
          dd = dw /xl    
          for xi in range(xl+1): #fraction of track width/rotation angle
            xa = dr + xi*dd
            #rint(xa)
            sin = math.sin(xa)
            cos = math.cos(xa)
            xp = sin*self.track_concave_radius
            y = cp.y - cos*self.track_concave_radius
            x = cp.x + xp*dv[2]
            z = cp.z - xp*dv[0]
            verts +=[x,y,z, sin,cos,1.0, xi/xl,((zi%10)/10), zc*xi/xl,zc,zc]
          #endfor
          if zi == tpc[0]:  #new waypoint
            print("Waitpoint#",zi,tpc)
            rc = 1.0
            cr = 0.0
            radius = tpc[1]
            tpi += 1
            if tpi < len(tps):
              tpc = tps[tpi]
            #endif  
            if radius != 0:
              turn_point = cp + Vector3([dv.z,0,-dv.x])*radius
              #rint("CentrePoint = ",cp,"Turn point = ",turn_point," dv:",dv)
              if radius > 0:
                ddd = drn - ddt/radius  # rh edge target
              else:  
                ddd = dln - ddt/radius  # lh edge target
              #endif  
              print("radius:",radius," ddd:",ddd*10)
            else:
              ddd = 0  
            #endif  
          #endif
          if radius == 0:
            turn_point = cp 
          #endif   
          #rint("%4d: p[%0.1f,%0.1f] v[%0.1f,%0.1f] a[%0.1f,%0.1f]"%(zi,cp.x,cp.z,dv.x,dv.z,da.x,da.z))
          self.track_pos.append(cp)
          self.track_vel.append(dv)
          self.track_tp.append(turn_point)
          self.track_edge.append((dl,dr))
          #rint(cp,turn_point)
          if radius != 0:
            rv = cp - turn_point
            rv.normalize()  #vector to centre of radius
            #
            da = rv/abs(radius)  #turn acceleration
            dv = dv - Vector3([da.x,0,da.z])   #adjust vector of track direction
          #endif  
          dv.normalize()
          cp = cp + dv
        #endfor          
        #rint(verts)  
        indis = self.zigzagstrip(xl+1,track_length)
        self.track = Object3d(self.ctx,verts,indis)
        self.track_texture = self.load_texture_2d('cracks.jpg')
        #self.track.setFog((0,0,0,1),track_length,200)
        
        #create player object
        verts = [
            # x, y, z, norm_x, norm_y, norm_z, text_x, text_y, red, green, blue
           -2, 0, 0.0,    0.0, 0.0, -1.0,   1.0, 0.0,    1.0, 0.0, 0.0,
            2, 0, 0.0,    0.0, 0.0, -1.0,   0.0, 0.0,    0.0, 1.0, 0.0,
            2, 8, 0.0,    0.0, 0.0, -1.0,   0.0, 1.0,    0.0, 0.0, 1.0,
           -2, 8, 0.0,    0.0, 0.0, -1.0,   1.0, 1.0,    0.0, 0.0, 1.0,
        ]
        indi = [0, 1, 2, 2, 3, 0]
        self.player = Object3d(self.ctx,verts,indi)
        self.player.setCamPos(Vector3([0,0,0]))
        self.player.use(False,False,True)
        player_textures = ('skateboard2.png','skateboard3.png','skateboard4.png')
        self.player_textures = []
        for fid in player_textures:
          self.player_textures.append(self.load_texture_2d(fid))
        #endif  
        self.player_texture = 0
        self.player_height = 1.0
        
        #for background
        self.createOffScreenSurface()
        if len(background_img) > 0:
          self.quad_texture = self.load_texture_2d(background_img)
        #endif

        self.ground_y = self.track_pos[-1][1]-self.track_concave_radius  #last y value  (rounding errors means rate of fall is not reliable)
        
        #ground
        ground_length = track_length*2
        indis = [0,2,1,3]
        y = self.ground_y - 0.1
        verts = [-ground_length, y, -ground_length, 0, 1, 0,  0, 0,  0, 1, 0,  
                  ground_length, y, -ground_length, 0, 1, 0,  1, 0,  0, 1, 0,  
                 -ground_length, y,  ground_length, 0, 1, 0,  0, 1,  0, 1, 0,  
                  ground_length, y,  ground_length, 0, 1, 0,  1, 1,  0, 1, 0]  
        self.grnd = Object3d(self.ctx,verts,indis) 
        self.grnd.use(False,True,False)
        
        #create grid
        verts=[]
        indis=[]
        for z in range(-ground_length,ground_length,100):
          verts += [-ground_length, self.ground_y, z, 0, 1, 0,  0, 0,  1, 1, 0,
                     ground_length, self.ground_y, z, 0, 1, 0,  0, 0,  1, 1, 0]
        for x in range(-ground_length,ground_length,100):
          verts += [x, self.ground_y, -ground_length, 0, 1, 0,  0, 0,  0, 1, 1,
                    x, self.ground_y,  ground_length, 0, 1, 0,  0, 0,  0, 1, 1]
        #rint(verts)
        indis = list(range(len(verts)))
        #rint(indis_
        self.grid = Object3d(self.ctx,verts,indis) 
        self.grid.use(False,True,False)
        
        #create supports
        indis = [0,3,1,4,2,5]
        self.supports = []
        tw = 4
        for ti in range(0,track_length,100):
        #ti = 0
        #if True:
          tp = self.track_pos[ti]
          tv = self.track_vel[ti]*4
          x1 = tp.x-tv[2]/2
          x2 = tp.x+tv[2]/2
          x3 = tp.x+tv[2]/2+tv[0]*2
          z1 = tp.z+tv[0]/2
          z2 = tp.z-tv[0]/2
          z3 = tp.z+tv[0]/2+tv[2]*2
          y = tp.y-self.track_concave_radius
          verts = [x1,self.ground_y-self.track_gradient*tv[0],                   z1, 1, 0, 0, 0, 0, 1, 0, 0,
                   x2,self.ground_y,                                      z2, 1, 0, 0, 0, 0, 1, 1, 0,
                   x3,self.ground_y-self.track_gradient*tv[2],                   z3, 1, 0, 0, 0, 0, 1, 0, 1,
                   x1,y,                z1, 1, 0, 0, 0, 0, 0, 1, 0,
                   x2,y,                z2, 1, 0, 0, 0, 0, 0, 0, 1, 
                   x3,y-self.track_gradient*tw*2,z3, 1, 0, 0, 0, 0, 0, 1, 1]
          #rint(verts)
          #rint(indis)
          support = Object3d(self.ctx,verts,indis)
          self.supports.append(support)
        #endfor
        
        #create parafoil
        fw = 20  #foil panels wide
        fd = 6   #foil panels deep
        r1 = 15
        r2 = r1*r1
        verts = []   #for foil
        lverts = []  #for lines
        for zi in range(fd+1):
          b = zi/fd
          r = 1 - b
          z = zi-fd/2
          for xi in range(fw+1):          
            x = xi-fw/2
            y = math.sqrt(r2 - x*x - z*z)
            if (xi & 1) == 0:
              y -= 0.2
              g = 0
              if zi == 0 or zi == fd:  #parachute lines
                lverts += [x, y, z, 0, 0, 0,  0, 0,  0.2, 0.2, 0.2,
                           0, 0, z/fd, 0, 0, 0,  0, 0,  0.2, 0.2, 0.2]
              #endif
            else:
              y += 0.2
              g = 0
            #endif
            verts += [x, y, z,  0, 0, 1,  xi/fw, zi/fd, r, g, b]
          #endfor
        #endfor                     
        indis = self.zigzagstrip(fw+1,fd+1)
        lindis = list(range(len(verts)))
        self.parafoil = Object3d(self.ctx,verts,indis)
        self.parafoil.use(True,False,False)
        self.parashadow = Object3d(self.ctx,verts,indis)
        self.parashadow.use(True,False,False)
        self.parashadow.setScale((1.0,0.0,1.0))
        self.parashadow.setShadow()
        self.paralines = Object3d(self.ctx,lverts,lindis)
        self.paralines.use(False,False,False)
        self.foil_scale = [0.2,0.0]
        
        pygame.font.init()
        #rint(pygame.font.get_fonts())
        self.font = pygame.font.Font(None,24)
        self.font2 = pygame.font.Font(None,48)
        #self.font = pygame.font.SysFont('arial',24)
        #self.font2 = pygame.font.SysFont('arial',48)

        #self.sphere = Sphere(ctx=self.ctx,rad=self.sphere_rad)
        self.reset()
    #enddef
    
    def zigzagstrip(self,xl,zl):
        #generate index data    
        indi = []      
        #Note: this indexing system will not work with back face culling
        for z in range(zl-1):
          if (z & 1) == 0:
            for x in range(xl):
              #One part of the strip
              indi.append((z * xl) + x)
              indi.append(((z + 1) * xl) + x)
            #endif
          else:  
            for x in range(xl-1,-1,-1):
              #One part of the strip
              indi.append((z * xl) + x)
              indi.append(((z + 1) * xl) + x)
            #endif
        #endif
        #rint(indi)
        return indi
    #enddef    

    def close(self):
        if alt_controller != None:
           alt_controller.close()
        #endif
    #enddef
        
    def createOffScreenSurface(self):
        # Create a 24bit (rgba) offscreen surface pygame can render to
        self.pg_screen = pygame.Surface(self.window_size, flags=pygame.SRCALPHA)
        # 24 bit (rgba) moderngl texture
        self.pg_texture = self.ctx.texture(self.window_size, 4)
        self.pg_texture.filter = moderngl.NEAREST, moderngl.NEAREST

        self.texture_program = self.load_program('texture.glsl')
        self.quad_fs = geometry.quad_fs()
        
    def reset(self):
        self.player_pos = Vector3([0,0,0])
        self.player_vel = Vector3([0,0,0])
        self.player_progress = 0
        self.player_forward_vel = 0
        self.player_side_vel = 0.0
        self.player_side = 0  #meaning centre of gutter
        self.foil_scale = [0.2,0.0]
        self.resetCamera() 
        self.rec_tm = 0
        self.last_rec_tm = -1           
        self.player_texture = 0
        self.end_time = 0
    #endif    

    def render(self, time: float, frame_time: float):
        global alt_controller
        rtm = 1.0-frame_time  #used for gradual changes 
        if alt_controller != None:
          f = alt_controller.getForce(frame_time)
          #rint("Force:",f)
          if f == None:  #no ardu found
            alt_controller = None
          else:
            self.force = f
            if alt_controller.isActive():
              if self.pause:
                self.pause = False
                print("Weight on")
            elif not self.pause:
              self.status = 0
              self.pause = True
              self.reset() 
            #endif  
          #endif  
        #endif
        self.shadow_y = self.ground_y+0.1
        self.shadow_scale = 1.0
        if self.pause:
          self.move_camera(frame_time*1000)  #manual control
          self.player_forward_vel = 0
        else:
          vel_lng = self.player_vel.length
          if vel_lng == 0:
            forward = Vector3([0,0,1])
          else:  
            forward = self.player_vel*1
            forward.normalize()
          #endif  
          if self.status == 0:
            self.start_time = time
            self.status = 1
            #rint("Get ready:",self.start_time)
          elif self.status < 3:
            st = int(time - self.start_time)
            if st > 0:
              self.status = st
            #endif  
            #rint("Status:",self.status)
          elif not self.pause:
            self.rec_tm += frame_time
          #endif
          
          if self.status < 5:
            self.player_progress += frame_time*self.player_forward_vel*self.radius_multiplier
            self.player_forward_vel += self.force[1]*-self.forward_force_scale*frame_time
            if self.player_forward_vel < 0:
              self.player_forward_vel = 0  #no going backwards
            #endif
          else: #off track
            self.player_pos += self.player_vel*frame_time   
            self.player_angle[2] = math.atan2(-forward.x,forward.z)  #set horizontal direction
            cp = Vector3([self.player_pos.x,self.player_pos.y+self.track_concave_radius-2,self.player_pos.z])
            self.setCameraPos( cp,  forward, self.player_up)
            self.player_angle[1] = self.player_angle[1]* rtm + -min(1.0,max(-1.0,self.force[0]))*frame_time
            rm = Matrix44.from_y_rotation(self.force[0]*frame_time)
            self.player_vel = rm * self.player_vel
            if self.status == 6:  #free flight
              if self.player_pos.y < self.ground_y:
                #rint(self.player_pos)
                print("Landed with deltaY:%0.1f unit/sec"%(self.player_vel.y,))
                self.player_pos.y = self.ground_y + 0.1
                self.player_vel.y = 0
                self.end_time = time
                self.status = 5
                self.player_texture = 0  #back on ground mode
                return #skip this render
              #endif
              if self.force_status == 0:
                match1 = 0
                match2 = 0
                match3 = 0
                #get target height
                ps = int((self.player_pos.y + self.track_concave_radius)/-self.track_gradient)
                #get lower track that matches
                pe = int((self.player_pos.y + self.track_concave_radius - 10)/-self.track_gradient)
                tl = len(self.track_pos)-1
                #rint("Scan range:",ps,pe)
                ps = max(0,min(tl,ps))
                pe = max(0,min(tl,pe))
                for pi in range(ps,pe):
                  track_pos = self.track_pos[pi]
                  ty = track_pos[1] - self.track_concave_radius
                  #if pi == 0:
                  '''if self.player_pos.y < ty - 1:  #temporary -1
                    continue  #below the track
                  if self.player_pos.y > ty + 4:
                    continue  #below the track'''
                  #rint("Height ok:%d P=(%d,%d,%d) T=(%d,%d,%d)"%(pi,self.player_pos.x,self.player_pos.y,self.player_pos.z,track_pos.x,ty,track_pos.z))  
                  match1 += 1  
                  track_forward = self.track_vel[pi]*1
                  track_forward.normalise()
                  tx = abs(track_forward.x)*4 + 1
                  if self.player_pos.x < (track_pos.x - tx):
                    continue  #too far left
                  if self.player_pos.x > (track_pos.x + tx):
                    continue  #too far right
                  match2 += 1  
                  tz = abs(track_forward.z)*4 + 1
                  if self.player_pos.z < (track_pos.z - tz):
                    continue  #too far left
                  match3 += 1  
                  #rint("Height & x ok:",pi,track_forward,self.player_pos.z,track_pos.z)  
                  if self.player_pos.z > (track_pos.z + tz):
                    continue  #too far right
                  #within range of shadow
                  self.shadow_y = ty + 0.3
                  self.shadow_scale = 0.3
                  #rint("Drop:",self.player_pos.y - ty)  
                  if self.player_pos.y > ty + 1:
                    continue  #too far above track'''
                  print("Landed on track at:",pi)  
                  self.player_progress = pi
                  self.player_forward_vel = self.player_vel.length
                  self.player_side_vel = 0
                  self.player_side = 0
                  self.status = 4  #back on track
                  self.player_texture = 0
                  self.foil_scale[1] = 0
                  #rint(track_pos)
                  return  #skip this render
                #endif
                #rint("Match ",match1,match2,match3)
              #endif  
              hv = Vector3([self.player_vel.x,(self.force[1]-0.5)*4,self.player_vel.z])
              hv.normalize()
              self.player_vel = hv * vel_lng 
              #rm = Matrix44.from_x_rotation((self.force[1])*frame_time)
              #self.player_vel = rm * self.player_vel
              hf = math.sqrt(forward.x*forward.x + forward.z*forward.z)
              pa = math.atan2(forward.y,hf)
              #rint(pa)
              self.player_angle[0] = pa
              g = Vector3([0,-9.8,0])
              gc = g | forward
              #rint("Gc:",gc)
              #raise the foil
              if self.foil_scale[0] < 1.0:  #deploy the foil
                self.foil_scale[0] += frame_time
              else:
                self.foil_scale[0] = 1.0
                if self.foil_scale[1] < 1.0:  #spread the foil
                  self.foil_scale[1] += frame_time
                else:
                  self.foil_scale[1] = 1.0
                #endif    
              self.player_vel += forward*(gc - vel_lng*vel_lng*0.03)*frame_time #gravity - friction
            else:  #mode 5
              #lower the foil
              if self.foil_scale[1] > 0.3:  #collapse the foil
                self.foil_scale[1] -= frame_time
                self.foil_scale[0] -= frame_time
              #endif
              if vel_lng > 1.0:  #slow down
                self.player_vel -= forward*0.1*frame_time
              #endif
              if self.end_time > 0: #so course complete
                if int(time) & 1 == 0:
                  self.player_texture = 0
                else:
                  self.player_texture = 1
                #endif
              #endif
            #endif
            '''if not self.pause:
              print("Vel:%0.1f"%(vel_lng)) 
              printVec("Forward:",forward)
              printVec("Pos:",self.player_pos)
              #rint("Grnd:",self.ground_y)'''
            #endif
            ##self.player_vel.x -= (forward.z*self.force[0]*10)*frame_time  # - forward.x*cf
            #self.player_vel.z -= (forward.x*self.force[0]*10)*frame_time  #  - forward.z*cf
          #endif  
        #endif  
        if self.status < 5:      
            (pf, pi) = math.modf(self.player_progress)
            pi = int(pi)
            if pi > self.track_start_pos:
              if self.status == 3:
                self.status = 4
                self.start_time = time
            #endif  
            #rint("Progress:",pi)
            if pi < 0:  #at start of track
              pi = 0
              self.reset()
            elif pi >= len(self.track_pos):  #end of track
              pi = len(self.track_pos)-1  #for the moment
              if self.status == 4:
                self.status = 5
                self.player_texture = 1  #victory mode
                self.end_time = time
                tm = self.end_time - self.start_time
                self.better_by = self.best_time - tm
                if (self.best_time == 0) or (tm < self.best_time):
                   self.best_time = tm
                   self.best_rec = tuple(self.rec)  #make a copy
                #endif 
                self.player_vel = self.track_vel[-1] * self.player_forward_vel
                self.player_vel[1] = 0
              #endif  
              #may try to join or jump between tracks
              return #skip render for this loop
            #endif 
            track_pos = self.track_pos[pi]
            #rint(track_pos)
            track_forward = self.track_vel[pi]*1
            self.player_angle[2] = math.atan2(-track_forward.x,track_forward.z)
            if pi+1 < len(self.track_pos):
              track_pos = lerp(track_pos, self.track_pos[pi+1], pf)
              #track_pos = pyrr.vector.interpolate(track_pos, self.track_pos[pi+1], pf)
              track_forward = lerp(track_forward, self.track_vel[pi+1],pf)
            track_forward.normalize()  
            #rint(track_pos)
            if not self.pause:
              #rint("Setpos:",track_pos, track_forward)
              cp = Vector3([track_pos.x,track_pos.y-2,track_pos.z])
              self.setCameraPos( cp,  track_forward, self.player_up)
            #endif  
            #rint("pp:",self.player_pos)
            track_tan = Vector3([track_forward.z,track_forward.y,-track_forward.x]) 
            #rint("TP:",track_pos)
            self.player_pos = track_pos*1  #copy track pos then adjust
            ds = -self.track_concave_radius*self.player_tan[0]
            self.player_pos.x += ds*track_tan.x  #radius of track
            self.player_pos.z += ds*track_tan.z  #radius of track
            self.player_pos.y -= self.track_concave_radius*self.player_tan[1]  #radius of track
            #endif
            acc_vec = self.track_tp[pi]-self.track_pos[pi]
            #rint("Acc vec:",acc_vec)
            radius = acc_vec.length
            turn_acc = 0
            if radius != 0:
              turn_acc = self.player_forward_vel*self.player_forward_vel/radius
              #rint(self.track_tp[pi],self.track_pos[pi], radius)
              player_delta = self.track_tp[pi] - self.player_pos
              player_delta.y -= self.track_concave_radius
              player_radius = player_delta.length
              #rint("Radius: %0.1f Player_radius:%0.1f"%(radius,player_radius))
              if player_radius > 0:
                self.radius_multiplier = radius/player_radius
              else:
                self.radius_multiplier = 1.0
              #endif  
            else:
              self.radius_multiplier = 1.0
            #endif  
            if radius > 0:
              acc_vec.normalize()
              c_force = acc_vec*turn_acc
              #rint("Acc vec:",acc_vec,radius)
            else:
              c_force = Vector3()
            #endif    
            side_force = c_force | track_tan #get lateral component
            g_force = side_force/9.8  #both centrifugal and gravity out by a factor of 0.25, so evens out
            self.player_g = Vector3([g_force,4,0])
            g_angle = math.atan2(g_force,4)
            #if not self.pause:
            #  print("G:%0.1f %3d",g_force,math.degrees(g_angle))
            #rint("Acc vec:",acc_vec,side_force,self.player_forward_vel)
            angle_in_trough = self.player_side*self.inv_quarter
            #rint("Angle:%4d Side:%0.1f Force:%0.1f"%(math.degrees(angle_in_trough),self.player_side,self.force[1]))
            self.down_angle = self.down_angle*rtm + g_angle*frame_time
            #the effect of player input on player angle is reduced as the g_force increases 
            self.player_angle[1] = self.down_angle - min(0.5,max(-0.5,self.force[0]))/self.player_g.length
            self.player_tan = (math.sin(angle_in_trough), math.cos(angle_in_trough))
            centering_acc = self.player_tan[0]*10
            side_acc = side_force*abs(self.player_tan[1]) 
            #print("SF:",side_force,"SA:",side_acc)
            self.player_side_vel *= (1.0-frame_time*10)  #adding a bit of friction
            '''if self.pause:
              player_multiplier = 40  #to help with testing
            #  print("Angle:%4d LH:%4d RH:%4d:"%(math.degrees(-angle_in_trough),math.degrees(self.track_edge[pi][0]),math.degrees(self.track_edge[pi][1])))
            else:'''
            player_multiplier = 10
            #endif  
            self.player_side_vel += (self.force[0]*player_multiplier - centering_acc + side_acc*0.3)*frame_time  #effect of centrifugal forces and gravity
            self.player_side += self.player_side_vel*frame_time
            #if not self.pause:
            if -angle_in_trough > self.track_edge[pi][0] or -angle_in_trough < self.track_edge[pi][1] or (self.force_status == 6 and self.status != 6):
              #self.pause = True
              #rint("Edge flip:",self.player_side,self.track_edge[pi])
              self.status = 6  #over the edge
              self.player_texture = 2  #for parafoil
              vs = track_tan * self.player_side_vel * self.player_tan[0]
              vy = self.player_side_vel * self.player_tan[1]
              vf = track_forward * self.player_forward_vel
              v = vs + vf
              self.player_vel = Vector3([v.x,vy,v.z])  #Vector3([0,0,0])
              print("Escape vel:",self.player_vel)
              self.player_g = Vector3()
              #self.end_time = time - no score if still flying
            #endif  
            #print("Angle:",angle_in_trough," Side:",self.player_side,self.player_tan)'''
        #endif
        if self.status == 5 and self.force_status == 0: #wait for restart
          if (time - self.end_time) > self.end_delay:
            self.status = 0
            self.pause = True
            self.reset()
          #endif
        #endif      
        
        #the actual rendering bit
        self.ctx.clear(0.0, 0.0, 0.0)
        self.ctx.enable(moderngl.BLEND)

        # Render background graphics
        if len(background_img) > 0:
          self.quad_texture.use()
          self.texture_program['texture0'].value = 0
          self.quad_fs.render(self.texture_program)
        #endif  
        
        self.ctx.wireframe = self.wire_frame
        self.ctx.enable(moderngl.DEPTH_TEST )
        
        proj = (self.camera.mat_projection * self.camera.mat_lookat).astype('f4')

        self.grnd.setCamPos(self.player_pos)        
        #rint(self.light.value)
        self.grnd.render(proj)
        self.grid.setCamPos(self.player_pos)        
        #rint(self.light.value)
        self.grid.render(proj,self.track_texture,moderngl.LINES)
        
        for support in self.supports:
          support.setCamPos(self.player_pos)        
          support.render(proj,self.track_texture,self.render_mode)
        #endfor  

        
        self.track.setCamPos(self.player_pos)        
        #rint(self.light.value)
        self.track.use(self.lit,self.fogged,self.textured)
        #self.track.render(proj,self.track_texture,self.render_mode)
        #experiment to overlay wireframe, 
        #self.ctx.wireframe = True   #the colour is still the same
        if self.render_track:
          self.track.render(proj,self.track_texture,self.render_mode)
        #endif
        
        if self.status < 5:  #shrink and grow man to simulate squating for speed
          target_height = (max(0.5,min(1.5,1.0+self.force[1])))
        else:
          target_height = 1.0
        #endif    
        self.player_height = 0.9*self.player_height + target_height*0.1
        pos = self.player_pos * 1
        translation = Matrix44.from_translation(pos, dtype='f4')
        hrot = Matrix44.from_eulers((self.player_angle[0], 0, self.player_angle[2]), dtype='f4')
        roll = Matrix44.from_eulers((0,self.player_angle[1],0), dtype='f4')

        #if parafoil modes
        #pos.y += self.track_concave_radius
        if self.foil_scale[1] > 0:
          sc = (self.foil_scale[0],self.foil_scale[1],self.foil_scale[0])
          self.parafoil.scale.value = sc
          self.parafoil.setCamPos(pos)
          trans2 = Matrix44.from_translation(Vector3([0,6,0]), dtype='f4')
          self.parafoil.render(proj*translation*hrot*roll*trans2)
          self.paralines.scale.value = sc
          self.paralines.setCamPos(pos)
          self.paralines.render(proj*translation*hrot*roll*trans2,self.track_texture,moderngl.LINES)
          if self.player_pos[1] < self.shadow_y+10:  #show shadow
            self.parashadow.setCamPos(pos)
            ss = min(self.shadow_scale,self.foil_scale[0])  #make shadow smaller if shadow is onto track
            sc = (ss,0,ss)  #scale in x and z directions
            self.parashadow.scale.value = sc
            trans3 = Matrix44.from_translation(Vector3([pos[0],self.shadow_y,pos[2]]), dtype='f4')
            hrot2 = Matrix44.from_eulers((0, 0, self.player_angle[2]), dtype='f4')
            self.parashadow.render(proj*trans3*hrot2,self.track_texture)
          #endif  
        #endif

        #pos.y -= self.track_concave_radius
        #rint(self.player_pos,pos)
        player_rendered = False
        if self.status < 5: # still on track so record progress
          int_rec_tm = int(math.floor(self.rec_tm))
          if int_rec_tm > self.last_rec_tm:
            self.rec.append((self.player_pos*1,tuple(self.player_angle),self.player_progress,self.player_height))
            self.last_rec_tm = int_rec_tm
          #endif  
          if int_rec_tm < len(self.best_rec) and int_rec_tm > 0.5:
            best = self.best_rec[int_rec_tm]
            #print(int_rec_tm,self.best_rec[int_rec_tm][0])
            #if int_rec_tm > 0:
            #  print(int_rec_tm-1,self.best_rec[int_rec_tm-1][0])
            bpos = best[0]*1  #make a copy first
            bprog = best[2]
            if (int_rec_tm+1) < len(self.best_rec):
              best2 = self.best_rec[int_rec_tm+1]
              dt = self.rec_tm - int_rec_tm
              bpos += (best2[0]-bpos)*dt
              bprog += (best2[2]- bprog)*dt
              #if not self.pause:
              #  print("Best:",best2[0],best[0],int_rec_tm,(self.rec_tm - int_rec_tm))
            #endif  
            if bprog < self.player_progress:  #the best player is behind
              #rint("Render player first")
              self.player.scale.value = (1.0,self.player_height,1.0)
              self.player.setCamPos(pos)
              self.player.render(proj*translation*hrot*roll, self.player_textures[self.player_texture])  #roll needs to be last
              player_rendered = True
            #endif
            self.player.scale.value = (1.0,best[3],1.0)
            #rint("Best roll:",best[1][1])
            bhrot = Matrix44.from_eulers((best[1][0], 0, best[1][2]), dtype='f4')
            broll = Matrix44.from_eulers((0,best[1][1],0), dtype='f4')
            btranslation = Matrix44.from_translation(bpos, dtype='f4')
            self.player.alpha.value = 0.5
            self.player.render(proj*btranslation*bhrot*broll, self.player_textures[0])  #roll needs to be last
            self.player.alpha.value = 1.0
          #endif  
        #endif     
        if not player_rendered:
          #rint("Render player after")
          self.player.scale.value = (1.0,self.player_height,1.0)
          self.player.setCamPos(pos)  #only required for fog
          self.player.render(proj*translation*hrot*roll, self.player_textures[self.player_texture])  #roll needs to be last
        #endif  
        self.ctx.enable_only(moderngl.BLEND | moderngl.DEPTH_TEST)

        self.ctx.wireframe =  False
        # Render foreground objects
        self.pg_texture.use()
        self.render_cnt += 1
        if time > (self.last_gui_refresh+0.2):  #200mS refresh
          fps = self.render_cnt/(time - self.last_gui_refresh)
          self.render_pygame(time,fps)
          self.last_gui_refresh = time
          self.render_cnt = 0
        #endif  
        self.quad_fs.render(self.texture_program)     
        self.ctx.disable(moderngl.BLEND)
    #enddef   
    
    def print(self, txt, loc, col = (255,255,255), font = None):
      if font == None:
        font = self.font
      text = font.render(txt, True, col)
      text = pygame.transform.flip(text, False, True)  # Flip the text vertically.
      self.pg_screen.blit(text, loc) 
    #end 
        
    def render_pygame(self, time, fps):
        """Render to offscreen surface and copy result into moderngl texture"""
        self.pg_screen.fill((0, 0, 0, 0))  # Make sure we clear with alpha 0!
        '''N = 8
        for i in range(N):
            time_offset = 6.28 / N * i
            pygame.draw.circle(
                self.pg_screen,
                ((i * 50) % 255, (i * 100) % 255, (i * 20) % 255),
                (
                    math.sin(time + time_offset) * 200 + self.window_size[0] // 2,
                    math.cos(time + time_offset) * 200 + self.window_size[1] // 2),
                math.sin(time) * 7 + 15,
            )'''
        # draw acceleration vector    
        cw = self.window_size[0] // 2
        ch = self.window_size[1] - 50
        gp = (cw+self.player_g.x*20,ch-self.player_g.y*20)    
        gs = self.player_g.length*self.acc_to_m2s
        if gs < 2:
          gc = (0,255,0)
        elif gs < 6:
          gc = (0,255,255)
        else:
          gc = (0,255,0)
        #endif        
        pygame.draw.line(self.pg_screen, gc,(cw,ch),gp,5)
        pygame.draw.circle(self.pg_screen,gc,gp,10) 
        self.print("G:%3.1f"%(gs,),(cw-50, ch),gc)
        
        #draw stop lights
        if self.status < 4:
            rc = (0,64,64)
            yc = (0,48,64)
            gc = (0,64,0)
            rl = (50,self.window_size[1]-50)
            yl = (50,self.window_size[1]-150)
            gl = (50,self.window_size[1]-250)
            if self.status == 1:
              rc = (0,0,255)
              self.print("GET READY", (100,self.window_size[1]-50),rc,self.font2)
            elif self.status == 2:
              yc = (0,196,255)
              self.print("GET SET",(100,self.window_size[1]-150),yc,self.font2)
            elif self.status == 3:
              gc = (0,255,0)
              self.print("GO",(100,self.window_size[1]-250),gc,self.font2)
              if alt_controller != None:
                self.print("Lean forwards",(200,self.window_size[1]-250),gc,self.font2)
            #endif    
            pygame.draw.circle(self.pg_screen,rc,rl,40) 
            pygame.draw.circle(self.pg_screen,yc,yl,40) 
            pygame.draw.circle(self.pg_screen,gc,gl,40) 
        #endif
            
        if self.pause:
            self.print("PAUSED", (self.window_size[0]-200, self.window_size[1]-100), (255,255,0), self.font2)
            if alt_controller == None:
              self.print("Press space to begin", (self.window_size[0]-350, self.window_size[1]-140), (255,255,0), self.font2)
            else:
              self.print("Step on balance platform", (self.window_size[0]-450, self.window_size[1]-140), (255,255,0), self.font2)
            #endif
        elif self.status >= 4:            
            v_col = (0,0,255)
            if self.status == 4:
              v = self.player_forward_vel
            else:
              v = self.player_vel.length
            #endif    
            self.print("Speed: %5.1f km/hr"%(v*self.unit_scale*3.6), (self.window_size[0]-300, self.window_size[1]-100), v_col, self.font2)
            if self.status == 5 and self.end_time > 0:
              tm = self.end_time - self.start_time
              tm_col = (255,0,255)    
              self.print("Time:  %5.1f sec"%(tm,), (self.window_size[0]-300, self.window_size[1]-150), tm_col, self.font2)
            else:  #mode 4 or 6
              tm = time-self.start_time
              tm_col = (255,255,255)
              self.print("Time:  %5.1f sec"%(tm,), (self.window_size[0]-300, self.window_size[1]-150), tm_col, self.font2)
            #endif
            if self.status == 5:  #fini
              if self.best_time > 0 and self.end_time > 0:
                if self.better_by > 0:
                  self.print("Better by",(self.window_size[0]-500, self.window_size[1]-200),(0,128,128),self.font2)
                  self.print("%5.1fSec"%(self.better_by,), (self.window_size[0]-200, self.window_size[1]-200),(0,255,255),self.font2)
                else:  
                  self.print("Today's best time", (self.window_size[0]-500, self.window_size[1]-200),(0,128,255),self.font2)
                  self.print("%5.1fSec"%(self.best_time,), (self.window_size[0]-200, self.window_size[1]-200),(0,128,255),self.font2)
                #endif
              #endif
              self.print("Restart in %d seconds"%(self.end_delay + self.end_time - time), (self.window_size[0]-500, self.window_size[1]-250),(0,128,0),self.font2)
            elif self.status == 6:
              alt = (self.player_pos.y-self.ground_y)*self.unit_scale
              dv = self.player_vel.y*self.unit_scale
              self.print("Alt: %3.0f m Delta: %5.1f m/s"%(alt,dv), (self.window_size[0]-300, self.window_size[1]-180), v_col, self.font)
              self.print("Angle %3d %3d %3d"%(math.degrees(self.player_angle[0]),math.degrees(self.player_angle[1]),math.degrees(self.player_angle[2])), (self.window_size[0]-300, self.window_size[1]-210), v_col, self.font)
          #endif    
        #endif    
            
        self.print("FPS:%0.1f"%(fps,),(20, 20), (255,255,255))

        self.print("RadiusMultiplier:%0.2f"%(self.radius_multiplier,), (200, 20), (255,255,0))
        if self.pause:
          self.print("Hint:Hug the curves", (400, 20), (255,255,0))
        #endif

        # Get the buffer view of the Surface's pixels
        # and write this data into the texture
        texture_data = self.pg_screen.get_view('1')
        self.pg_texture.write(texture_data)

    def key_event(self, key, action, modifiers): 
        super().key_event(key, action, modifiers)
        print("Key:",key)
        keys = self.wnd.keys
        #print(dir(keys))
        #'A', 'ACTION_PRESS', 'ACTION_RELEASE', 'B', 'BACKSLASH', 'BACKSPACE', 'C', 'CAPS_LOCK', 'COMMA', 'D', 'DELETE', 'DOWN', 'E', 'END', 'ENTER', 'EQUAL', 'ESCAPE', 'F', 'F1', 'F10', 'F11', 'F12', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'G', 'H', 'HOME', 'I', 'INSERT', 'J', 'K', 'L', 'LEFT', 'LEFT_BRACKET', 'M', 'MINUS', 'N', 'NUMBER_0', 'NUMBER_1', 'NUMBER_2', 'NUMBER_3', 'NUMBER_4', 'NUMBER_5', 'NUMBER_6', 'NUMBER_7', 'NUMBER_8', 'NUMBER_9', 'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4', 'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 'NUMPAD_9', 'O', 'P', 'PAGE_DOWN', 'PAGE_UP', 'PERIOD', 'Q', 'R', 'RIGHT', 'RIGHT_BRACKET', 'S', 'SEMICOLON', 'SLASH', 'SPACE', 'T', 'TAB', 'U', 'UP', 'V', 'W', 'X', 'Y', 'Z'
        if action == keys.ACTION_PRESS:
            if key == keys.SPACE:
              self.pause = not self.pause
            elif key == keys.M:
              self.render_mode += 1
              print("Render Mode:",self.render_mode)
            elif key == keys.N:
              self.render_mode -= 1
              print("Render Mode:",self.render_mode)
            elif key == keys.L:
              self.lit = not self.lit
            elif key == keys.G:
              self.fogged = not self.fogged
            elif key == keys.H:
              self.wire_frame = not self.wire_frame
              print("Wire Frame:",self.wire_frame)
            elif key == keys.I:
              self.info()
            elif key == keys.P:
              self.player_progress = 0
            elif key == keys.T:
              self.textured = not self.textured
            elif key == keys.Y:
              self.render_track = not self.render_track
            elif key >= keys.NUMBER_0 and key <= keys.NUMBER_9:
              self.force_status = key - keys.NUMBER_0
            #endif  
        #endif
            
    def info(self):
        print('Info:', json.dumps(self.ctx.info, indent=2))
        print('Extensions:', self.ctx.extensions)
       # print('Hardware Info:', json.dumps(mgl.hwinfo(self.ctx), indent=2))
        print('Version Code:', self.ctx.version_code)
        
    def mouse_position_event(self, x: int, y: int, dx, dy):
        #rint(x,y)
        max_dim = max(self.window_size[0],self.window_size[1])
        if alt_controller == None:      
          self.force = ((x- self.window_size[0]/2)/max_dim,(y- self.window_size[1]/2)/max_dim)
          if print_force:
            print("Force:%0.1f,%0.1f"%tuple(self.force))
          #endif
        #endif
    #enddef      

    def mouse_release_event(self, x, y, button):
        if alt_controller == None:      
          self.force = (0,0)
        #endif  
    #enddef    
#endclass

import sys   
if __name__ == '__main__':
    com_port = None
    #fullScreen = False
    print_com = False
    print_force = False
    num_sensors = 4
    force_scale = (4,6)
    if len(sys.argv) > 1:
      nextArg = ' '
      args = [sys.argv[0]] #this will be the list passed to moderngl
      for argv in sys.argv[1:]:
        remove = False
        if nextArg != ' ' and argv.startswith(' '):
          util.log('You failed to enter argument for option:' + nextArg)
          exit(4)
        #endif
        elif nextArg == 'b':
          background_img = argv
          nextArg = ""
          args = args[:-1]
          remove = True
        elif argv == "-a":
          print_force = True
          remove = True
        elif argv == "-d":
          print_com = True
        # -c BOOL used by moderngl for enable disable cursor
        # -fs for fullscreen
        # -r BOOL ,,   ,,  ,,       ,,   ,,      ,,   resize
        # -s ,,   ,,  ,,       ,, samples for multi sampling
        # -vs BOOL enable or disable vsync
          remove = True
        elif argv == "-h":
          print("Arguments:")
          print(" -a = print force")
          print(" -b bacground_img")
          print(" -d = print com")
          print(" -m x,y = force scale")
          print(" -p com_port")
          print(" -l num_sensors")
          print(" -t track_length")
        elif nextArg == 'm':
          ap = argv.split(",")
          if len(ap) != 2:
            print("Force scale = x,y")
            exit(1)
          #endif  
          force_scale = (float(ap[0]),float(ap[1]))
          nextArg = ""
          args = args[:-1]
          remove = True
        elif nextArg == 'p':
          com_port = argv
          nextArg = ""
          args = args[:-1]
          remove = True
        elif nextArg == 'l':
          num_sensors = int(argv)
          nextArg = ""
          args = args[:-1]
          remove = True
        elif nextArg == 't':
          track_length = int(argv)
          nextArg = ""
          args = args[:-1]
          remove = True
        #elif argv == "-f":  #already covered internally with -fs or press F11
        #  full_screen = True
        elif len(argv) == 2 and argv[0] == '-':
          nextArg = argv[1]
          print("Next arg" + nextArg)
        #endif
        if not remove:
          args.append(argv)
        #endif  
      #endfor
      sys.argv = args  #command line args to forward to moderngl
    #endif
    if com_port != None:
      import balance
      alt_controller = balance.balance(com_port,num_sensors,force_scale, print_com,print_force)
    #endif  
    GutterRun.run()
