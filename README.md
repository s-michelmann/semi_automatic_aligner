# semi_automatic_aligner
This is a little GUI that facilitates text-to-speech alignment. The idea is to manually select segments from the audio and align them with parts of the transcript. This helps when long silences or noise are messing up the forced alignment. You can also correct the transcript while you are aligning.
This version is for **MacOS**, tested under MacOS Big Sur (to use with windows you need workarounds for the penn aligner, e.g. using cygwin and python 2). You can also integrate different aligners by changing the aligner function (this is not ready). Also: this is my own private (and messy) tool, so use with caution.


Installation

install anaconda or miniconda
install XCode

## getting the aligner to work
(here: using penn phonetics forced aligner. I have been using https://github.com/jaekookang/p2fa_py3
### Install the htk toolkit
from http://htk.eng.cam.ac.uk/

Download the unix/linux version and put it in your Documents folder
Open a terminal and type

$	tar -xvf HTK-3.4.1.tar.gz

$	cd htk

Then type
  $	export CPPFLAGS=-UPHNALG
  $ ./configure --disable-hlmtools --disable-hslab
  $	make clean    
  $	sudo make -j4 install

When compiling (make -j4 all) watch out for fatal error: 'malloc.h' file not found  in this case you want to do the following fix:

$ export CPPFLAGS=-I/opt/X11/include

Add CPPFLAGS
$ export CPPFLAGS=-I/opt/X11/include

If the above doesn't work, do
$ ln -s /opt/X11/include/X11 /usr/local/include/X11

 Replace line 21 (#include <malloc.h>) of HTKLib/strarr.c as below
  include <malloc/malloc.h>

 Replace line 1650 (labid != splabid) of HTKLib/HRec.c as below
   labpr != splabid
 This step will prevent "ERROR [+8522] LatFromPaths: Align have dur<=0"
 See: https://speechtechie.wordpress.com/2009/06/12/using-htk-3-4-1-on-mac-os-10-5/

 Compile with options if necessary
$ ./configure
$ make all

Now continue with
$ sudo make -j4 install

Now check that conda is available
$ conda —-version

And update if necessary
$ conda update conda

Make a new conda environment named alignment that uses python3
$ conda create -n alignment python=3

activate the environment
$ conda activate alignment

Install sox using conda
$ conda install -c conda-forge sox

clone p2fa for python3
$ git clone https://github.com/jaekookang/p2fa_py3.git

Now cd into p2fa_py3/p2fa and call
$ python align.py examples/ploppy.wav examples/ploppy.txt examples/everythingWorks.TextGrid

If everything works well you should now see a file named everythingWorks.TextGrid in the examples folder. The file contains the aligned sentence: I am trying to say ploppy

Now you can cd back into the parent directory of p2fa_py3
$ cd ../..

Now clone this repository
$ git clone https://github.com/s-michelmann/semi_automatic_aligner

Install all the requirements
conda install --file requirements.txt

then cd into the folder
$ cd semi_automatic_aligner
type
$ python semi_align.py

this should open the GUI. You need to open a wav file and a txt file and the whole gui will load (see wiki for manual)
