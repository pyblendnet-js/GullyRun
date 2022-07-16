#FOOT CONTROLLED BALANCE BOARD

import arduino #for foot control via load cells      

class balance():
  zero = None
  ardu = None
  num_sensors = 4
  com_port = "COM3"
  print_com = False
  print_force = False
  minimum_weight = 1600
  weight = -20
  totalWeightSamples = 0
  totalWeightTime = 0
  total_force = 0
  force = [0,0]
  weight_conversion = 0.175
  force_scale = (4,6)
  active = False
  
  def __init__(self,com_port, num_sensors=4, force_scale=(4,6), print_com=False, print_force=False):
    arduino.BAUD = 57600
    self.ardu = arduino.openArdu(com_port)
    self.print_com = print_com
    self.print_force = print_force
    self.num_sensors = num_sensors
    self.force_scale = force_scale
    if self.ardu == None:
      print("Failed to open arduino on com port:",com_port)
    else:
      print("Arduino interface opened on com port:",com_port)
      arduino.clearCom(arduino.currentSerial)
    #endif  
  #enddef
  
  def close(self):
    arduino.closeArdu()
  #endif  

  def getForce(self,dt):
    #rint("Get force:",self.ardu)
    if self.ardu == None:
      return None
    #endif
    #rint("F:",self.force)
    self.totalWeightTime += dt  #gets reset if no weight
    replies = arduino.getReplies()
    if len(replies) > 0:
      vals = replies[-1].split(",")
      if len(vals) > 5:
        return self.force  #invalid frame
      vi  = 0 
      v = [-1]*5
      vsum = 0
      for vs in vals:
        v[vi] = int(vs)
        vsum += v[vi]
        vi += 1
      #endfor  
      #rint(vi,sum,self.num_sensors)
      if vi >= self.num_sensors:  #got three values
        if self.print_com:
          print("Com in:",v)
        #endif 
        rl = 0
        fb = 0
        #rint(self.zero) 
        print(vsum)
        if (self.zero == None) or (vsum < self.minimum_weight):
          self.zero = tuple(v)
          self.weight = -20
          self.totalWeightSamples = 0
          self.totalWeight = 0
          self.totalWeightTime = 0
          self.instanceWeight = -20
          self.force = [0,0]
          self.active = False
        else: 
          self.active = True
          # sum/8 = kg
          self.weight = 0
          for i in range(num_sensors):
            v[i] -= self.zero[i]
            self.weight += v[i]
          #endfor  
          self.weight *= self.weight_conversion  #instananeous weight
          self.totalWeightTime += dt
          if self.totalWeightTime > 2.0: #need time for balance to settle
            self.totalWeight += self.weight
            self.totalWeightSamples += 1
            self.weight = self.totalWeight/self.totalWeightSamples
          #endif
          if True:
            #rint((v[0]-v[1])/(v[0] + v[1]))
              #rint("Got here")
              #try:
              if True:
                if self.num_sensors == 2:
                    rl = v[0]
                    fb = v[1]
                elif self.num_sensors == 3:
                    if (v[0] + v[1]) == 0:  #invalid frame
                      return self.force 
                    rl = (v[0]-v[1])/(v[0] + v[1])
                    bv = (v[0] + v[1])/2
                    fb = (bv-v[2]*2)/(v[2]*2 + bv)
                else: #assume 4 sensors
                    rl = (v[0] + v[1] - v[2] - v[3])/-vsum
                    fb = (v[0] + v[2] - v[1] - v[3])/-vsum
                #endif   
                #limit range to match mouse on a HD screen
                rl = min(0.5,max(-0.5,rl*self.force_scale[0]))
                fb = min(0.3,max(-0.3,fb*self.force_scale[1]))
                #rint("%d %2.3f %2.3f"%(int(vsum/8),rl,fb))
                rt = 1.0 - dt*10
                self.force[0] = self.force[0]*rt + rl*dt*10
                self.force[1] = self.force[1]*rt + fb*dt*10
                if self.print_force:
                  print("Balance Force:",rl,fb)
                #endif
              #except:
              #  pass
              #endtry                        
           #endif
        #endif  
      #endif
    #endif  
    return self.force
  #enddef
  
  def isActive(self):
    #rint("Weight:",self.weight)
    return self.active
  #enddef  
#endclass          

