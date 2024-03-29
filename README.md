# semi_automatic_aligner
This is a little GUI that facilitates text-to-speech alignment. The idea is to manually select segments from the audio and align them with parts of the transcript. This helps when long silences or noise are messing up the forced alignment. You can also correct the transcript while you are aligning.
This version is for **MacOS**, tested under MacOS Big Sur (to use with windows you need workarounds for the penn aligner, e.g. using cygwin and python 2). It uses penn phonetics forced aligner. You can also integrate different aligners by changing the aligner function (this is not ready, you have to finish coding this yourself). Also: this is my own private (and messy) tool, so use with caution. It only gives you word onset and offset times, **not** phoneme level alignment.

<img width="1002" alt="screen_shot" src="https://user-images.githubusercontent.com/42154998/228976643-e3033751-008c-4208-ab8c-4e89b5373c1e.png">

## Installation  

#### Prerequisites  
- [x] install anaconda or miniconda  
- [x] install XCode  
      `xcode-select --install`

### Getting the aligner to work  
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

  change into your designated folder (e.g. Documents/alignment)  

  clone p2fa for python3  
  `git clone https://github.com/jaekookang/p2fa_py3.git`  

  Now  
  `cd p2fa_py3/p2fa`  
  and type  
  `python align.py examples/ploppy.wav examples/ploppy.txt examples/everythingWorks.TextGrid`   

  If everything works you should now see a file named *everythingWorks.TextGrid* in the examples folder. The file contains the aligned sentence: I am trying to say ploppy  

### Getting this GUI to work  
Now you can cd back into your desgnated directory that should have a folder named p2fa_py3 and a folder named htk in it.  

- [x] Now clone this repository including the submodule for textgrid!  
  `git clone --recurse-submodules -j8 https://github.com/s-michelmann/semi_automatic_aligner`  


- [x] Install all the requirements  
  change into the folder `cd semi_automatic_aligner`  
  type  
  `conda install --file requirements.txt`  

- [x] type `python semi_align.py`  

  this should open the GUI. Once You have opened a .wav File - open wav and a .txt file the GUI will load the whole interface (see also wiki for manual). Note that .wav files may have issues with the aligner if they are not one channel sampled at 16K.

## Use  
You need to
- `conda activate alignment` 
- run the GUI (type `python semi_align.py`)
- open a .wav file and a .txt file that contains the transcription of the audio. You should then see the audio and the text displayed.
- Left-click onto the audio-trace to make the left selection (hit the green play button to play).
- (Pause and) right-click onto the audio-trace to make a right selection and thereby select a segment (a blue patch will mark the segment)
- Click the blue play button to play the segment (note that the segment stops automatically with inaccuracies in the range of the refresh rate)
- When playing, the axes will update automatically. To skip through the audio use the left and right button. The double right lets you skip fast.
- The listbox on the right contains all the words from the transcript. Select the words by clicking and holding, or click, press shift then click somewhere else
- Click align to align the listbox selection to the audio segment
- To update the listbox with the words, edit the transcript in the textbox below the audio. Click update to update the listbox
- If you want to find an item from the listbox in the transcript (textbox), select the item and click update. This will highlight the text in green up to the current position.
- Save and load your progress to a .csv.

## Notes
- Too much text can get laggy. Consider splitting your transcript in parts and align them separately. Then concatenate your .csv files.
