# ModernGL Gully Run
![Gully Run screenshot](/screenshot1.png)

## About
Gully is my first attempt to use moderngl.py to create a 3D game with procedurally generated scenery.

The idea is to guide a skateboarder down a convoluted gully in the shortest possible time.

The game can be operated either using a mouse (move up to go faster, move down to go slower) or through a stand-on balance board (more on that later). For mouse operation, the space bar is used to start the game and to pause it.

The physics used is fairly simple and no collision geometry is used, but you will get a faster time if you hug the corners.

If you come off the track, there is an Easter egg as consolation.

Each time the python script is run, a new track is generated procedurally.

## Installation

Locate everything anywhere you like. Assuming you have python3 installed, then for the first time, run from a terminal and you'll see what dependancy packages are missing.

### Dependancies

- python3
- moderngl
- moderngl_window
- pathlib           #to locate the resources directory
- numpy             #to create vertix and indici objects
- pyrr              #for matrix translations
- pygame            #for onscreen gui
- json              #only used for diagnostic output

If you use the optional balance controller, you'll also need:
 for linux "sudo apt-get install python3-serial"
 or for windows "py -3 -m pip install pyserial"

All standard libraries as of May 2022

## Running
You can use these shell/batch files:
./gullyrun_mouse.sh (Linux - after making it executable) or 
gullyrun_mouse.bat (Windows)

The basic command line is ""python3 gullyrun.py"" (Linux) or ""py -3 gullyrun.py"" (Windows).
Using the balance option, you will need to set the serial port in the shell or batch file which depends on your platform.

## Command line arguments:
-b background_img (default is none)
-t track_length (default is 1000)

The following arguments only apply to the balance controller option.
-p com_port = the USB port name connected to the arduino (or similar) controller  (default is none, which means the game is controlled by the mouse)
-a = print the force values received from the controller
-d = print the raw serial port data from the controller
-m x,y = force scale (we found that the front back motion needed to be more sensitive than the left right motion)
-l num_sensors   (between 2 and 4 sensors could be used. For simplicity, we used 4 load cells)

## Optional - Balance Board Controller

To control the game without using your hands, a square board with 4 low profile load cells at each corner. There were connected to the analog inputs of an Arduino microcontroller. This controller printed out 5 values (see file ai4.ino), the first 4 being the measurements from the load cells that were placed at each corner of the board. The system calibrates as zero when first turned on with no one standing on the board.
Play is begun when a minimum weight is detected on the board and then by leaning in different directions. In effect, it acts as a hands-free joystick.

The file ai4.ino is the code for an arduino (I used an Uno).
We used [Loadstar iload sensors](https://www.loadstarsensors.com/iload.html)


 

