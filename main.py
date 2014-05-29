#!/usr/bin/python

from __future__ import absolute_import, division, print_function, unicode_literals

"""This is the main file of pytaVSL. It aims to provide a VJing and lights-projector-virtualisation tool.

Images are loaded as textures, which then are mapped onto slides (canvases - 8 of them).

This file was deeply instpired by Slideshow.py demo file of pi3d.
"""

import time, glob, threading
import pi3d
import liblo
import random

from six.moves import queue

LOGGER = pi3d.Log.logger(__name__)
LOGGER.info("Log using this expression.")


class Slide(pi3d.Sprite):
    def __init__(self):
        super(Slide, self).__init__(w=1.0, h=1.0)
        self.visible = False
        self.active = False
        self.fadeup = False

        # Scales
        self.sx = 1.0
        self.sy = 1.0
        self.sz = 1.0

        # Angle
        self.ax = 0.0
        self.ay = 0.0
        self.az = 0.0

    def set_scale(self, sx, sy, sz):
        self.sx = sx
        self.sy = sy
        self.sz = sz
        self.scale(sx, sy, sz)

    def set_angle(self, ax, ay, az):
        # set angle (absolute)
        self.ax = ax
        self.ay = ay
        self.az = az
        self.rotateToX(ax)
        self.rotateToY(ay)
        self.rotateToZ(az)


class Container:
    def __init__(self, parent):
        self.parent = parent
        self.nSli = 8
        self.slides = [None]*self.nSli
        half = 0
        for i in range(self.nSli):
            self.slides[i] = Slide()

        for i in range(self.nSli):
            # never mind this, hop is just to fill in the first series of images from
            # inside-out: 4 3 5 2 6 1 7 0.
            half += (i%2)
            step = (1,-1)[i%2]
            hop = 4 + step*half

            self.slides[hop].positionZ(0.8-(hop/10))
            item = [self.parent.iFiles[hop%self.parent.nFi], self.slides[hop]]
            self.parent.fileQ.put(item)

        self.focus = 3 # holds the index of the focused image
        self.focus_fi = 0 # the file index of the focused image
        self.slides[self.focus].visible = True
        self.slides[self.focus].fadeup = True


    def update(self):
        # for each slide check the fade direction, bump the alpha and clip
        pass

    def draw(self):
        # slides have to be drawn back to front for transparency to work.
        # the 'focused' slide by definition at z=0.1, with deeper z
        # trailing to the left.  So start by drawing the one to the right
        # of 'focused', if it is set to visible.  It will be in the back.
        for i in range(self.nSli):
            ix = (self.focus+i+1)%self.nSli
            if self.slides[ix].visible == True:
                self.slides[ix].draw()
                self.slides[ix].set_alpha(1.0)
            else:
                self.slides[ix].set_alpha(0.0)
            
    def posit(self):
        self.slides[self.focus].translate(random.random()*20-5, random.random()*20-5, 0.0)

    def other(self):
        self.slides[self.focus].visible = False
        self.focus = (self.focus+int(10*random.random()))%self.nSli
        self.slides[self.focus].visible = True


    # def join(self):
    #     print(iFiles)
    #     self.parent.iFiles.extend(glob.glob("/home/orl/barons.png"))
    #     self.parent.nFi = len(iFiles)
    #     print("And now")
    #     print(iFiles)
#        self.slides[self.focus-1].visible = True
#        print(self.slides[self.focus].y())
#        self.slides[self.focus].translate(0.0, -self.slides[self.focus].sy/2.0, 0.0)
#        print(self.slides[self.focus].sy)
#        print(self.slides[self.focus].y())
#        self.slides[self.focus].set_scale(self.slides[self.focus].sx/2.0, self.slides[self.focus].sy/2.0, self.slides[self.focus].sz)
#        self.slides[self.focus].set_angle(self.slides[self.focus].ax/2.0, self.slides[self.focus].ay/2.0, self.slides[self.focus].az)
#        self.slides[self.focus].set_angle(0.0, 0.0, random.random()*360)
#        print(self.slides[self.focus].az)
#        self.slides[self.focus].position(self.slides[self.focus].x(), self.slides[self.focus+1].y(), self.slides[self.focus].z())


class pytaVSL(object):
    def __init__(self, port=56418):
        self.port = port
        self.DISPLAY = pi3d.Display.create(background=(0.0, 0.0, 0.0, 1.0), frames_per_second=25)
        self.shader = pi3d.Shader("uv_flat")
        self.CAMERA = pi3d.Camera(is_3d=False)

        # Loading files in the queue
        self.iFiles = glob.glob("pix/*.*")
        self.nFi = len(self.iFiles)
        self.fileQ = queue.Queue()

        # Containers
        self.ctnr = Container(parent=self)

        # Slides per container
        self.ctnr.nSli = 8
        self.alpha_step=0.025

    def on_start(self):
        if self.port is not None:
            self.server = liblo.ServerThread(self.port)
            self.server.register_methods(self)
            self.server.start()
            print("Listening on OSC port: " + str(self.port))

    def on_exit(self):
        if self.port is not None:
            self.server.stop()
            del self.server

    def tex_load(self):
        """ Threaded function. mimap = False will make it faster.
        """
        while True:
            item = self.fileQ.get()
            # reminder, item is [filename, target Slide]
            fname = item[0]
            slide = item[1]
            tex = pi3d.Texture(item[0], blend=True, mipmap=True)
            xrat = self.DISPLAY.width/tex.ix
            yrat = self.DISPLAY.height/tex.iy
            if yrat < xrat:
                xrat = yrat
            wi, hi = tex.ix * xrat, tex.iy * xrat

            slide.set_draw_details(self.shader,[tex])
            slide.set_scale(wi, hi, 1.0) 
            slide.set_alpha(0)
            self.fileQ.task_done()

    # OSC Methods
    @liblo.make_method('/alpha', 'f')
    def button_cb(self, path, args):
            print(args)
            self.ctnr.slides[self.ctnr.focus].translate(args[0], 0.0, 0.0)




########## MAIN APP ##########

pyta = pytaVSL()
pyta.on_start()

t = threading.Thread(target=pyta.tex_load)
t.daemon = True
t.start()

pyta.fileQ.join()

mykeys = pi3d.Keyboard()
pyta.CAMERA = pi3d.Camera.instance()
pyta.CAMERA.was_moved = False # to save a tiny bit of work each loop

while pyta.DISPLAY.loop_running():
    pyta.ctnr.draw()
    k = mykeys.read()
    
    if k> -1:
        first = False
        if k == 27: #ESC
            mykeys.close()
            DISPLAY.stop()
            break
        #         if k == 115: #S
        #             ctnr.posit()
        #         else:
        #             ctnr.join()

pyta.DISPLAY.destroy()
pyta.destroy()
