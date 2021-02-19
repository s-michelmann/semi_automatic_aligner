# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 19:59:40 2020

@author: Sebastian Michelmann
"""
import os
import sys
import inspect
import wave
import warnings
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from textgrid_remote.textgrid import textgrid
from p2fa_py3.p2fa import align
# from subprocess import Popen, PIPE


class SegmentAligner:

    def __init__(self, audiofile, textfile, temp_path):
        if not os.path.exists(temp_path):
            os.mkdir(temp_path) 
        
        self.audio = wave.open(audiofile, mode='rb')
        texthandle = open(textfile, 'r')
        text = texthandle.read()
        all_words = text.split()
        self.all_aligned_words = []
        tmpid = 0
        # initialize all aligned words with None 
        for ww in all_words:
            idstring = "w" + str(tmpid)
            self.all_aligned_words.append((idstring, ww.lower(), None, None))
            tmpid += 1
        self.audio_sel = (0, -1)
        self.aligerfunction = self.align_penn
        self.selected_words = []
        self.temp_path = temp_path
        self.aligned_words = []
         
    def align_all(self):
        self.align_segment((0, -1), (0, None))
        
        
    def align_segment(self, audio_sel, word_sel):
        self.audio_sel = audio_sel
        self.selected_words = self.all_aligned_words[word_sel[0]:word_sel[1]]
        self.write_audio_selection()
        self.write_text_selection() 
        
        #-- This section is where all the updates in the class need to be done
        # other functions shouldn't make any changes !!
        words = self.aligerfunction()
        self.aligned_words = words
        # append the id and errorcheck
        # ids will be important to interactively insert words!
        # inserting words will need to add the word to all_aligned_words and create a 
        # new entry with ID none and positions none none. then a pass needs to 
        # overwrite all the IDs in order 
        words_id = []
        i = 0
        for ww in self.all_aligned_words[word_sel[0]:word_sel[1]]:
            if not ww[1] == words[i][0]:
                warnings.warn('word ' + ww[1] 
                              + ' has not been aligned... skipping', None)
                words_id.append((ww[0], ww[1], None, None))
            else:
                words_id.append((ww[0], words[i][0], words[i][1], words[i][2]))
                i += 1
        self.all_aligned_words[word_sel[0]:word_sel[1]] = words_id
        return words_id
    
    def write_text_selection(self):       
        print('writing text')
        with open(self.temp_path + os.path.sep + 'tmp.txt', 'w') as f:
            for item in self.selected_words:
                f.write("%s\n" % item[1].lower())
            f.close()
  
    def write_audio_selection(self):
        print('writing audio')
        tmp_audio = wave.open(self.temp_path + os.path.sep + 'tmp.wav', mode = 'wb')
        tmp_audio.setparams(self.audio.getparams())
        sr =  tmp_audio.getframerate()
        n_frames2write = int(
            (self.audio_sel[1] - self.audio_sel[0]) *sr)
       # tmp_audio.setnframes(n_frames2write)
        posnow = int(self.audio.tell())
        self.audio.setpos(int(self.audio_sel[0]*sr))
        data = self.audio.readframes(n_frames2write)
        tmp_audio.writeframes(data)
        self.audio.setpos(posnow)
        tmp_audio.close()
    
    # aligner function using penn aligner (overwrit for system specific setup)
    def align_penn(self):
       def parse_grid(grid):
           tiers = grid.getList('word')
           s_word_strings = []
           for ww in self.selected_words:
               s_word_strings.append(ww[1].lower())
           words = []
           for tier in tiers:
               for i in tier.intervals:
                   if i.mark.lower() in s_word_strings:
                       words.append((i.mark.lower(), i.minTime +self.audio_sel[0]
                                     , i.maxTime+self.audio_sel[0]))
           print('done')
           return words
       print('aligning...')

       # # open cygwin // this is for windows 8.1. without
       # handle = Popen('C://cygwin//bin//bash.exe', stdin=PIPE, stderr=PIPE, stdout=PIPE, text = True, shell=True)
       # handle.communicate(input = 'python2 align.py ' + self.temp_path +
       #                    '/tmp.wav' + ' ' + self.temp_path +
       #                    '/tmp.txt'+ ' ' + self.temp_path  + '/tmp.TextGrid')
       # handle.wait()


       align.align(self.temp_path + '/tmp.wav', self.temp_path + '/tmp.txt', self.temp_path + '/tmp.TextGrid')

       grid = textgrid.TextGrid()
       grid.read(self.temp_path + '//tmp.Textgrid')
       # removing the textgrid otherwise aligner will not crash when error
       if os.path.exists(self.temp_path + '//tmp.Textgrid'):

           os.remove(self.temp_path + '//tmp.Textgrid')
       else:
           print("alignment must've failed") 
       return parse_grid(grid)
   
    # # aligner function using aeneas (overwrit for system specific setup)
    # def align_aeneas(self):
    #     from aeneas.executetask import ExecuteTask
    #     from aeneas.task import Task
    #     # this code will be specific to the aligner that is being used.
    #     # the aligner aligns tmp/tmp.wav to tmp/tmp.txt
    #     def parse_leaves(leaves):
    #         print('parsing')
    #         words = []
    #         for l in leaves:
    #             if (l.text):
    #                 words.append(
    #                     (l.text, float(l.begin.copy_abs() + self.audio_sel[0]),
    #                               float(l.end.copy_abs() + self.audio_sel[0])))
    #         print('done')
    #         return words
    #     # create Task object
    #     cfg = u"task_language=eng|is_text_type=plain|os_task_file_format=json"
    #     task = Task(config_string=cfg)
    #     task.audio_file_path_absolute = u'' + self.temp_path + os.path.sep + 'tmp.wav'
    #     task.text_file_path_absolute = u'' + self.temp_path + os.path.sep + 'tmp.txt'
    #     task.sync_map_file_path_absolute = u'' + self.temp_path + os.path.sep + 'tmp.json'
    #     print('aligning...')
    #     # process Task
    #     ExecuteTask(task).execute()
    #     # output sync map to file
    #     #task.output_sync_map_file()
    #
    #     leaves = task.sync_map_leaves()
    #     return parse_leaves(leaves)
