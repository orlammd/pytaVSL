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
import os

from six.moves import queue

LOGGER = pi3d.Log.logger(__name__)
LOGGER.info("Log using this expression.")


class Slide(pi3d.Sprite):
    def __init__(self):
        super(Slide, self).__init__(w=1.0, h=1.0)
        self.visible = False
        self.creation = True

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

    def animate(self, start, end, duration, step, function):

        def threaded():
            nb_step = int(round(duration/step))
            a = float(end-start)/nb_step

            if function == 'position_x': #PositionX
                for i in range(nb_step+1):
                    val = a*i+start
                    self.set_position(val, self.y(), self.z())
                    time.sleep(step)

        t = threading.Thread(target=threaded)
        t.start()


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
        self.items = {}
        for i in range(self.nSli):
            # Textured Slides
            self.slides[i] = Slide()

            self.slides[i].positionZ(0.8-(i/20))
            self.items[i] = [self.parent.iFiles[i%self.parent.nFi], self.slides[i]]
            self.parent.fileQ.put(self.items[i])


            # Mask Slides
            self.slides[i].mask.set_shader(self.parent.matsh)
            self.slides[i].mask.set_material((1.0, 0.0, 0.0))
            self.slides[i].mask.positionZ(0.81-(i/10))

        self.focus = 0 # holds the index of the focused image
