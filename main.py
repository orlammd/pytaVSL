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
import os.path

from six.moves import queue

LOGGER = pi3d.Log.logger(__name__)
LOGGER.info("Log using this expression.")


class Slide(pi3d.Sprite):
    def __init__(self):
        super(Slide, self).__init__(w=1.0, h=1.0)
        self.visible = False
        self.slide_infos = False

        # Scales
        self.sx = 1.0
        self.sy = 1.0
        self.sz = 1.0

        # Angle
        self.ax = 0.0
        self.ay = 0.0
        self.az = 0.0

        # Mask Slide
        self.mask = pi3d.Sprite()
        self.mask_on = False


    def set_position(self, x, y, z):
        self.position(x, y, z)
        self.mask.position(x, y, z+0.1)

    def set_translation(self, dx, dy, dz):
        self.translate(dx, dy, dz)
        self.mask.translate(dx, dy, dz)

    def set_scale(self, sx, sy, sz):
        self.sx = sx
        self.sy = sy
        self.sz = sz
        self.scale(sx, sy, sz)
        if self.mask_on:
            self.mask.scale(sx, sy, sz)

    def set_angle(self, ax, ay, az):
        # set angle (absolute)
        self.ax = ax
        self.ay = ay
        self.az = az
        self.rotateToX(ax)
        self.rotateToY(ay)
        self.rotateToZ(az)
        if self.mask_on:
            self.mask.rotateToX(ax)
            self.mask.rotateToY(ay)
            self.mask.rotateToZ(az)


class Container:
    def __init__(self, parent, nSli):
        self.parent = parent
        self.nSli = nSli # number of slides per container
        self.slides = [None]*self.nSli
        for i in range(self.nSli):
            # Textured Slides
            self.slides[i] = Slide()

            self.slides[i].positionZ(0.8-(i/10))
            item = [self.parent.iFiles[i%self.parent.nFi], self.slides[i]]
            self.parent.fileQ.put(item)


            # Mask Slides
            self.slides[i].mask.set_shader(self.parent.matsh)
            self.slides[i].mask.set_material((1.0, 0.0, 0.0))
            self.slides[i].mask.positionZ(0.81-(i/10))

        self.focus = 0 # holds the index of the focused image
        self.slides[self.focus].visible = True

    def slide_info(self, si):
        for i in range(self.nSli):
            if i != si:
                self.slides[i].slide_infos = False
            else:
                self.slides[i].slide_infos = True


    def draw(self):
        # slides have to be drawn back to front for transparency to work.
        # the 'focused' slide by definition at z=0.1, with deeper z
        # trailing to the left.  So start by drawing the one to the right
        # of 'focused', if it is set to visible.  It will be in the back.
        for i in range(self.nSli):
            ix = (self.focus+i+1)%self.nSli
            if self.slides[ix].slide_infos == True:
                text = "--- SLIDE INFOS ---\nSlide Number: " + str(ix) + "\nPosition: \n    x: " + str(self.slides[ix].x()) + " y: " + str(self.slides[ix].y()) + " z: " + str(self.slides[ix].z()) + "\nScale:\n    sx: " + str(self.slides[ix].sx) + " sy: " + str(self.slides[ix].sy) + " sz: " + str(self.slides[ix].sz) + "\nAngle:\n    ax: " + str(self.slides[ix].ax) + " ay: " + str(self.slides[ix].ay) + " az: " + str(self.slides[ix].az) + "\nOpacity: " + str(self.slides[ix].alpha()) + "\nVisibility: " + str(self.slides[ix].visible)
                arialFont = pi3d.Font("../attempts/pi3d_demos/fonts/FreeMonoBoldOblique.ttf",  (255,255,255,255), add_codepoints=[256], background_color=(0, 0, 0, 100))        
                infostring = pi3d.String(font=arialFont, string=text, justify="l")
                infostring.position(0, 0, 0.19)
                infostring.set_shader(self.parent.shader)
                infostring.scale(200, 200, 1.0)        
                self.slides[ix].mask.draw()
                infostring.draw()
                self.slides[ix].set_alpha(0.5)

            if self.slides[ix].visible == True:
                self.slides[ix].draw()
                if self.slides[ix].mask_on:
                    self.slides[ix].mask.draw()




            

