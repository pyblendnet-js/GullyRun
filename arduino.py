#arduino interface based on ledusa by Robert Parker 2019
import platform, time
import serial
# for linux "sudo apt-get install python3-serial"
# for windows "py -3 -m pip install pyserial"
# you may need to download from "https://github.com/pyserial/pyserial" first
# docs at https://pythonhosted.org/pyserial/
BAUD = 9600  #for version V11 for arduino stepcontroller
NUMSPOKES = 1
GPIO_ARDU_RESET_PIN = 7
gpioActive = False  #for raspberry pi to reset first spoke
portRange = 20  #windows adds a new COM port allocation with each new device
verbose = 0
arduHostComms = False  #might be true for DUE
currentSerial = None

def clearCom(ser): # flushes input buffer
  while ser.in_waiting > 0:
    try:
      c = str(ser.readline(), 'utf-8')
    except:
      pass
    if verbose & 1:
      print("Flush:" + c)
  #time.sleep(0.5)

def openArdu(com_nm):  #if you know where your arduino so, come straight here
  global currentSerial
  if(verbose & 1):
    print("Try " + com_nm)
  #endif
  try:
    if platform.system() == "Windows":
      ser = serial.Serial(com_nm, BAUD,timeout=2 )  #,xonxoff=0,rtscts=0) - windows10 didn't like me tampering with flow control etc.
      ser.readline()  #for some reason Windows10 needs this once to get things moving
    else:
      ser = serial.Serial(com_nm, BAUD,timeout=2,xonxoff=0,rtscts=0)
    #endif
  except:
    print("Failed to open arduino")
    return None
  #endtry
  if(verbose & 1):
    print("Open " + str(com_nm) + " @ " + str(BAUD) + "bps")
  #endif
  if not arduHostComms:
    #print("Wait a second")
    time.sleep(0.5) # can take second to reset for regular arduino
  #endif
  clearCom(ser)
  currentSerial = ser
  return ser  #returns the open serial port
#enddef

def closeArdu():
  if currentSerial != None:
    currentSerial.close()
  #endif
#enddef

def send(msg, ser = None):
  if ser == None:
    ser = currentSerial
  #endif
  if ser == None:
    return
  #endif
  ser.write(msg.encode())
#enddef
  

def getReplies(ser = None, si = 0):
  if ser == None:
    ser = currentSerial
  if ser == None:
    return None
  replies = []
  try:
    while ser.in_waiting > 0:
      try:
        c = str(ser.readline(), 'utf-8').strip()
      except UnicodeDecodeError as e:
        c = "Not string"
      rply = str(c)
      if (verbose & 0x40) != 0:
        print(str(si) + '<' + rply)
      #endif
      replies.append(rply)
    #endwhile
  except:
    print("Error reading serial #" + si.toString())
  #endtry
  return replies
#enddef


