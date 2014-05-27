#!/usr/bin/python

from __future__ import absolute_import, division, print_function, unicode_literals

"""This is the main file of pytaVSL, and aims to provide a VJing and lights-projector-virtualisation tool.

Images are loaded as textures, which then are mapped onto slides (canvases - 8 of them).

This file was deeply instpired by Slideshow.py demo file of pi3d.
"""

import time, glob, threading
import pi3d
import liblo

from six.moves import queue

LOGGER = pi3d.Log.logger(__name__)
LOGGER.info("Log using this expression.")

# Setup display and initialiser pi3d
DISPLAY = pi3d.Display.create(background=(0.0, 0.0, 0.0, 1.0), frames_per_second=18)
shader = pi3d.Shader("uv_flat")
CAMERA = pi3d.Camera(is_3d=False)
drawFlag = False


# Loading files in the queue
iFiles = glob.glob("pix/*.*")
nFi = len(iFiles)
fileQ = queue.Queue()

# Slides
nSli = 8

def tex_load():
    """ Threaded function. mimap = False will make it faster.
    """
    while True:
        item = fileQ.get()
        # reminder, item is [filename, target Slide]
        fname = item[0]
        slide = item[1]
        tex = pi3d.Texture(item[0], blend=True, mipmap=True)
        xrat = DISPLAY.width/tex.ix
        yrat = DISPLAY.height/tex.iy
        if yrat < xrat:
            xrat = yrat
        wi, hi = tex.ix * xrat, tex.iy * xrat
        slide.set_draw_details(shader,[tex])
        slide.scale(wi, hi, 1.0)
        slide.set_alpha(0)
        fileQ.task_done()


class Slide(pi3d.Sprite):
    def __init__(self):
        super(Slide, self).__init__(w=1.0, h=1.0)
        self.visible = False
        self.active = False
        self.fadeup = False

class Container:
    def __init__(self):
        self.slides = [None]*nSli
        half = 0
        for i in range(nSli):
            self.slides[i] = Slide()
            self.slides[i].positionZ(0.1*i + 0.1)
            item = [iFiles[i%nFi], self.slides[i]]
            fileQ.put(item)

        self.focus = 7
        self.focus_fi = 7
        self.slides[self.focus].visible = True

    def draw(self):
        for i in range(nSli):
            ix = (self.focus+i+1)%nSli
            if self.slides[ix].visible == True:
                self.slides[ix].draw()

    def update(self):
        # for each slide check the fade direction, bump the alpha and clip
        for i in range(nSli):
            a = self.slides[i].alpha()
            if self.slides[i].fadeup == True and a < 1:
                a += alpha_step
                self.slides[i].set_alpha(a)
                self.slides[i].visible = True
                self.slides[i].active = True
            elif self.slides[i].fadeup == False and a > 0:
                a -= alpha_step
                self.slides[i].set_alpha(a)
                self.slides[i].visible = True
                self.slides[i].active = True
            else:
                if a <= 0:
                    self.slides[i].visible = False
                self.slides[i].active = False
                    

ctnr = Container()

t = threading.Thread(target=tex_load)
t.daemon = True
t.start()

fileQ.join()

mykeys = pi3d.Keyboard()
CAMERA = pi3d.Camera.instance()
CAMERA.was_moved = False # to save a tiny bit of work each loop


while DISPLAY.loop_running():
    ctnr.update()
    ctnr.draw()

    k = mykeys.read()

    if k> -1:
        first = False
        if k == 27: #ESC
            mykeys.close()
            DISPLAY.stop()
            break

DISPLAY.destroy()
