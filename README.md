# semi_automatic_aligner
This is a GUI that facilitates text-to-speech alignment. The idea is to manually select segments from the audio and align them with parts of the transcript. This helps when long silences or noise are messing up the forced alignment. You can also correct the transcript while you are aligning.
This version is for **MacOS**, tested under MacOS Big Sur (to use with windows you need workarounds for the penn aligner, e.g. using cygwin and python 2). You can also integrate different aligners by changing the aligner function (this is not ready). Also: this is my own private (and messy) tool, so use with caution.


## Installation  

#### Prerequisites  
- [x] install anaconda or miniconda  
- [x] install XCode  
      `xcode-select --install`

### Getting an aligner to work  
(here: using penn phonetics forced aligner)  
I have been using https://github.com/jaekookang/p2fa_py3 that works with python3. The htk installation is from the instructions by jaekookang. (the GUI-code can/could be adapted to work with other aligners and system specific setups)  

- [x] Install the htk toolkit
      (download from http://htk.eng.cam.ac.uk/)
1. Download the unix/linux version and put it in your designated folder (e.g. Documents/alignment)  
2. In the terminal type `tar -xvf HTK-3.4.1.tar.gz` to unzip the folder.
3. Change directory to the htk folder `cd htk`  
and
4. type  `export CPPFLAGS=-UPHNALG`
5. type `./configure --disable-hlmtools --disable-hslab`
6. make sure you get a clean build (in case you have been compiling other stuff), type `make clean`
7. compile 	`make -j4 all`

Note: When compiling (make -j4 all) watch out for fatal error: 'malloc.h' file not found  in this case you want to do the following fix:
  - `export CPPFLAGS=-I/opt/X11/include`
  - `export CPPFLAGS=-I/opt/X11/include`

If the above doesn't work, do
  - `ln -s /opt/X11/include/X11 /usr/local/include/X11`

  - Then open the file *HTKLib/strarr.c* and in line 21


  | replace 	| with 	|
  |-	|-	|
  | include <malloc.h 	| include <malloc/malloc.h 	|

  - Then open *HTKLib/HRec.c* go to line 1650 and

  | replace 	| with 	|
  |-	|-	|
  | (labid != splabid) 	| labpr != splabid 	|


This step will prevent "ERROR [+8522] LatFromPaths: Align have dur<=0"
 See: https://speechtechie.wordpress.com/2009/06/12/using-htk-3-4-1-on-mac-os-10-5/

Now back to step 7:

7. `./configure`  
  `make -j4 all`

Now finally continue with the install

8. `sudo make -j4 install`

- [x] Install sox
  check that conda is available
  `conda —-version`

  And update if necessary
  `conda update conda`

Make a new conda environment named alignment that uses python3
 `conda create -n alignment python=3`

activate the environment
`conda activate alignment`

Install sox using conda
`conda install -c conda-forge sox`

- [x] get jaekookang's p2fa for python3

change into your designated folder (e.g. Documents/alignment)/
clone p2fa for python3
`git clone https://github.com/jaekookang/p2fa_py3.git`

Now
`cd p2fa_py3/p2fa`
and type
`python align.py examples/ploppy.wav examples/ploppy.txt examples/everythingWorks.TextGrid`

If everything works well you should now see a file named *everythingWorks.TextGrid* in the examples folder. The file contains the aligned sentence: I am trying to say ploppy

### Getting this GUI to work  
Now you can cd back into your desgnated directory that should have a folder named p2fa_py3 and a folder named htk in it.

- [x] Now clone this repository including the submodule for textgrid!
  `git clone -recurse-submodules -j8 https://github.com/s-michelmann/semi_automatic_aligner`
change into the folder `cd semi_automatic_aligner`
- [x] Install all the requirements
  `conda install --file requirements.txt`
type
- [x] type `python semi_align.py`

this should open the GUI. Once You have opened a .wav File - open wav and a .txt file the GUI will load the whole interface (see wiki for manual). Note that .wav files may have issues with the aligner if they are not one channel sampled at 16K.
