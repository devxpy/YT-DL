from youtube_dl import YoutubeDL
from urllib.request import urlretrieve
from tkinter import *
from tkinter import filedialog, ttk, messagebox, font
from PIL import ImageTk, Image
from threading import Thread
import webbrowser
from datetime import datetime
from time import time, sleep
import requests
import os
import subprocess


class Application(Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.wm_title("YT-DL")
        self.master.minsize(width=700, height=400)

        # styling
        self.bgdark='#181818'
        self.bglight = '#222222'
        self.highlit = '#494949'
        self.txt='#F5F5F5'
        self.red = '#DC1826'
        self.master.configure(bg=self.bgdark)
        s = ttk.Style()
        s.theme_create('yummy', settings={
            'TNotebook': {'configure': {'background'  : self.bglight, 'borderwidth':'0', 'tabposition':'n'}},
            'TNotebook.Tab': {'configure': {'focuscolor':['background'],'background': self.bglight, 'foreground': self.txt, 'borderwidth':'0', 'padding':[10,3,10,3] }, 'map' : {'background':[('active', self.highlit)], 'foreground':[('selected',self.red)] } },
            'TProgressbar' : {'configure': {'troughcolor':self.highlit, 'background':self.red, 'borderwidth':'0', 'thickness':10}},
        })

        s.theme_use('yummy')

        # make the tabs
        n = ttk.Notebook(self.master)
        self.main_frame = Frame(n, bg=self.bgdark)
        self.dl_frame = Frame(n, bg=self.bgdark)
        self.log_frame = Frame(n, bg=self.bgdark)
        self.main_frame.config(highlightthickness=0)
        self.dl_frame.config(highlightthickness=0)
        self.log_frame.config(highlightthickness=0)

        self.main_frame.grid_columnconfigure(0,weight=1)
        self.dl_frame.grid_columnconfigure(0,weight=1)
        self.log_frame.grid_columnconfigure(0,weight=1)

        #make the scrollable gui for download
        self.dl_frame.grid_rowconfigure(0, weight=1)
        self.dl_frame.grid_columnconfigure(0, weight=1)

        xscrollbar = Scrollbar(self.dl_frame, orient=HORIZONTAL, bd=0, relief='flat')
        xscrollbar.grid(row=1, column=0, sticky=E+W)

        yscrollbar = Scrollbar(self.dl_frame, orient=VERTICAL, bd=0, relief='flat')
        yscrollbar.grid(row=0, column=1, sticky=N+S)

        self.dl_canvas = Canvas(self.dl_frame, bg=self.bgdark, relief='flat',  bd=0,scrollregion=(0, 0, 2000, 10000), xscrollcommand=xscrollbar.set,  yscrollcommand=yscrollbar.set, background=self.bgdark)
        self.dl_canvas.grid(row=0, column=0, sticky=N+S+E+W)
        self.inner_dl_frame = Frame(self.dl_canvas, bg=self.bgdark)
        self.dl_canvas.create_window(0,0, window=self.inner_dl_frame, anchor='nw')

        xscrollbar.config(command=self.dl_canvas.xview)
        yscrollbar.config(command=self.dl_canvas.yview)

        #add tabs to the notebook
        n.add(self.main_frame, text='     Home    ')
        n.add(self.dl_frame,   text='   Download   ')
        n.add(self.log_frame,  text='     Log        ')
        n.pack(fill=BOTH, expand=1)

        # make the gui for main window
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.entry_frame = Frame(self.main_frame, bg=self.bgdark)
        self.status_frame = Frame(self.main_frame, bg=self.bgdark)
        self.entry_frame.grid(row=0, column=0)
        self.status_frame.grid(row=1,column=0)


        self.url_label = Label(self.entry_frame, bg=self.bgdark, foreground=self.txt, text='Hello there! Copy url of some video from Youtube ')
        self.url_label.grid(sticky='n')

        # scrollable options frame
        opt_frame = Frame(self.main_frame, bg=self.bgdark)
        opt_frame.grid(row=2, column=0, sticky=N+E+S+W)
        opt_frame.grid_columnconfigure(0, weight=1)
        opt_frame.grid_rowconfigure(0, weight=1)

        opts_xscrollbar = Scrollbar(opt_frame, orient=HORIZONTAL, bd=0, relief='flat')
        opts_xscrollbar.grid(row=1, column=0, sticky=E+W)

        opts_yscrollbar = Scrollbar(opt_frame, orient=VERTICAL, bd=0, relief='flat')
        opts_yscrollbar.grid(row=0, column=1, sticky=N+S)

        self.opts_canvas = Canvas(opt_frame,selectborderwidth=0, bg=self.bgdark, relief='flat',  bd=0,scrollregion=(0, 0, 2000, 10000), xscrollcommand=opts_xscrollbar.set,  yscrollcommand=opts_yscrollbar.set, background=self.bgdark)
        self.opts_canvas.grid(row=0, column=0, sticky=N+S+E+W)
        self.options_frame = Frame(self.opts_canvas, bg=self.bgdark)
        self.opts_canvas.create_window(0,0, window=self.options_frame, anchor='nw')

        opts_xscrollbar.config(command=self.opts_canvas.xview)
        opts_yscrollbar.config(command=self.opts_canvas.yview)

        self.display_opts_thread = None # used to determine whether a display options thread is running or not

        # make gui for logger
        self.log_box = Listbox(self.log_frame, width=150, height=20, bg=self.bgdark, foreground=self.txt, activestyle='none', relief='flat', borderwidth=0)
        self.log_box.pack()



        # auto clipboard thread
        Thread(target=self.auto_link).start()
        now = datetime.now()
        self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + 'Automatic link retriever thread started')

        #other variables needed
        self.dl_frames = {}  # stores references to each download frame inside the download tab(dl_frame) --> {<download_id> : <download frame reference>}
        self.download_count = 0  # helps to set the download id
        self.pause_buttons = {}  # stores references of the pause buttons along with the pause value --> {<download_id> : [<pause btn reference>, <pause value(True/False/None)>]}
        self.canvas_dict = {}  # stores canvas for thumbnails in the format --> {<canvas name> : [<canvas_object_reference>, <thumbnail link>]}

    def auto_link(self):
        while True:
            try:
                # get the text that user copied
                text = self.master.clipboard_get().split()[0]
                #verify that the text is a valid url and no other display option thread is running
                if ('youtube.com/watch?v=' in text or 'youtu.be' in text) and self.display_opts_thread is None and text != self.url_label['text']:
                    self.url_label['text'] = text
                    self.status_frame.destroy()
                    self.status_frame = Frame(self.main_frame, bg=self.bgdark)
                    self.status_frame.grid(row=1)
                    Button(self.status_frame, text='Press here / Press Enter', bd=0, cursor='bottom_side', padx=5, bg=self.bglight, foreground=self.txt, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda: self.retrieve_info(text)).grid()
                    self.master.bind("<Return>", lambda _: self.retrieve_info(self.url_label['text']))
                elif ('youtube.com/watch?v=' in text or 'youtu.be' in text) and not self.display_opts_thread.isAlive() and text != self.url_label['text']:
                    self.url_label['text'] = text
                    self.status_frame.destroy()
                    self.status_frame = Frame(self.main_frame, bg=self.bgdark)
                    self.status_frame.grid(row=1)
                    Button(self.status_frame, text='Press here / Press Enter', bd=0, cursor='bottom_side', padx=5, bg=self.bglight, foreground=self.txt, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda: self.retrieve_info(text)).grid()
                    self.master.bind("<Return>", lambda _: self.retrieve_info(self.url_label['text']))
                else:
                    self.master.bind("<Return>", None)
            except:
                pass
            sleep(1)

    def display_onframe(self, name, url_dict, link, thumb_url, audio_stream, num):

        f = Frame(self.options_frame, bg=self.bgdark, padx=5, pady=10)
        f.grid(row=num)
        # canvas for thumbnails
        self.canvas_dict['canvas' + str(num)] = [Canvas(f, width=190, height=110, bg=self.bgdark, cursor = 'draft_small'), thumb_url]
        self.canvas_dict['canvas' + str(num)][0].config(highlightthickness=0)
        self.canvas_dict['canvas' + str(num)][0].bind("<Button-1>", lambda _: webbrowser.open(link))
        self.canvas_dict['canvas' + str(num)][0].grid(column=0, row=1)

        # label for vid name
        if len(name) > 35:
            show_name = name[:33] + ' ..'
        else:
            show_name = name
        Label(f, text=show_name, padx=10, bg=self.bgdark, foreground=self.txt).grid(column=0, row=0)

        # buttons for quality selection
        # video buttons
        btn_col = 1
        for quality in url_dict:  # url_dict format -->  {<quality> : [<video url>, <total filesize>]}

            if 'mp4' in quality:
                btn_text = quality + str(round((url_dict[quality][1]+audio_stream[1]) / 1048576, 2)) + ' MB'
            else:
                btn_text = quality

            Button(f, text=str(btn_text), padx=5, bg=self.bglight, bd=0, cursor='bottom_side', foreground=self.txt, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda n=name, l=link, q=quality, dl_url=url_dict[quality][0], tot=url_dict[quality][1], a=audio_stream: self.add_download(n, dl_url, l, q, a, tot)).grid( column=btn_col, row=1)
            btn_col += 1

        # audio button
        if audio_stream is not None:  # audio_stream format --> [<audio url>, <audio filesize>]
            quality = str('Audio (mp3)\n') + str(round(audio_stream[1] / 1048576, 2)) + ' MB'
            Button(f, text=quality, padx=5, bg=self.bglight, bd=0, cursor='bottom_side', foreground=self.txt, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda n=name, l=link, q=quality, dl_url=audio_stream[0], tot=audio_stream[1]: self.add_download(n, dl_url, l, q, None, tot)).grid(column=btn_col, row= 1)

    def display_options(self, url):
        try:
            req_info = {}  # -->  {<quality> : [<video url>, <total filesize>]}
            ydl_opts = {'simulate':True, 'quiet':True}

            with YoutubeDL(ydl_opts) as ydl:
                total_info = ydl.extract_info(url)

                # url is not a playlist
                if 'formats' in total_info:
                    audio_stream = None
                    # collect specific information for each different resolution and make a dict
                    for i in total_info['formats']:

                        if 'mp4' in i['ext'] and i['acodec'] == 'none':  # filter DASH mp4
                            total_size = int(i['filesize'])
                            if i['fps'] > 30:
                                fps = str(i['fps'])
                            else:
                                fps = ''
                            req_info[str(i['height']) + 'p %s (mp4)\n' % fps] = [i['url'], total_size]

                        elif 'm4a' in i['ext']:  # filter DASH m4a
                            total_size = int(i['filesize'])
                            audio_stream = [i['url'], total_size]

                        elif '3gp' in i['ext'] and i['acodec'] != 'none':  # filter 3gp with audio streams present
                            total_size = int(requests.get(i['url'], stream=True, timeout=5).headers['Content-Length'])
                            req_info[str(i['height']) + 'p (3gp)\n' + str(round(total_size / 1048576, 2)) + ' MB'] = [
                                i['url'], total_size]

                        else:
                            pass

                    name = ''.join([y for y in total_info['title'] if ord(y) < 65535])
                    self.display_onframe(name, req_info, url, total_info['thumbnail'], audio_stream, 0)

                # url is a playlist
                else:
                    num = 0

                    # iterates through each entry. each entry has info for different video
                    for foo in total_info['entries']:

                        req_info = {}
                        total_info = ydl.extract_info('https://www.youtube.com/watch?v=' + foo['id'])
                        audio_stream = None

                        # collect specific information for each different resolution and make a dict
                        for i in total_info['formats']:

                            if 'mp4' in i['ext'] and i['acodec'] == 'none':  # filter DASH mp4
                                total_size = int(i['filesize'])
                                if i['fps'] > 30:
                                    fps = str(i['fps'])
                                else:
                                    fps = ''
                                req_info[str(i['height']) + 'p %s (mp4)\n' % fps] = [i['url'], total_size]

                            elif 'm4a' in i['ext']:  # filter DASH m4a
                                total_size = int(i['filesize'])
                                audio_stream = [i['url'], total_size]

                            elif '3gp' in i['ext'] and i['acodec'] != 'none':  # filter 3gp with audio streams present
                                total_size = int(
                                    requests.get(i['url'], stream=True, timeout=5).headers['Content-Length'])
                                req_info[str(i['height']) + 'p \n' + str(round(total_size / 1048576, 2)) + ' MB'] = [
                                    i['url'], total_size]

                            else:
                                pass

                        name = ''.join([y for y in total_info['title'] if ord(y) < 65535])
                        self.display_onframe(name, req_info, 'https://www.youtube.com/watch?v=' + foo['id'],
                                             total_info['thumbnail'], audio_stream, num)
                        num += 2

            # till now, we would have successfully showed the available formats using the display_onframe()
            # display_onframe() also creates a canvas dict  -->  {<canvas name> : [<canvas_object_reference>, <thumbnail link>]}
            # so now, we can show thumbnails
            for foobar in self.canvas_dict:
                # download thumbnail
                filename, headers = urlretrieve(self.canvas_dict[foobar][1])
                # make an image object
                im = Image.open(filename)
                out = im.resize((190, 110))
                # Put the image into a canvas compatible class, and stick in an
                # arbitrary variable so the garbage collector doesn't destroy it
                self.canvas_dict[foobar][0].image = ImageTk.PhotoImage(out)
                # Add the image to the canvas
                self.canvas_dict[foobar][0].create_image(0, 0, image=self.canvas_dict[foobar][0].image, anchor='nw')

            now = datetime.now()
            self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + 'Display options thread ended')

            # update the status bar
            self.status_frame.destroy()
            self.status_frame = Frame(self.main_frame, bg=self.bgdark)
            self.status_frame.grid(row=1)
            Label(self.status_frame, text='Select a quality or copy another link', bg=self.bgdark, foreground=self.txt).grid()

        except:
            # clear options frame
            self.options_frame.destroy()
            self.options_frame = Frame(self.opts_canvas, bg=self.bgdark)
            self.opts_canvas.create_window(0,0, window=self.options_frame, anchor='nw')

            # update the status bar..
            self.status_frame.destroy()
            self.status_frame = Frame(self.main_frame, bg=self.bgdark)
            self.status_frame.grid(row=1)
            Button(self.status_frame, text='Can\'t connect to server. Press here / Enter to retry',  bd=0, cursor='bottom_side', padx=5, bg=self.bglight, foreground=self.txt, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda: self.retrieve_info(url)).pack()

            now = datetime.now()
            self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + 'Display options thread ended')

    def retrieve_info(self, url):
            if  self.display_opts_thread is None :
                pass
            elif not self.display_opts_thread.isAlive():
                pass
            else:
                return None
            # clear the status frame and update it
            self.status_frame.destroy()
            self.canvas_dict = {}
            self.status_frame = Frame(self.main_frame, bg=self.bgdark)
            self.status_frame.grid(row=1)
            Label(self.status_frame, text='Figuring out some stuff..', bg=self.bgdark, foreground=self.txt).grid(row=0, column=0)

            # clear the options frame and update it
            self.options_frame.destroy()
            self.options_frame = Frame(self.opts_canvas, bg=self.bgdark)
            self.opts_canvas.create_window(0,0, window=self.options_frame, anchor='nw')

            # start thread to display options for user
            self.display_opts_thread = Thread(target=self.display_options, args=(url,))
            self.display_opts_thread.start()
            now = datetime.now()
            self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + 'Display options thread started')

    def add_download(self, name, dl_url, link, quality, audio_stream, total_size):
        if 'Audio' in quality:
            directory = filedialog.asksaveasfilename(defaultextension='.m4a', confirmoverwrite=False,
                                                     filetypes=(("Audio Files", "*.mp3"),),
                                                     initialfile=''.join([t for t in name if t.isalnum() or t == ' ']).encode('ascii', 'ignore'))
        elif '3gp' in quality:
            directory = filedialog.asksaveasfilename(defaultextension='.3gp', confirmoverwrite=False,
                                                     filetypes=(("Video Files", "*.3gp"),),
                                                     initialfile=''.join([t for t in name if t.isalnum() or t == ' ']).encode('ascii', 'ignore'))
        elif 'mp4' in quality:
            directory = filedialog.asksaveasfilename(defaultextension='.mp4', confirmoverwrite=False,
                                                     filetypes=(("Video Files", "*.mp4"),),
                                                     initialfile=''.join([t for t in name if t.isalnum() or t ==    ' ']).encode('ascii', 'ignore'))
        else:
            return None

        if directory != '':  # check if the user cancelled the dialog...
            self.download_count += 1

            # make GUI for the specific download
            if len(name) > 35:
                show_name = name[:33] + '...'
            else:
                show_name = name

            download_id = 'dl_no' + str(self.download_count)  # generate a download_id for future use
            self.dl_frames[download_id] = Frame(self.inner_dl_frame, bg=self.bgdark, padx =10, pady=10, background=self.bgdark)  # put a frame made using the download_id inside our dl_frames dict
            self.dl_frames[download_id].grid(sticky='nw')

            progbar = ttk.Progressbar(self.dl_frames[download_id], length=100, mode='determinate')
            Label(self.dl_frames[download_id], text=show_name, bg=self.bgdark, foreground=self.txt).grid(row=0, column=2)
            status_label = Label(self.dl_frames[download_id], text=' Connecting.. ', bg=self.bgdark, foreground=self.txt)
            size_label = Label(self.dl_frames[download_id], width=30, text='Down : 00 of 00 MB', bg=self.bgdark, foreground=self.txt)
            left_label = Label(self.dl_frames[download_id], width=20, text='Rem : 00 MB', bg=self.bgdark, foreground=self.txt)
            eta_label = Label(self.dl_frames[download_id], width=20, text='ETA : 00 mins', bg=self.bgdark, foreground=self.txt)
            speed_label = Label(self.dl_frames[download_id], width=25, text='Rate : 00 KB/s', bg=self.bgdark, foreground=self.txt)

            eta_label.grid(row=0, column=3,)
            left_label.grid(row=0, column=4)
            size_label.grid(row=0, column=5)
            progbar.grid(row=0, column=6, padx=10 )
            status_label.grid(row=0, column=7)
            speed_label.grid(row=0, column=8)

            # pause button, placed inside the pause_buttons dict
            self.pause_buttons[download_id] = [Button(self.dl_frames[download_id], font=font.Font(size='10'), bg=self.bgdark, bd=0, cursor='circle', foreground=self.txt, relief='flat', activebackground=self.highlit, activeforeground=self.txt, text='⚫',
                                                      command=lambda d=download_id: pause_resume_download(d)),False]
            def pause_resume_download(d_id):
                self.pause_buttons[d_id][1] = not self.pause_buttons[d_id][1]
            self.pause_buttons[download_id][0].grid(row=0, column=0, padx=5)


            # button to kill download
            Button(self.dl_frames[download_id],font=font.Font(size='10'), text='✕', bg=self.bgdark, bd=0, cursor='x_cursor', foreground=self.red, relief='flat', activebackground=self.highlit, activeforeground=self.txt,
                   command=lambda d_id=download_id: remove_download(d_id)).grid(row=0, column=1, padx=5)
            def remove_download(d_id):
                self.pause_buttons[d_id][1] = None


            # try to open the file. if file opens, then the file already exists, thus we may ask if user wants to resume download or not
            try:
                f = open(directory, "r")
                f.close()
                size_on_disk = os.stat(directory).st_size
                # asks if user wants to resume download
                if messagebox.askyesno("Duplicate File Name", "Resume download from earlier?"):

                    if 'mp4' in quality:
                        # if download was already complete
                        if size_on_disk >= total_size + audio_stream[1]:
                            self.on_download_finish(download_id, directory)
                            return None

                        # only video part was downloaded
                        elif size_on_disk >= total_size:
                            size_on_disk = -1

                        else:
                            pass

                    else:
                        if os.stat(directory).st_size >= total_size:
                            self.on_download_finish(self, download_id, directory)
                            return None
                        else:
                            pass

                # user don't wanna resume download
                else:
                    size_on_disk = 0
            # file doesnt exist
            except:
                size_on_disk = 0

            # start download thread
            if 'mp4' in quality:
                Thread(target=self.download_dash, args=(
                    link, quality, audio_stream, dl_url, directory, total_size, progbar, size_label,
                    left_label,
                    eta_label,
                    speed_label, status_label,  download_id, size_on_disk)).start()
            else:
                Thread(target=self.download, args=(
                    link, quality, dl_url, directory, total_size, progbar, size_label,  left_label,
                    eta_label,
                    speed_label, status_label,  download_id, size_on_disk)).start()

            now = datetime.now()
            self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + 'Got URL: ' + dl_url)
            self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                -1] + ' - download thread started')

        else:  # user cancelled the save file dialog
            return None


    def download(self, link, quality, dl_url, directory, total_size, progbar, size_label,
                  left_label,
                 eta_label, speed_label, status_label,  download_id, size_on_disk):
        retries = 50
        total = total_size - size_on_disk
        num = 0
        size = 1024 * 64


        if size_on_disk == 0:
            write_mode = 'wb'
        else:
            write_mode = 'ab'

        with open(directory, write_mode) as downloaded_file:
            for retry in range(retries):
                try:
                    if retry != 0:
                        size_on_disk = total_size - total + (num * size)
                        # get new download link from youtube
                        ydl_opts = {'simulate':True, 'quiet':True}
                        with YoutubeDL(ydl_opts) as ydl:
                            total_info = ydl.extract_info(link)
                            # collect specific information for each different resolution and make a dict
                            for i in total_info['formats']:

                                if 'm4a' in i['ext'] and 'm4a' in quality:  # filter audio only
                                    dl_url = i['url']
                                    break

                                elif '3gp' in i['ext'] and i[
                                    'acodec'] != 'none' and '3gp' in quality:  # filter 3gp with audio streams present
                                    if str(i['height']) in quality:  # checking if the format is of selected quality
                                        dl_url = i['url']
                                        break
                                else:
                                    pass

                    # make a new request
                    req = requests.get(dl_url, stream=True, headers={'Range': 'bytes=%d-' % size_on_disk}, timeout=5)
                    total = int(req.headers['Content-Length'])  # represents the size to be downloaded
                    num = 0
                    start = time()
                    status_label['text'] = 'Downloading..'

                    for chunk in req.iter_content(size):
                        if chunk:  # check for empty chunk
                            if self.pause_buttons[download_id][1]:  # if pause is set to true
                                pause_start = time()  # record when the download was paused

                                status_label['text'] = 'Paused'
                                self.pause_buttons[download_id][0]['text'] = '►'

                                while True:
                                    if not self.pause_buttons[download_id][1]:  # if pause is set to false
                                        status_label['text'] = 'Downloading..'
                                        self.pause_buttons[download_id][0]['text'] = '⚫'

                                        pause_end = time()  # record when the download resumed
                                        start = start + (
                                            pause_end - pause_start)  # modify the start time to correctly fir
                                        break  # break free from this infinite loop, effectively resuming the download

                                    else:  # if pause is still True
                                        sleep(1)  # to prevent thread from hanging up

                            if self.pause_buttons[download_id][1] is None:  # means that user cancelled the download
                                self.dl_frames[download_id].destroy()
                                del self.dl_frames[download_id]
                                del self.pause_buttons[download_id]
                                req.close()
                                now = datetime.now()
                                self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                                    -1] + ' - download thread ended')
                                return None

                            # write the chunk to file
                            downloaded_file.write(chunk)
                            num += 1

                            if num * size >= total:  # if file was downloaded
                                if 'Audio' in quality:
                                    task = ['ffmpeg', '-i', directory, '-c:a', 'libmp3lame', '-ac', '2', '-q:a', '2',
                                            '-y',
                                            ".".join(directory.split(".")[:-1]) + '.mp3']
                                    subprocess.check_call(task)

                                    # delete the m4a file
                                    downloaded_file.close()
                                    os.remove(directory)
                                    directory = ".".join(directory.split(".")[:-1]) + '.mp3'

                                self.on_download_finish(download_id, directory)
                                return None

                            # do come calculation and update info
                            total_percent = ((total_size - total + (num * size)) / total_size) * 100
                            progbar['value'] = total_percent
                            size_label['text'] = 'Down : ' + str(round((total_size - total + (num * size)) / 1048576, 2)) + ' of ' + str(round(total_size / 1048576, 2)) + ' MB'
                            left_label['text'] = 'Rem : ' + str(round((total - (num * size)) / 1048576, 2)) + ' MB'

                            percent = ((num * size) / total) * 100
                            end = time()
                            if end != start:
                                speed = percent / (end - start)  # percentage/sec
                                eta_label['text'] = 'ETA : ' + str(
                                    round((100 - percent) / (speed * 60), 2)) + ' mins'
                                speed_label['text'] = 'Rate : ' + str(
                                    round(((speed / 100) * total) / 1024, 1)) + ' KB/s'

                except:
                    status_label['text'] = 'Retrying..'
                    sleep(0.5)
                    if retry == retries - 1:  # if all retries failed
                        self.on_download_finish(download_id, directory, failed=True)
                        return None

                    elif self.pause_buttons[download_id][1] is None:  # means that user cancelled the download
                        self.dl_frames[download_id].destroy()
                        del self.dl_frames[download_id]
                        del self.pause_buttons[download_id]
                        now = datetime.now()
                        self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                            -1] + ' - download thread ended')
                        return None

                    else:  # go try once more
                        pass

    def download_dash(self, link, quality, audio_stream, dl_url, directory, total_video_size, progbar, size_label,
                       left_label, eta_label, speed_label, status_label,  download_id,
                      size_on_disk):
        retries = 50
        size = 1024 * 25
        num = 0

        if size_on_disk != -1:
            # download the video part
            if size_on_disk == 0:
                write_mode = 'wb'
            else:
                write_mode = 'ab'
            total = total_video_size - size_on_disk
            with open(directory, write_mode) as downloaded_file:
                for retry in range(retries):
                    try:
                        if retry != 0:
                            size_on_disk = total_video_size - total + (
                                num * size)  # pos = total video size - size of remaining part to be downloaded + amount downloaded till now
                            # get new download link from youtube
                            ydl_opts = {'simulate':True, 'quiet':True}
                            with YoutubeDL(ydl_opts) as ydl:
                                total_info = ydl.extract_info(link)
                                for i in total_info['formats']:

                                    if 'mp4' in i['ext'] and i[
                                                               'acodec'] == 'none':  # filter mp4 with audio streams present
                                        if str(i['height']) in quality and i['filesize'] == total_video_size:
                                            dl_url = i['url']
                                            break
                                    else:
                                        pass

                        # Make a request to download video
                        req = requests.get(dl_url, stream=True, headers={'Range': 'bytes=%d-' % size_on_disk},
                                           timeout=5)
                        total = int(req.headers['Content-Length'])  # represents the size to be downloaded
                        start = time()
                        num = 0
                        # iterates over the request
                        status_label['text'] = 'Downloading..'
                        for chunk in req.iter_content(size):
                            if chunk:  # check for empty chunk
                                if self.pause_buttons[download_id][1]:  # if pause is set to true
                                    pause_start = time()  # record when the download was paused

                                    status_label['text'] = 'Paused'
                                    self.pause_buttons[download_id][0]['text'] = '►'

                                    while True:
                                        if not self.pause_buttons[download_id][1]:  # if pause is set to false
                                            status_label['text'] = 'Downloading..'
                                            self.pause_buttons[download_id][0]['text'] = '⚫'

                                            pause_end = time()  # record when the download resumed
                                            start = start + (
                                                pause_end - pause_start)  # modify the start time to correctly fir
                                            break  # break free from this infinite loop, effectively resuming the download

                                        else:  # if pause is still True
                                            sleep(1)  # to prevent thread from hanging up

                                if self.pause_buttons[download_id][1] is None:  # means that user cancelled the download
                                    self.dl_frames[download_id].destroy()
                                    del self.dl_frames[download_id]
                                    del self.pause_buttons[download_id]
                                    req.close()
                                    now = datetime.now()
                                    self.log_box.insert(END,
                                                        str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                                                            -1] + ' - download thread ended')
                                    return None

                                # write the chunk to file
                                downloaded_file.write(chunk)
                                num += 1

                                if num * size >= total:  # if file was downloaded
                                    req.close()
                                    break

                                # do come calculation and update info
                                total_percent = ((total_video_size - total + (num * size)) / (
                                    total_video_size + audio_stream[1])) * 100
                                progbar['value'] = total_percent
                                size_label['text'] = 'Down : ' + str(
                                    round((total_video_size - total + (num * size)) / 1048576, 2)) + ' of ' +  str(round((total_video_size + audio_stream[1]) / 1048576, 2)) + ' MB'
                                left_label['text'] = 'Rem : ' + str(
                                    round(((total + audio_stream[1]) - (num * size)) / 1048576, 2)) + ' MB'

                                percent = ((num * size) / total) * 100
                                end = time()
                                if end != start:
                                    speed = percent / (end - start)  # percentage/sec
                                    eta_label['text'] = 'ETA : ' + str(
                                        round((100 - total_percent) / (speed * 60), 2)) + ' mins'
                                    speed_label['text'] = 'Rate : ' + str(
                                        round(((speed / 100) * total) / 1024, 1)) + ' KB/s'

                        break

                    except:
                        if self.pause_buttons[download_id][1] is None:  # means that user cancelled the download
                            self.dl_frames[download_id].destroy()
                            del self.dl_frames[download_id]
                            del self.pause_buttons[download_id]
                            now = datetime.now()
                            self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                                -1] + ' - download thread ended')
                            return None

                        elif retry == retries - 1:  # if all retries failed
                            self.on_download_finish(download_id, directory, failed=True)
                            return None

                        else:
                            status_label['text'] = 'Retrying..'
                            sleep(0.5)

        # download audio
        temp = '/'.join(directory.split('/')[:-1]) + '/TMP'
        size = 1024 * 25
        num = 0
        dl_url, total = audio_stream
        with open(temp, 'wb') as audio_file:
            for retry in range(retries):
                try:
                    if retry == 0:
                        pos = 0
                    else:
                        # get new download link from youtube
                        ydl_opts = {'simulate':True, 'quiet':True}
                        with YoutubeDL(ydl_opts) as ydl:
                            total_info = ydl.extract_info(link)
                            for i in total_info['formats']:
                                if 'm4a' in i['ext']:  # filter mp4 with audio streams present
                                    dl_url = i['url']
                                    break
                                else:
                                    pass
                        pos = audio_stream[1] - total + (
                            num * size)  # pos = total video size - total video size supposed to be downloaded + amount downloaded till now

                    status_label['text'] = 'Downloading (Audio)'
                    req = requests.get(dl_url, stream=True, headers={'Range': 'bytes=%d-' % pos}, timeout=5)
                    total = int(req.headers['Content-Length'])
                    num = 0
                    start = time()
                    for chunk in req.iter_content(size):
                        if chunk:
                            if self.pause_buttons[download_id][1]:  # if pause is set to true
                                pause_start = time()  # record when the download was paused

                                status_label['text'] = 'Paused'
                                self.pause_buttons[download_id][0]['text'] = '►'

                                while True:
                                    if not self.pause_buttons[download_id][1]:  # if pause is set to false
                                        status_label['text'] = 'Downloading..'
                                        self.pause_buttons[download_id][0]['text'] = '⚫'

                                        pause_end = time()  # record when the download resumed
                                        start = start + (
                                            pause_end - pause_start)  # modify the start time to correctly fir
                                        break  # break free from this infinite loop, effectively resuming the download

                                    else:  # if pause is still True
                                        sleep(1)  # to prevent thread from hanging up

                            if self.pause_buttons[download_id][1] is None:  # means that user cancelled the download
                                self.dl_frames[download_id].destroy()
                                del self.dl_frames[download_id]
                                del self.pause_buttons[download_id]
                                req.close()
                                now = datetime.now()
                                self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                                    -1] + ' - download thread ended')
                                return None

                            # write to file
                            audio_file.write(chunk)
                            num += 1

                            if num * size >= audio_stream[1]:
                                req.close()
                                break

                            # do come calculation and update info
                            total_percent = ((total_video_size + audio_stream[1] - total + (num * size)) / (
                                total_video_size + audio_stream[1])) * 100
                            progbar['value'] = total_percent
                            size_label['text'] = 'Down : ' + str(
                                    round((total_video_size - total + (num * size)) / 1048576, 2)) + ' of ' + str(
                                round((total_video_size + (num * size)) / 1048576, 2)) + ' MB'
                            left_label['text'] = 'Rem : ' + str(
                                round((total - (num * size)) / 1048576, 2)) + ' MB'

                            percent = ((num * size) / total) * 100
                            end = time()
                            if end != start:
                                speed = percent / (end - start)  # percentage/sec
                                eta_label['text'] = 'ETA : ' + str(
                                    round((100 - total_percent) / (speed * 60), 2)) + ' mins'
                                speed_label['text'] = 'Rate : ' + str(
                                    round(((speed / 100) * total) / 1024, 1)) + ' KB/s'

                    break

                except:
                    if self.pause_buttons[download_id][1] is None:  # means that user cancelled the download
                        self.dl_frames[download_id].destroy()
                        del self.dl_frames[download_id]
                        del self.pause_buttons[download_id]
                        now = datetime.now()
                        self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                            -1] + ' - download thread ended')
                        return None

                    elif retry == retries - 1:  # if all retries failed
                       self.on_download_finish(download_id, directory, failed=True)
                       return None

                    else:
                        status_label['text'] = 'Retrying..'
                        sleep(0.5)

        status_label['text'] = 'Combining parts'
        # add audio to video
        task = ['MP4Box', '-add', temp, directory]
        subprocess.check_call(task)
        self.on_download_finish(download_id, directory)
        return None


    def on_download_finish(self, download_id, directory, failed=False ):
        # delete respective frame and replace with fresh one
        self.dl_frames[download_id].destroy()
        self.dl_frames[download_id] = Frame(self.inner_dl_frame, bg=self.bgdark)
        self.dl_frames[download_id].grid(row=download_id[-1])
        del self.pause_buttons[download_id]

        # put stuff into the new frame
        if failed is True:
            now = datetime.now()
            Label(self.dl_frames[download_id],
                  text='Your download ' + directory.split('/')[-1] + ' failed at ' + str(
                      now.time().strftime(
                          '%I:%M %p')) + '\n Please check connection', bg=self.bgdark, foreground=self.txt).grid(column=1, row=0)
            Button(self.dl_frames[download_id], font=font.Font(size='10'), text='✕', bg=self.bgdark, bd=0, cursor='x_cursor', foreground=self.red, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda: close()).grid(column=0,row=0)
            def close():
                self.dl_frames[download_id].destroy()
                del self.dl_frames[download_id]
                now = datetime.now()
                self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                                        -1] + ' - download thread ended')

            return None

        else:
            now = datetime.now()
            Label(self.dl_frames[download_id],
                  text='Your download for ' + directory.split('/')[-1] + ' was successful on ' + str(
                      now.time().strftime('%I:%M %p')), bg=self.bgdark, foreground=self.txt).grid(column=3, row=0)

            Button(self.dl_frames[download_id], font=font.Font(size='15'), text='↗', bg=self.bgdark, bd=0, cursor='x_cursor', foreground=self.red, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda d=directory: os.startfile('/'.join(d.split('/')[:-1]))).grid(column=0, row=0)
            Button(self.dl_frames[download_id], font=font.Font(size='15'), text='▶', bg=self.bgdark, bd=0, cursor='x_cursor', foreground=self.red, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda d=directory: os.startfile(d, 'open')).grid(column=1, row=0)
            Button(self.dl_frames[download_id], font=font.Font(size='10'), text='✕', bg=self.bgdark, bd=0, cursor='x_cursor', foreground=self.red, relief='flat', activebackground=self.highlit, activeforeground=self.txt, command=lambda d=directory: close()).grid(column=2, row=0)

            def close():
                self.dl_frames[download_id].destroy()
                del self.dl_frames[download_id]
                now = datetime.now()
                self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                    -1] + ' - download thread ended')

            now = datetime.now()
            self.log_box.insert(END, str(now.time().strftime('%I:%M %p  :')) + directory.split('/')[
                -1] + ' - download thread ended')

            return None

if __name__ == "__main__":
    root = Tk()
    app = Application(root)
    app.mainloop()