#        self.slides[self.focus].visible = True

    def draw(self):
        # slides have to be drawn back to front for transparency to work.
        # the 'focused' slide by definition at z=0.1, with deeper z
        # trailing to the left.  So start by drawing the one to the right
        # of 'focused', if it is set to visible.  It will be in the back.
        for i in range(self.nSli):
            ix = (self.focus+i+1)%self.nSli
            if self.slides[ix].visible == True:
                if self.slides[ix].mask_on:
                    self.slides[ix].mask.draw()
                self.slides[ix].draw()





            

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
        self.ctnr = Container(parent=self, nSli=16)



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
            if slide.creation:
                xrat = self.DISPLAY.width/tex.ix
                yrat = self.DISPLAY.height/tex.iy
                if yrat < xrat:
                    xrat = yrat
                wi, hi = tex.ix * xrat, tex.iy * xrat
                slide.set_scale(wi, hi, 1.0) 

            slide.set_draw_details(self.shader,[tex])
            self.fileQ.task_done()
            slide.creation = False

    def destroy(self):
        self.DISPLAY.destroy()



    # OSC Methods
    @liblo.make_method('/pyta/slide/visible', 'ii')
    def slide_visible_cb(self, path, args):
        print(args[0])
        if args[0] < self.ctnr.nSli:
            if args[1]:
                self.ctnr.slides[args[0]].visible = True
            else:
                self.ctnr.slides[args[0]].visible = False     
        else:
            print("OSC ARGS ERROR: Slide number out of range")        

    @liblo.make_method('/pyta/slide/mask_on', 'ii')
    def slide_mask_on_cb(self, path, args):
        if args[0] < self.ctnr.nSli:
            if args[1]:
                slide = self.ctnr.slides[args[0]]
                slide.mask.position(slide.x(), slide.y(), slide.z()+0.1)
                slide.mask.scale(slide.sx, slide.sy, slide.sz)
                slide.mask.rotateToX(slide.ax)
                slide.mask.rotateToY(slide.ay)
                slide.mask.rotateToZ(slide.az)
                slide.mask_on = True
            else:
                self.ctnr.slides[args[0]].mask_on = False     
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
    @liblo.make_method('/pyta/slide/relative_scale_xy', 'if')
    @liblo.make_method('/pyta/slide/rsxy', 'if')
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
            elif path == "/pyta/slide/relative_scale_xy" or path == "/pyta/slide/rsxy":
                self.ctnr.slides[args[0]].set_scale(self.ctnr.slides[args[0]].sx*args[1], self.ctnr.slides[args[0]].sy*args[1], self.ctnr.slides[args[0]].sz)

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

    @liblo.make_method('/pyta/slide/animate', 'iiiffs') # slide, start, end, duration, step, function
    def slide_animate(self, path, args):
        self.ctnr.slides[args[0]].animate(*args[1:])


    @liblo.make_method('/pyta/slide/load_file', 'iss')
    @liblo.make_method('/pyta/slide/load_file', 'is')
    def slide_load_file_cb(self, path, args):
        if len(args) == 3: # Auto-scaling disabled
            self.ctnr.slides[args[0]].creation = False
        else:
            self.ctnr.slides[args[0]].creation = True
        if self.ctnr.slides[args[0]].visible:
            print("WARNING: you're loading a file in a potentially visible slide - loading takes a bit of time, the effect might not render immediately")
        fexist = False
        for i in range(self.nFi):
            if args[1] == str(self.iFiles[i]):
                self.ctnr.items[args[0]] = [self.iFiles[i%self.nFi], self.ctnr.slides[args[0]]]
                self.fileQ.put(self.ctnr.items[args[0]])
                print("loading file " + args[1] + " in slide " + str(args[0]))
                fexist = True
        if fexist == False:
            print(args[1] + ": no such file in the current list - please consider adding it with /pyta/add_file ,s [path to the file]")
            print("Current list of files:")
            print(self.iFiles)

    @liblo.make_method('/pyta/slide/slide_info', 'ii')
    def slide_info_cb(self, path, args, types, src):
	slide = self.ctnr.slides[args[0]]
	dest = src.get_url().split(":")[0] + ':' + src.get_url().split(":")[1] + ':' + str(args[1])
	prefix = '/pyta/slide_info/'
        liblo.send(dest, prefix + 'slidenumber', args[0])
        liblo.send(dest, prefix + 'position', slide.x(), slide.y(), slide.z())
        liblo.send(dest, prefix + 'scale', slide.sx, slide.sy, slide.sz)
        liblo.send(dest, prefix + 'angle', slide.ax, slide.ay, slide.az)
        liblo.send(dest, prefix + 'visible', slide.visible)
        liblo.send(dest, prefix + 'alpha', slide.alpha())
    
    @liblo.make_method('/pyta/slide/save_state', 'is')
    def slide_save_state(self, path, args):
	slide = self.ctnr.slides[args[0]]
	prefix = '/pyta/slide/'
        filename = 's' + str(args[0]) + '.' + args[1] + '.state'
	print('Write in progress in ' + filename)
 
        statef = open(filename, 'w')
        statef.write("slide " + str(args[0]) + "\n") 
        statef.write("file " + str(self.ctnr.items[args[0]][0]) + "\n") 
        statef.write("position " + str(slide.x()) + " " + str(slide.y()) + " " + str(slide.z()) + "\n")
        statef.write("scale " + str(slide.sx) + " " + str(slide.sy) + " " + str(slide.sy) + "\n")  
        statef.write("angle " + str(slide.ax) + " " + str(slide.ay) + " " + str(slide.az) + "\n") 
        statef.write("alpha " + str(slide.alpha()) + "\n") 
        statef.close()

    @liblo.make_method('/pyta/slide/load_state', 's')
    def slide_load_state(self, path, args):
        statef = open(args[0], 'r')
        param = statef.read()
        sn = int(param.split("\n")[0].split(" ")[1])
        fn = param.split("\n")[1].split(" ")[1]
        pos = param.split("\n")[2].split(" ")[1:]
        sc = param.split("\n")[3].split(" ")[1:]
        ag = param.split("\n")[4].split(" ")[1:]
        al = float(param.split("\n")[5].split(" ")[1])

#        print(str(sn) + " " + str(fn) + " " + str(pos) + " " + str(sc) + " " + str(ag) + " " + str(al))

        slide = self.ctnr.slides[sn]
        self.slide_load_file_cb('/hop', (sn, fn, "NoCreation"))
        slide.position(float(pos[0]), float(pos[1]), float(pos[2]))
        slide.set_scale(float(sc[0]), float(sc[1]), float(sc[2]))
        slide.set_angle(float(ag[0]), float(ag[1]), float(ag[2]))
        slide.set_alpha(al)


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
        #             ctnr.posit()
        #         else:
        #             ctnr.join()

pyta.destroy()