class PytaVSL(object):
    def __init__(self, port=56418):
        # setup OSC
        self.port = port

        # setup OpenGL
        self.DISPLAY = pi3d.Display.create(background=(0.0, 0.0, 0.0, 1.0), frames_per_second=25)
        self.shader = pi3d.Shader("uv_flat")
        self.matsh = pi3d.Shader("mat_light")
        self.CAMERA = pi3d.Camera(is_3d=False)

        # Loading files in the queue
        self.iFiles = glob.glob("pix/*.*")
        self.nFi = len(self.iFiles)
        self.fileQ = queue.Queue()

        # Containers
        self.ctnr = Container(parent=self, nSli=8)


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
            self.fileQ.task_done()

    def destroy(self):
        self.DISPLAY.destroy()



    # OSC Methods
    @liblo.make_method('/pyta/slide/visible', 'ii')
    def slide_visible_cb(self, path, args):
        if args[0] < self.ctnr.nSli:
            if args[1]:
                self.ctnr.slides[args[0]].visible = True
            else:
                self.ctnr.slides[args[0]].visible = False     
        else:
            print("OSC ARGS ERROR: Slide number out of range")        

    @liblo.make_method('/pyta/slide/alpha', 'if')
    def slide_alpha_cb(self, path, args):
        if args[0] < self.ctnr.nSli:
            self.ctnr.slides[args[0]].set_alpha(args[1])
        else:
            print("OSC ARGS ERROR: Slide number out of range")

    @liblo.make_method('/pyta/slide/position', 'ifff')
    @liblo.make_method('/pyta/slide/position_x', 'if')
    @liblo.make_method('/pyta/slide/position_y', 'if')
    @liblo.make_method('/pyta/slide/position_z', 'if')
    def slide_position_cb(self, path, args):
        if args[0] < self.ctnr.nSli:
            if path == "/pyta/slide/position":
                self.ctnr.slides[args[0]].set_position(args[1], args[2], args[3])
            elif path == "/pyta/slide/position_x":
                self.ctnr.slides[args[0]].set_position(args[1], self.ctnr.slides[args[0]].y(), self.ctnr.slides[args[0]].z())
            elif path == "/pyta/slide/position_y":
                self.ctnr.slides[args[0]].set_position(self.ctnr.slides[args[0]].x(), args[1], self.ctnr.slides[args[0]].z())
            elif path == "/pyta/slide/position_z":
                self.ctnr.slides[args[0]].set_position(self.ctnr.slides[args[0]].x(), self.ctnr.slides[args[0]].y(), args[1])
        else:
            print("OSC ARGS ERROR: Slide number out of range")

    @liblo.make_method('/pyta/slide/translate', 'ifff')
    @liblo.make_method('/pyta/slide/translate_x', 'if')
    @liblo.make_method('/pyta/slide/translate_y', 'if')
    @liblo.make_method('/pyta/slide/translate_z', 'if')
    def slide_translate_cb(self, path, args):
        if args[0] < self.ctnr.nSli:
            if path == "/pyta/slide/translate":
                self.ctnr.slides[args[0]].set_translation(args[1], args[2], args[3])
            elif path == "/pyta/slide/translate_x":
                self.ctnr.slides[args[0]].set_translation(args[1], 0.0, 0.0)
            elif path == "/pyta/slide/translate_y":
                self.ctnr.slides[args[0]].set_translation(0.0, args[1], 0.0)
            elif path == "/pyta/slide/translate_z":
                self.ctnr.slides[args[0]].set_translation(0.0, 0.0, args[1])   
        else:
            print("OSC ARGS ERROR: Slide number out of range")

    @liblo.make_method('/pyta/slide/scale', 'ifff')
    @liblo.make_method('/pyta/slide/scale_x', 'if')
    @liblo.make_method('/pyta/slide/scale_y', 'if')
    @liblo.make_method('/pyta/slide/scale_z', 'if')
    def slide_scale_cb(self, path, args):
        if args[0] < self.ctnr.nSli:
            if path == "/pyta/slide/scale":
                self.ctnr.slides[args[0]].set_scale(args[1], args[2], args[3])
            elif path == "/pyta/slide/scale_x":
                self.ctnr.slides[args[0]].set_scale(args[1], self.ctnr.slides[args[0]].sy, self.ctnr.slides[args[0]].sz)
            elif path == "/pyta/slide/scale_y":
                self.ctnr.slides[args[0]].set_scale(self.ctnr.slides[args[0]].sx, args[1], self.ctnr.slides[args[0]].sz)
            elif path == "/pyta/slide/scale_z":
                self.ctnr.slides[args[0]].set_scale(self.ctnr.slides[args[0]].sx, self.ctnr.slides[args[0]].sy, args[1])
        else:
            print("OSC ARGS ERROR: Slide number out of range")

    @liblo.make_method('/pyta/slide/rotate', 'ifff')
    @liblo.make_method('/pyta/slide/rotate_x', 'if')
    @liblo.make_method('/pyta/slide/rotate_y', 'if')
    @liblo.make_method('/pyta/slide/rotate_z', 'if')
    def slide_rotate_cb(self, path, args):
        if args[0] < self.ctnr.nSli:
            if path == "/pyta/slide/rotate":
                self.ctnr.slides[args[0]].set_angle(args[1], args[2], args[3])
            elif path == "/pyta/slide/rotate_x":
                self.ctnr.slides[args[0]].set_angle(args[1], self.ctnr.slides[args[0]].ay, self.ctnr.slides[args[0]].az)
            elif path == "/pyta/slide/rotate_y":
                self.ctnr.slides[args[0]].set_angle(self.ctnr.slides[args[0]].ax, args[1], self.ctnr.slides[args[0]].az)
            elif path == "/pyta/slide/rotate_z":
                self.ctnr.slides[args[0]].set_angle(self.ctnr.slides[args[0]].ax, self.ctnr.slides[args[0]].ay, args[1])
        else:
            print("OSC ARGS ERROR: Slide number out of range")


    @liblo.make_method('/pyta/slide/load_file', 'is')
    def slide_load_file_cb(self, path, args):
        if self.ctnr.slides[args[0]].visible:
            print("WARNING: you're loading a file in a potentially visible slide - loading takes a bit of time, the effect might not render immediately")
        fexist = False
        for i in range(self.nFi):
            if args[1] == self.iFiles[i]:
                item = [self.iFiles[i], self.ctnr.slides[args[0]]]
                self.fileQ.put(item)
                print("loading file " + args[1])
                fexist = True
        if fexist == False:
            print(args[1] + ": no such file in the current list - please consider adding it with /pyta/add_file ,s [path to the file]")

    @liblo.make_method('/pyta/slide/slide_info', 'ii')
    def slide_info_cb(self, path, args):
        if args[1]:
            self.ctnr.slide_info(args[0])
        else:
            self.ctnr.slide_info(-1)


                
    @liblo.make_method('/pyta/add_file', 's')
    def add_file_cb(self, path, args):
        if os.path.exists(args[0]):
            self.iFiles.extend(glob.glob(args[0]))
            self.nFi = len(self.iFiles)
            print("file " + args[0] + " added to the list:")
            for i in range(self.nFi):
                print("  + " + self.iFiles[i])
        else:
            print("ERREUR: " + args[0] + ": no such file or directory")




########## MAIN APP ##########

pyta = PytaVSL()
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
            pyta.DISPLAY.stop()
            break
        #         if k == 115: #S
        #             ctnr.posit()
        #         else:
        #             ctnr.join()

pyta.destroy()

