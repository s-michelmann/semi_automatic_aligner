# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 21:26:31 2020

@author: Sebastian Michelmann
"""
#%% todo:-add zoom button, -add menu with save  aligner selection
# note:
# make color green for fixed text

    
    
# Make button read text from list and change label from update to update listbox
# IMPORTANT: rewrite play segment so that only chunks in segment are written
#        -add words and safe, -add labels and move axis with color change

#        -set text bgcolor highlight to word selection
#        -add a decode-text from audio option
# add lim_old == lim_new check to left and right step to avoid redrawing words

# clicking on the label should also highlight the segment 
# label replotting too slow...
#%% START FROM HERE
# updating the plot fucks it up! Try a timer instead that has the segment running while playing

# open the aligner with the corresponding files

open_with_files = False;

#import time

from segmentaligner import SegmentAligner
import pyaudio
#import struct
import numpy as np
import string
import csv

#%% TRY THE PLOTTING PART
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
#from matplotlib.transforms import Bbox
import threading
import random
import matplotlib
matplotlib.use('TkAgg')
#%% NOTE: audio needs to be async!
constructed = False
time_axis = None
fig = None
fig2 = None
canvas = None
canvas2 = None
step_width = None
stream = None
words_in_view = (0,-1)
ax1 = None
ax2 = None
selection_A = 0
last_list_sel = None
root = tk.Tk()
bg = None
#start_time = time.time()
root.geometry('1000x550+50+50')
root.title("SeMi-automatic aligner")



# #Icons made by <a href="https://www.flaticon.com/authors/skyclick" title="Skyclick">Skyclick</a> from <a href="https://www.flaticon.com/" title="Flaticon"> www.flaticon.com</a>
#root.iconbitmap(r'semi_files//img//brain.ico')
root.configure(background= 'white')

textname = None
audioname = None
savefilename = None
words_read = None
def openTfile():
    global textname
    textname =  tk.filedialog.askopenfilename(
        initialdir = os.getcwd() + '\\semi_files\\data',title = "Select file",filetypes = (
            ("txt files","*.txt"),("all files","*.*")))
    if audioname:
        fileMenuItems.entryconfig("Open .txt", state="disabled")
        fileMenuItems.entryconfig("Open .wav", state="disabled")
        fileMenuItems.entryconfig("Save", state="normal")
        fileMenuItems.entryconfig("Save As", state="normal")
        add_elements()
        refresh_root()
    
    return


def openWfile():
    global audioname
    audioname =  tk.filedialog.askopenfilename(
        initialdir = os.getcwd() + '\\semi_files\\data',title = "Select file",filetypes = (
            ("txt files","*.wav"),("all files","*.*")))
    if textname:
        fileMenuItems.entryconfig("Open .txt", state="disabled")
        fileMenuItems.entryconfig("Open .wav", state="disabled")
        fileMenuItems.entryconfig("Save", state="normal")
        fileMenuItems.entryconfig("Save As", state="normal")
        add_elements()
        refresh_root()
    return

def asksavefile():
    global savefilename
    files = [('Csv Files', '*.csv'), ] 
    savefilename = tk.filedialog.asksaveasfilename(initialdir = os.getcwd() + '\\semi_files\\data',
        title = "Select file", filetypes = files, defaultextension = files) 
    savefile()
   

def savefile():
    if not(savefilename):
        asksavefile()
    else:
        with open(savefilename, 'w', newline='') as csvfile:            
            cswrriter = csv.writer(csvfile)
            for ww in sa.all_aligned_words:
                if ww[3]:
                    cswrriter.writerow([ww[0], ww[1], "{:.5f}".format(
                            float(ww[2])), "{:.5f}".format(float(ww[3]))])
                else: 
                    cswrriter.writerow([ww[0], ww[1], "NaN", "NaN"])

def loadfile():
    global words_read
    words_read = []
    files = [('Csv Files', '*.csv'),]
    loadfilename = tk.filedialog.askopenfilename(initialdir = os.getcwd() + '\\semi_files\\data', title = "Select file", filetypes = files)
    
    with open(loadfilename, newline='') as csvfile:
        cwreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in cwreader:
            word = row[0].split(sep = ',')
            if word[3]== 'NaN':
                words_read.append((word[0], word[1], None, None))
            else:
                #print(word)
                words_read.append(
                    (word[0], word[1], float(word[2]), float(word[3])))
    if constructed:
        for ii in range(len(words_read)):
            if (words_read[ii][0] == sa.all_aligned_words[ii][0]) and (
                    words_read[ii][1] == sa.all_aligned_words[ii][1]):
                sa.all_aligned_words[ii] = words_read[ii]
            else:          
                tk.messagebox.showerror(
                    title=None, message='there is a mismatch between the words')
                return
        fill_listbox() 
        draw_words()          
def close():
    MsgBox  = tk.messagebox.askquestion(title = 'warning',
                                                message='exit?')
    if MsgBox == 'no':
        return      
    else: 
        root.destroy()
menuBar = tk.Menu(root)
fileMenuItems = tk.Menu(menuBar)
fileMenuItems.add_command(label="Open .txt", command=openTfile)
fileMenuItems.add_command(label="Open .wav", command=openWfile)
fileMenuItems.add_command(label="Save", command=savefile)
fileMenuItems.add_command(label="Save As", command=asksavefile)
fileMenuItems.add_command(label="Load", command=loadfile)
fileMenuItems.add_command(label="Close", command=close)

fileMenuItems.entryconfig("Save", state="disabled")
fileMenuItems.entryconfig("Save As", state="disabled")


menuBar.add_cascade(label="File", menu=fileMenuItems)
root.config(menu=menuBar)




def add_elements():
    global sa, playing, segment_playing, txt, my_thread, listbox, selection_A, ax1, ax2, bg
    global selection_B, left_select, right_select, max_wpm, x_scale, words_inwin
    global words_inwin, left_sel, audiopos, zoom_in, constructed
    global time_axis, fig, fig2, canvas, canvas2, step_width, stream
    
    constructed = True
    
    #audioname = 'semi_files//data//grav1.wav'
    #textname = 'semi_files//data//grav1.txt'
    tmpfolder = 'semi_files//data//tempalign'
    sa = SegmentAligner(audioname, textname, tmpfolder)
    #%% read all the data
    n_frames = sa.audio.getnframes()
    sr = sa.audio.getframerate()
    time_axis = np.arange(0, n_frames/sr, 1/sr);
    
    sa.audio.setpos(sa.audio_sel[0])
    #struct.unpack(str(2*n_frames) + 'B', sa.audio.readframes(n_frames))
    data_all = np.frombuffer(sa.audio.readframes(n_frames),dtype=np.int16)
    sa.audio.setpos(sa.audio_sel[0])
    
    
    playing = False
    segment_playing = False
    txt = None
    my_thread = None
    listbox = None
    selection_A = 0
    selection_B = time_axis[-1]
    left_select = False
    right_select = False
    max_wpm = 400 # 200 is realistic
    x_scale = 20
    words_inwin = round(x_scale*(max_wpm/60))
    step_width = 5
    left_sel = 0
    audiopos = 0
    zoom_in = 1
    
    
    
    #% --- create the figure for the audioplot
    fig = Figure(figsize = (8.5,1.5), dpi=100,frameon=False) #means 1 inch = 100 pixels
       
    gs = fig.add_gridspec(5, 1)
    fig.add_subplot(gs[0:3, 0])
    
    
    ax1 = fig.gca()
    ax1.plot(time_axis[0:-1:200], data_all[0:-1:200],'-', color = 'dimgray', lw = 0.5)
    ax1.get_yaxis().set_ticks([])
    ax1.set_xlim([0,x_scale]) # this works in audio, if pos> half of time a
    
   # ax1.text(1, 0,"test",  fontsize = 6, bbox=dict(pad = 0, facecolor='red', lw = 0 ), animated=False)
  

   # fig.set_tight_layout(True)
   # fig.tight_layout()
    
    fig.tight_layout(pad=0.01, w_pad=0.01, h_pad=0.01)
    fig.add_subplot(212).plot(time_axis, np.empty((len(time_axis),1))
                               , color = 'dimgray', lw = 0.2)
   
    ax2 = fig.gca()
    ax2.get_yaxis().set_ticks([])
    ax2.get_xaxis().set_ticks([])
    ax2.set_ylim([0,1]) 
    ax2.set_xlim([0,x_scale]) 
    canvas = FigureCanvasTkAgg(fig, master = root)
    
    canvas.draw()
   # canvas.flush_events()
    # lines = ax1.get_lines()
    # for line in lines:
    #     line.set_animated(True)
    #     fig.draw_artist(line)
    
     
    canvas.get_tk_widget().place(x = 0, y = 30, width=850, height=220)
        
    #% --- create the figure for the labelplot
   
       
   
    # fig2 = Figure(figsize = (8.5,0.5), dpi=100,frameon=False) #means 1 inch = 100 pixels
    # fig2.add_subplot(111).plot(time_axis, np.empty((len(time_axis),1))
    #                            , color = 'dimgray', lw = 0.2)
    # fig2.gca().get_yaxis().set_ticks([])
    # fig2.gca().get_xaxis().set_ticks([])
    # fig2.tight_layout(pad=0.1)
    # fig2.gca().set_ylim([0,1]) 
    # fig2.gca().set_xlim([0,x_scale]) # this works in audio, if pos> half of time a
    
    
    # canvas2 = FigureCanvasTkAgg(fig2, master = root)
    # canvas2.draw()
    # canvas2.get_tk_widget().place(x = 0, y = 180, width=850, height=150)
    
    # define the audio stream which also updates the xposition
   #frame_count = 1024
    
    
    p = pyaudio.PyAudio()
    
    stream = p.open(format = p.get_format_from_width(sa.audio.getsampwidth()),
                    channels = sa.audio.getnchannels(),
                    rate = sa.audio.getframerate(),
                    output = True, stream_callback = callback, start = False)


    
    canvas.mpl_connect('button_press_event', onclick)
    
    align_button = tk.Button(root, text = "align", command = align)
    align_button.place(x = 850, y = 505, width=150, height=25)
    
    
    
    txt_update_button = tk.Button(root, text = 'update', command = txt_update)
    txt_update_button.place(x = 0, y = 505, width=50, height=25)
    
   
    
    txt = tk.Text(root, wrap = tk.WORD, bg = 'grey12', fg = 'gold', 
                  inactiveselectbackground="red", selectbackground = 'red', 
                  insertbackground = 'red')
    
    # replace this with a canvas!
    scroll = tk.Scrollbar(txt)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    # Configure the scrollbars
   # scroll.config(command=txt.yview)
   
    txt['yscrollcommand'] = scroll.set
    
    txt.place(x = 0, y = 270, width=850, height=240)
    
    add_text()
    
    
    
    
    #text['yscrollcommand'] = scrollbar1.set
    
    #word_axis = np.arange(1/sr, len(time_axis)-1/sr, len(sa.all_aligned_words))
    
    
    
        
    #txt.tag_config(word[0], background="yellow", foreground="red")
    #for word in sa.all_aligned_words: 
    #print(txt.index('testtag'))
        #print(txt.get("1.0","end" ))
        #print(txt.get("%d.%d" % (1, 3),"%d.%d" % (1, 8)))
    
    # Creating a Listbox and 
    # attaching it to root window 
    listbox = tk.Listbox(root, selectmode = "extended") 
      
    # Adding Listbox 
    listbox.place(x = 850, y = 30, width=150, height=480)
      
    # Creating a Scrollbar and  
    # attaching it to listbox
    scrollbar = tk.Scrollbar(listbox) 
      
    # Adding Scrollbar to the right 
    # side of root window 
    scrollbar.pack(side = tk.RIGHT, fill = tk.BOTH) 
    
       
    fill_listbox()
     
          
    # Attaching Listbox to Scrollbar 
    # Since we need to have a vertical  
    # scroll we use yscrollcommand 
    listbox.config(yscrollcommand = scrollbar.set) 
      
    # setting scrollbar command parameter  
    # to listbox.yview method its yview because 
    # we need to have a vertical view 
    scrollbar.config(command = listbox.yview) 
    
    if words_read:
        for ii in range(len(words_read)):
                if (words_read[ii][0] == sa.all_aligned_words[ii][0]) and (
                        words_read[ii][1] == sa.all_aligned_words[ii][1]):
                    sa.all_aligned_words[ii] = words_read[ii]
        fill_listbox() 
        draw_words()          
    
    bg = canvas.copy_from_bbox(ax1.bbox)



def add_text():
    global listbox
   
    ls = None
 
    
    txt.delete('1.0', 'end')
    ii = 0
    for word in sa.all_aligned_words: 
          
        txt.insert('end', word[1], word[0])
        txt.insert('end', ' ')
        
        if last_list_sel:
            ls = max(last_list_sel)
            if ls >= ii:
                txt.tag_config(word[0], background="SeaGreen3")
            else:
                txt.tag_config(word[0], background='grey12')
        
        
        # if listbox and list_sel[1] > ii:
        #     txt.tag_config(word[0], background="red")
        ii += 1
    if ls:
        listbox.selection_set( min(listbox.size()-1, ls))
        listbox.see(ls)
    
def align():
    if not constructed:
        return
    global listbox, selection_A, selection_B
    list_sel = listbox.curselection()
    if not list_sel:
        tk.messagebox.showerror(title=None, message='no words selected')
        return
    if selection_A == 0 and selection_B == time_axis[-1]:
        MsgBox  = tk.messagebox.askquestion(title = None,
                                            message='select all audio?')
        if MsgBox == 'no':
            return
    elif not(left_select) and not(right_select):
        MsgBox  = tk.messagebox.askquestion(title = 'selection missing',
                                            message='select all audio?')
        if MsgBox == 'no':
            return
    elif not(left_select):
        MsgBox  = tk.messagebox.askquestion(title = 'selection missing',
                                            message='select from beginning?')
        if MsgBox == 'no':
            return
    elif not(right_select):
        MsgBox  = tk.messagebox.askquestion(title = 'selection missing',
                                            message='select until end?')
        if MsgBox == 'no':
            return
    audio_sel = (selection_A, selection_B)
    word_sel = (int(list_sel[0]),int(list_sel[-1]+1))
   
    sa.align_segment(audio_sel, word_sel)
   
    fill_listbox()
    draw_words()
    listbox.selection_set( min(listbox.size()-1, list_sel[-1]+1))
    listbox.see(list_sel[-1])
    #min(listbox.size()-1, list_sel[-1]+1)

def callback(in_data, frame_count, time_info, status):
    #global audiopos
    #audiopos +=1024
    data = sa.audio.readframes(frame_count)
    return (data, pyaudio.paContinue)   

def doubleright_step():
    if not constructed:
        return
    if playing or segment_playing:
        return
    global  sa #,words_in_view

    xl = ax1.get_xlim()
    if (xl[1]+10*step_width)<time_axis[-1]:
        ax1.set_xlim((xl[0]+10*step_width, xl[1]+10*step_width))
        ax2.set_xlim((xl[0]+10*step_width, xl[1]+10*step_width))
    else:
        ax1.set_xlim((time_axis[-1]-x_scale), time_axis[-1])
        ax2.set_xlim((time_axis[-1]-x_scale, time_axis[-1]))
    
    # new
    line = ax1.get_lines()
    
    while len(line)>1:
        line[1].remove()
        line = ax1.get_lines()
    
    patches = ax1.patches
    if len(patches)>0:
          patches.remove(patches[0])
    draw_words()

# radical change: only draw if words_in_view, then update in refresh (add draw_words)
def draw_words():
    global ax1, ax2 #,words_in_view
    sign = +1
    if ax2.texts:
       while len(ax2.texts)>0:
           del(ax2.texts[-1])
    
    at = sa.audio.tell()
    lim = ax1.get_xlim()    
    # words_in_view = []
    #i = 0
    for word in sa.all_aligned_words:
        jit = sign*(random.random())/2
        if word[2] and (lim[0]-1< word[2] and lim[1]+1> word[2]):
            
            if time_axis[at] < word[2]:
                ax2.text(word[2],0.45+jit,word[1], fontsize = 8,
                                bbox=dict(pad = 0, facecolor='red', lw = 0
                                         ))
            else:
                ax2.text(word[2],0.45+jit,word[1], fontsize = 8,
                                bbox=dict(pad = 0, facecolor='green', lw = 0
                                          )) # , alpha=0.5)  
            sign *= -1
            # if lim[0]-1< word[2] and lim[1]+1> word[2]:
            #     words_in_view.append(i)
            #i +=1
          
    canvas.draw() 
    
    #canvas.flush_events()      
def fill_listbox():
    global listbox
    if listbox:
        listbox.delete(0,'end')
    # Insert elements into the listbox 
    for word in sa.all_aligned_words: 
        if word[3]:
            tp = (word[0], word[1], "{:.3f}".format(
                float(word[2])), "{:.3f}".format(float(word[3])))
            listbox.insert(tk.END, tp)
        else: 
            listbox.insert(tk.END, word)
    #listbox.pack()
  
# -- define the onclick function for the figure canvas:
def left_step():
    if not constructed:
        return
    if playing or segment_playing:
        return
    global sa, ax1, ax2 #words_in_view
    
    xl = ax1.get_xlim()
    if (xl[0]-step_width)>=0:
        ax1.set_xlim((xl[0]-step_width, xl[1]-step_width))
        ax2.set_xlim((xl[0]-step_width, xl[1]-step_width))
    else:
        ax1.set_xlim((0, x_scale))
        ax2.set_xlim((0, x_scale))
    
    # new
    line = ax1.get_lines()
    
    while len(line)>1:
        line[1].remove()
        line = ax1.get_lines()
    
    patches = ax1.patches
    if len(patches)>0:
          patches.remove(patches[0])
    
    
    draw_words() # will also draw the canvas
    # i = 0
    # words_in_view = []
    # for word in sa.all_aligned_words:
    #     if word[2]:                    
    #         if xl[0]-1< word[2] and xl[1]+1> word[2]:
    #             words_in_view.append(i)
    #         i +=1
    # canvas.draw()
  #  canvas2.draw()  
def onclick(event):
    global ax1, ax2, bg
    if not constructed:
        return
    # print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
    #       ('double' if event.dblclick else 'single', event.button,
    #        event.x, event.y, event.xdata, event.ydata))
    global right_select, selection_B
    # LEFT CLICK EVENT
    if segment_playing:
        pause_audio()
    if event.button==1:
        global selection_A, left_select
        
        #get data
        x = event.xdata
        if not(x):
            return
        
        selection_A = x
        selection_B = time_axis[-1]
        left_select = True
        right_select = False
        # set audio
        idcs = np.where(time_axis<selection_A)
        ps = idcs[0][-1]
        sa.audio.setpos(ps)
        
        # popping the 2nd line
        line = ax1.get_lines()
        
        while len(line)>1:
            line[1].remove()
            line = ax1.get_lines()
        # add the red line
        ax1.axvline(x=x, color = 'crimson', lw = 0.5)
        
        patches = ax1.patches
        if len(patches)>0:
              patches.remove(patches[0])
             
        # if (x+x_scale/2)<time_axis[-1] and (x-x_scale/2)>0:
        #     fig.gca().set_xlim((x-x_scale/2), 
        #                        (x+x_scale/2))
        # elif x < x_scale:
        #     fig.gca().set_xlim((0, 
        #                        x_scale))
        # elif x > (time_axis[-1] -x_scale):
        #     fig.gca().set_xlim((time_axis[-1] -x_scale, 
        #                        time_axis[-1]))
            
        # also update the text box:
        for tt in ax2.texts:
            coor = tt.get_position()
            if coor[0] <= x:
                tt.get_bbox_patch().set_facecolor('green')
            else:
                tt.get_bbox_patch().set_facecolor('red')
            
        # canvas.draw()
        # canvas.flush_events()
        # bg = canvas.copy_from_bbox(ax1.bbox)
     #   canvas2.draw()
   #     canvas.draw()
      
    elif event.button==3:
        
        x = event.xdata
        if not(x):
            return
        
        patches = ax1.patches
        if len(patches)>0:
             patches.remove(patches[0])
       # canvas.draw()
        
        
        if not(x<selection_A):
            ytupel =ax1.get_ylim()
            width = event.xdata-selection_A
            ax1.add_patch(Rectangle((selection_A, ytupel[0]), 
                            width, ytupel[1]-ytupel[0], 
                            fc ='cornflowerblue',  
                            ec ='cornflowerblue', 
                            lw = 0, 
                            alpha=0.25) ) 
            selection_B = x
            right_select = True
            # find indies to set the position right
            idcs = np.where(time_axis<selection_B)
            ps = idcs[0][-1]
            sa.audio.setpos(ps)
            # popping the 3rd line
            line = ax1.get_lines()
                        
            while len(line)>2:
                line[2].remove()
                line = ax1.get_lines()
            # add the red line
            ax1.axvline(x=x, color = 'royalblue', lw = 0.5)
            patches = ax1.patches
            
            # also update the text box:
            for tt in ax2.texts:
                coor = tt.get_position()
                if coor[0] <= x:
                    tt.get_bbox_patch().set_facecolor('green')
                else:
                    tt.get_bbox_patch().set_facecolor('red')
        
           # refresh()
        else:
            patches = ax1.patches
            if len(patches)>0:
                  patches.remove(patches[0])
            # popping the 2nd line
            line = ax1.get_lines()
            
            while len(line)>2:
                line[2].remove()
                line = ax1.get_lines()
    canvas.draw()
    #canvas.flush_events
    bg = canvas.copy_from_bbox(ax1.bbox)
def pause_audio():
    if not constructed:
        return
    global playing, segment_playing
    global my_thread

    if playing or segment_playing:
        my_thread.join()
    playing = False
    segment_playing = False
    stream.stop_stream()    
    canvas.flush_events()
def play_audio():
    global playing
    global my_thread
    global bg
    if not constructed or playing:
        return
    
    
    
    if segment_playing:
        pause_audio()
        
    # at = sa.audio.tell()
    # x = time_axis[at]
    # lim_old = ax1.get_xlim()
    # lim_new = (x-x_scale/2, x+x_scale/2)
    # if lim_new[0] < time_axis[0]:
    #     lim_new = (time_axis[0], x_scale)
    # if lim_new[1] > time_axis[-1]:
    #     lim_new = (time_axis[-1]-x_scale,time_axis[-1])
   
    # if not(lim_old == lim_new):
    #     ax1.set_xlim(lim_new)
    #     ax2.set_xlim(lim_new)
 # TODO FIX  draw_words()
    if len(sa.aligned_words)>0:
        draw_words()
    else:
        canvas.draw() 
        #canvas.flush_events()    
    
  #  bg = canvas.copy_from_bbox(ax1.bbox)
    
    playing = True
   
    my_thread = threading.Thread(target=start_audio_stream)
    my_thread.start() 
    
    
   # print('playing audio')
    
def play_pause(event = None):
    if not constructed:
        return
    global playing
    if playing: 
        pause_audio()
    else:
        play_audio()
        
def play_segment():
    if not constructed:
        return
    if not right_select: return
    global playing, segment_playing, my_thread
    if playing:
        pause_audio()
    if not selection_A and selection_B and (selection_B>selection_A):
        return
    playing = True
    segment_playing = True
    idcs = np.where(time_axis<selection_A)
    ps = idcs[0][-1]
    sa.audio.setpos(ps)
    my_thread = threading.Thread(target=start_audio_stream)
    my_thread.start() 
    
   # print('playing audio')     
    
def refresh():
    #print('refresh')
    global segment_playing, bg #, words_in_view
   # global start_time
    
    canvas.restore_region(bg)
    
    at = sa.audio.tell()
    if at == len(time_axis):
        x = time_axis[-1] 
    else:
        x = time_axis[at] #time.thread_time()
   
    lim_old = ax1.get_xlim()
    lim_new = lim_old
    
    line = ax1.get_lines()
    patches = ax1.patches
   
    #print(x)
    # note: make this faster by setting a text index range for bb updata every time the axes are refreshed
    # also add this index variable in the draw words function (it needs to be gobal)
    if not(segment_playing):
        if len(line)>2:
            lin = line[2]
            lin.set_xdata(x)
            lin.set_animated(True)
            ax1.draw_artist(lin)
        elif x>selection_A:
            lin = ax1.axvline(x=x, color = 'royalblue', lw = 0.5)
            lin.set_animated(True)
            ax1.draw_artist(lin)
        
        # if len(line)>1:
        #    # popping the 3rd line
        #     while len(line)>2:
        #         lin = line[2]
        #         ax1.draw_artist(lin)
        #         line[2].remove()
        #         line = ax1.get_lines()
        # lin = ax1.axvline(x=x, color = 'royalblue', lw = 0.5)
        # ax1.draw_artist(lin)
        # only update after middle!
        if x >= lim_old[1]- x_scale/200:
                     
            #ax.set_xlim((lim_[0]+adjust, lim_[1]+adjust))
            lim_new = (x-x_scale/2, x+x_scale/2)
            if lim_new[0] < time_axis[0]:
                lim_new = (time_axis[0], x_scale)
            if lim_new[1] > time_axis[-1]:
                lim_new = (time_axis[-1]-x_scale,time_axis[-1])
            ax1.set_xlim(lim_new)
            ax2.set_xlim(lim_new)
            draw_words()
            bg = canvas.copy_from_bbox(ax1.bbox)
        # i = 0
        # words_in_view = []
        # for word in sa.all_aligned_words:
        #     if word[2]:                    
        #         if lim_new[0]-1< word[2] and lim_new[1]+1> word[2]:
        #             words_in_view.append(i)
        #         i +=1
            
     #update text colors    
    for pp in patches:
        ax1.draw_artist(pp)
    if ax2.texts:
        for tt in ax2.texts:
           
            coor = tt.get_position()
            #if coor[0] > lim_new[0]-x_scale/2 and coor[1] < lim_new[1]+x_scale/2:
            bxp = tt.get_bbox_patch()
            if coor[0] <= x:
                bxp.set_facecolor('green')
            else:
               bxp.set_facecolor('red')
            ax2.draw_artist(tt)
            # ax2.draw_artist(tt)
        # for ii in words_in_view:
           
        #     coor = ax2.texts[ii].get_position()
        #     if coor[0] > lim_new[0]-x_scale/2 and coor[1] < lim_new[1]+x_scale/2:
        #         if coor[0] <= x:
        #             ax2.texts[ii].get_bbox_patch().set_facecolor('green')
        #         else:
        #             ax2.texts[ii].get_bbox_patch().set_facecolor('red')
 #   ylim = ax2.get_ylim()
  #  bx = Bbox([[lim_new[0]-1, ylim[0]], [lim_new[1]-1], ylim[1]])
  #  bx = Bbox([[lim_new[0]-1,ylim[0]],[lim_new[1]-1,ylim[1]]])
   # canvas2.blit(bbox = bx)
    # lines = ax1.get_lines()
    # for ll in lines:
    #     ax1.draw_artist(ll)
    #canvas.restore_region(bg)
    #canvas.draw()
    
    canvas.blit()
    
    # flush_events kills everything on MAC... wtf?
   # canvas.flush_events()
   
    #bg = canvas.copy_from_bbox(ax1.bbox)
    
   # print("FPS: ", 1.0 / ((time.time() - start_time)+0.0000001)) # FPS = 1 / time to process loop
  # start_time = time.time()
#    canvas2.draw()
    if segment_playing and x >= selection_B:
        pause_audio()

def refresh_root():
    #print('refresh_root')
    if playing:
        refresh()
    root.after(17, refresh_root)
def right_step():
    if not constructed:
        return
    if playing or segment_playing:
        return
    global  sa #,words_in_view
    
    xl = ax1.get_xlim()
    if (xl[1]+step_width)<time_axis[-1]:
        ax1.set_xlim((xl[0]+step_width, xl[1]+step_width))
        ax2.set_xlim((xl[0]+step_width, xl[1]+step_width))
    else:
        ax1.set_xlim((time_axis[-1]-x_scale), time_axis[-1])
        ax2.set_xlim((time_axis[-1]-x_scale, time_axis[-1]))
    
    
    
    # new
    line = ax1.get_lines()
    
    while len(line)>1:
        line[1].remove()
        line = ax1.get_lines()
    
    patches = ax1.patches
    if len(patches)>0:
          patches.remove(patches[0])
    
    draw_words() # will draw canvas too
    # i = 0
    # words_in_view = []
    # for word in sa.all_aligned_words:
    #     if word[2]:                    
    #         if xl[0]-1< word[2] and xl[1]+1> word[2]:
    #             words_in_view.append(i)
    #         i +=1
    # canvas.draw()
    # canvas2.draw()

    
    
    draw_words() # will draw canvas too   
def start_audio_stream():
    stream.start_stream()
    
    
def stop_audio():
    global playing, left_select, right_select, selection_A, selection_B
    if playing:
        my_thread.join()
    
    playing = False
    right_select = False
    left_select = False
    selection_A = 0
    selection_B = time_axis[-1]
    stream.stop_stream()
    sa.audio.setpos(int(0))
    patches = ax1.patches
    if len(patches)>0:
        patches.remove(patches[0])
    line = ax1.get_lines()
    while len(line)>1:
        line[1].remove()
        line = ax1.get_lines()
    ax1.set_xlim((0, x_scale))
    ax2.set_xlim((0, x_scale))
    canvas.draw()
    canvas.flush_events()
   # canvas.flush_events()
  #  canvas2.draw()
    
# note insertions need to be sanity checked for empty characters points etc
def txt_update():
    global listbox, last_list_sel
    tmp = listbox.curselection()
    if tmp:
        last_list_sel = tmp
    if not constructed:
        return
    new_words = []
    ix2 = '99.99'
    for word in sa.all_aligned_words:
        try:
            ix1 = txt.index(word[0] + '.first')
        except:
            print("deletion detected")
            continue
                  
        segs1 = ix1.split('.')    
        segs2 = ix2.split('.')   
        if (int(segs1[0])-int(segs2[0]) > 0) or (
                int(segs1[1])-int(segs2[1]) > 1) or (
                    ix2 == '99.99' and not(ix1 == '1.0')): 
                        
            print('insertion detected')
            
            if ix2 == '99.99': ix2 = '1.0'
            
            inserted_text = txt.get(ix2,ix1)
            inserted_words = inserted_text.split()
            for ww in inserted_words:
                ww = ww.translate(str.maketrans('', '',string.punctuation))
                new_words.append((None, ww, None, None))
        
        ix2 = txt.index(word[0] + '.last')
        
        wrd = txt.get(ix1,ix2)
        if not(wrd == word[1]):
            print('change detected')
            new_words.append((word[0], wrd, word[2], word[3]))
        else:
            new_words.append(word)
    remainder = txt.get(ix2,'end')
    if remainder.split():
        print('additional words detected')
        
        inserted_words = remainder.split()
        for ww in inserted_words:
            ww = ww.translate(str.maketrans('', '',string.punctuation))
            new_words.append((None, ww, None, None))
    sa.all_aligned_words = []
    
    tmpid = 0
    for ww in new_words:
            idstring = "w" + str(tmpid)
            sa.all_aligned_words.append((idstring, ww[1], ww[2], ww[3]))
            tmpid +=1
    fill_listbox()
    add_text()
    draw_words()
       


leftphoto = tk.PhotoImage(file = 'semi_files//img//left.png')
#labelphoto.pack()
leftbutton = tk.Button(root,image = leftphoto, command = left_step)
leftbutton.place(x = 0, y = 0, width=30, height=30)

playphoto = tk.PhotoImage(file = 'semi_files//img//play.png')
#labelphoto.pack()
playbutton = tk.Button(root,image = playphoto, command = play_audio)
playbutton.place(x = 30, y = 0, width=30, height=30)

pausephoto = tk.PhotoImage(file = 'semi_files//img//pause.png')
#labelphoto.pack()
pausebutton = tk.Button(root,image = pausephoto, command = pause_audio)
pausebutton.place(x = 60, y = 0, width=30, height=30)

stopphoto = tk.PhotoImage(file = 'semi_files//img//stop.png')
#labelphoto.pack()
stopbutton = tk.Button(root,image = stopphoto, command = stop_audio)
stopbutton.place(x = 90, y = 0, width=30, height=30)


rigthphoto = tk.PhotoImage(file = 'semi_files//img//right.png')
#labelphoto.pack()
rightbutton = tk.Button(root,image = rigthphoto, command = right_step)
rightbutton.place(x = 120, y = 0, width=30, height=30)



segphoto = tk.PhotoImage(file = 'semi_files//img//play2.png')
#labelphoto.pack()
segbutton = tk.Button(root,image = segphoto, command = play_segment)
segbutton.place(x = 150, y = 0, width=30, height=30)


doublerigthphoto = tk.PhotoImage(file = 'semi_files//img//doubleright.png')
#labelphoto.pack()
doublerightbutton = tk.Button(root,image = doublerigthphoto, command = doubleright_step)
doublerightbutton.place(x = 180, y = 0, width=30, height=30)



# add the function for the space bar
root.bind("<Return>", play_pause)

# audioname = 'semi_files//data//grav1.wav'
# textname = 'semi_files//data//grav1.txt'
# add_elements()
# refresh_root()


if open_with_files:
    audioname = 'semi_files//data//grav1.wav'
    textname = 'semi_files//data//grav1.txt'
    add_elements()
    refresh_root()

root.mainloop()
