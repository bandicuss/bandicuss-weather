# Adapted from theNeighborrr/bandicuss-weather-intros, revision c1640f3.
# Copyright (c) 2026 theNeighborrr. MIT license; see LICENSE-intros.
"""Pixel startup animation for Bandicuss Weather v4.1.

The application calls play_intro() before station selection. The animation
performs no weather acquisition; Horizon Observatory handles the live request
status display afterward. Pixel drawing primitives also support that display.

The optional intro needs an interactive terminal of at least 79 columns by
24 rows. Press any key to continue; Ctrl-C exits. NO_COLOR or a nonempty
BANDICUSS_NO_ANIMATION disables it, and redirected or smaller terminals skip it.
Horizon Observatory supports 97x23 independently of the startup intro.
Running this module directly plays only the startup animation.
"""
import math
import os
import shutil
import sys
import time

WIDTH, HEIGHT, FPS, DURATION = 78, 40, 16, 8.0
SCENES = ("FIRST LIGHT", "STORM FRONT", "SNOWFALL", "AFTER DARK")
PALETTE = []


def color(hex_value):
    rgb = tuple(bytes.fromhex(hex_value.lstrip("#")))
    if rgb not in PALETTE:
        PALETTE.append(rgb)
    return PALETTE.index(rgb)


def ramp(a, b, count=16):
    a, b = bytes.fromhex(a), bytes.fromhex(b)
    return [color(bytes(round(x + (y-x)*i/(count-1)) for x,y in zip(a,b)).hex()) for i in range(count)]


SKIES = [ramp("161839", "e98468"), ramp("101c34", "53677c"),
         ramp("243b60", "94b5c6"), ramp("050d23", "174954")]
DAWN = [color(c) for c in ("ffd8a0", "ffae69", "ffa486", "bf7089", "725c86", "434269", "242d4f", "333654", "805878", "bc7485")]
STORM = [color(c) for c in ("222d46", "2d3e55", "3b4e68", "aecbdf", "6893b1", "35495b", "152434", "ffc574", "e7effb", "899ec0")]
SNOW = [color(c) for c in ("7396b7", "bed5df", "e4edf0", "587995", "294961", "193447", "405c6e", "f3d1a0", "8cb5c6", "6b8d9e")]
NIGHT = [color(c) for c in ("2c6e78", "379e93", "68c7a6", "879ab4", "48537a", "192d43", "0a192c", "9dcad1", "e3f0e1", "204559")]
INK = color("0b1528")
TITLE = ramp("e5f8ef", "79ced2", 7)
FONT = {
    'B': ["11110","10001","10001","11110","10001","10001","11110"],
    'A': ["01110","10001","10001","11111","10001","10001","10001"],
    'N': ["10001","11001","11001","10101","10011","10011","10001"],
    'D': ["11110","10001","10001","10001","10001","10001","11110"],
    'I': ["11111","00100","00100","00100","00100","00100","11111"],
    'C': ["01111","10000","10000","10000","10000","10000","01111"],
    'U': ["10001","10001","10001","10001","10001","10001","01110"],
    'S': ["01111","10000","10000","01110","00001","00001","11110"],
}


class Canvas:
    def __init__(self, scene):
        self.pixels = bytearray(v for y in range(HEIGHT) for v in [SKIES[scene][min(15,int(y*16/29))]]*WIDTH)

    def dot(self, x, y, c):
        x,y = round(x),round(y)
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            self.pixels[y*WIDTH+x]=c

    def rect(self, x, y, w, h, c):
        for yy in range(round(y),round(y+h)):
            for xx in range(round(x),round(x+w)):
                self.dot(xx,yy,c)

    def ellipse(self,x,y,rx,ry,c):
        for yy in range(max(0,math.floor(y-ry)),min(HEIGHT,math.ceil(y+ry)+1)):
            for xx in range(max(0,math.floor(x-rx)),min(WIDTH,math.ceil(x+rx)+1)):
                if ((xx-x)/rx)**2+((yy-y)/ry)**2<=1:
                    self.dot(xx,yy,c)

    def ridge(self,points,c):
        for (x1,y1),(x2,y2) in zip(points,points[1:]):
            for x in range(x1,x2):
                top=round(y1+(y2-y1)*(x-x1)/(x2-x1))
                self.rect(x,top,1,HEIGHT-top,c)

    def tree(self,x,y,scale,c):
        for dy in range(scale*3):
            half=dy//3
            self.rect(x-half,y+dy,half*2+1,1,c)
        self.rect(x,y+scale*3,1,2,c)

    def cloud(self,x,y,s,c,shade):
        self.ellipse(x,y,7*s,2*s,shade)
        self.ellipse(x-3*s,y-1*s,3*s,2*s,c)
        self.ellipse(x+1*s,y-2*s,4*s,3*s,c)
        self.ellipse(x+5*s,y-0.4*s,3*s,2*s,c)


def scene_frame(scene, t):
    """A deterministic 78x40 palette-index frame. t is local scene seconds."""
    c=Canvas(scene)
    if scene==0:
        c.ellipse(52,17-t*1.6,9,9,DAWN[1]);c.ellipse(52,17-t*1.6,7,7,DAWN[0])
        c.cloud(13+t*2,8,.9,DAWN[2],DAWN[3]);c.cloud(66+t,5,.65,DAWN[2],DAWN[3])
        c.ridge([(0,24),(10,19),(18,22),(29,14),(40,23),(47,20),(57,24),(66,16),(78,23)],DAWN[4])
        c.ridge([(0,29),(13,23),(22,27),(36,23),(48,29),(65,24),(78,27)],DAWN[5])
        c.rect(0,29,78,11,DAWN[6])
        for y in range(29,40):
            center=51+math.sin(y*1.1+t*2)*3;spread=(y-26)*.8
            for x in range(round(center-spread),round(center+spread)):
                if (x+int(t*7)+y*3)%7<4:c.dot(x,y,DAWN[8+(y%2)])
        for x,y in [(3,25),(7,27),(73,26),(69,29)]:c.tree(x,y,2,INK)
        for x,y in [(32+t*3,9),(37+t*3,7)]:
            c.dot(x-1,y,INK);c.dot(x,y+1,INK);c.dot(x+1,y,INK)
    elif scene==1:
        for y in range(3):
            for x in range(-12,93,20):c.cloud(x+t*2.2-y*7,4+y*4,1.7,STORM[y%2],STORM[2])
        # One localized bolt per scene; no full-screen flashing.
        if .85<t<1.1:
            for x,y in [(51,10),(50,11),(49,12),(48,13),(50,13),(49,14),(48,15),(47,16),(46,17)]:
                c.dot(x,y,STORM[8]);c.dot(x+1,y,STORM[9])
        for i in range(38):
            x=(i*19-int(t*19))%82-2;y=(i*11+int(t*24))%34
            c.dot(x,y,STORM[4]);c.dot(x-1,y+1,STORM[3])
        for i in range(16):
            x=i*5;top=23-(i*7%10)
            c.rect(x,top,4,34-top,STORM[6])
            for yy in range(top+2,32,3):
                if (i+yy)%3:c.dot(x+1,yy,STORM[7])
        c.rect(0,33,78,7,INK)
        for i in range(16):
            y=34+i%5;x=(i*13+int(t*9))%78
            c.rect(x,y,3+i%3,1,STORM[4] if i%2 else STORM[7])
    elif scene==2:
        c.ellipse(62,7,4,4,SNOW[1])
        c.ridge([(0,27),(10,16),(18,22),(30,6),(40,19),(49,12),(62,27),(72,18),(78,24)],SNOW[0])
        c.ridge([(0,34),(13,25),(21,32),(37,15),(49,28),(60,20),(78,35)],SNOW[3])
        # Snow caps on the principal peaks.
        for x,y,w in [(30,6,7),(49,12,4),(37,15,6)]:
            for dy in range(5):
                for dx in range(-dy,dy+1):
                    if dy<3 or (dx+dy)%3:c.dot(x+dx,y+dy,SNOW[2])
        c.ridge([(0,36),(17,33),(33,35),(51,31),(67,33),(78,31)],SNOW[1])
        for x,y,s in [(6,23,3),(15,27,2),(67,21,3),(73,25,3),(58,28,2)]:
            c.tree(x,y,s,SNOW[4]);c.dot(x,y,SNOW[2])
        c.rect(45,28,9,6,SNOW[5]);c.ridge([(44,29),(49,25),(55,29)],SNOW[5])
        # Cabin roof helper above fills down; restore the foreground snow.
        c.rect(44,34,12,6,SNOW[1]);c.rect(47,29,2,2,SNOW[7]);c.rect(51,29,1,2,SNOW[7])
        for i in range(54):
            x=(i*23+math.sin(t*1.4+i)*2+t*2)%78;y=(i*13+t*(3+i%4))%40
            c.dot(x,y,SNOW[2] if i%3 else SNOW[8])
    else:
        for i in range(60):
            x=(i*31+7)%78;y=(i*17+3)%25
            c.dot(x,y,NIGHT[8] if math.sin(t*2+i)>0.5 else NIGHT[7])
        for x in range(78):
            y=10+math.sin(x*.1+t*.6)*4+math.sin(x*.22-t)*2
            for dy in range(7):
                c.dot(x,y+dy,NIGHT[0 if dy<2 else 1 if dy<4 else 2 if dy==4 else 0])
        c.ellipse(63,7,3,3,NIGHT[8]);c.ellipse(64,6,3,3,SKIES[3][3])
        c.ridge([(0,31),(12,24),(24,29),(34,21),(46,29),(59,24),(69,28),(78,23)],NIGHT[5])
        c.ridge([(0,36),(14,31),(23,34),(39,30),(52,35),(67,31),(78,33)],NIGHT[6])
        for x,y in [(3,23),(9,29),(71,24),(76,26)]:c.tree(x,y,3,INK)
    # Persistent title with a one-pixel dark silhouette, readable in every scene.
    x0=(WIDTH-(len('BANDICUSS')*6-1))//2;y0=28
    points=[(x0+i*6+x,y0+y,y) for i,letter in enumerate('BANDICUSS') for y,row in enumerate(FONT[letter]) for x,b in enumerate(row) if b=='1']
    for x,y,_ in points:
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1),(1,1)]:c.dot(x+dx,y+dy,INK)
    for x,y,row in points:c.dot(x,y,TITLE[row])
    return bytes(c.pixels)


def frame_at(seconds):
    seconds=max(0,min(DURATION-1/FPS,seconds))
    scene=min(3,int(seconds/2))
    return scene_frame(scene,seconds-scene*2),scene


def ansi_frame(pixels,scene,columns=80,rows=24):
    """Scale original pixels to fit, keeping captions at the terminal font size."""
    from bandicuss_intro_layout import fit_canvas,resample,position,caption
    left,top,width,height=fit_canvas(columns,rows,WIDTH,HEIGHT,captions=4,pixel=True)
    art=resample(pixels,WIDTH,HEIGHT,width,height)
    chunks=[caption('B A N D I C U S S   /   W E A T H E R',columns,top)]
    for y in range(0,height,2):
        chunks.append(position(left,top+1+y//2));last=None
        for x in range(width):
            pair=(art[y*width+x],art[(y+1)*width+x])
            if pair!=last:
                a,b=(PALETTE[i] for i in pair)
                chunks.append('\x1b[38;2;%d;%d;%d;48;2;%d;%d;%dm'%(*a,*b));last=pair
            chunks.append('▀')
        chunks.append('\x1b[0m\x1b[K')
    bottom=top+1+height//2
    chunks.append(caption('W E A T H E R   C E N T E R',columns,bottom,(167,213,215)))
    chunks.append(caption(SCENES[scene]+'   /   '+str(scene+1)+' OF 4',columns,bottom+1))
    chunks.append(caption('ANY KEY TO CONTINUE',columns,bottom+2))
    return ''.join(chunks)


def play_intro(duration=DURATION):
    """Play once, skippable. Always restore input mode, cursor and screen.

    Requires an interactive terminal of at least 79x24. Any key continues;
    Ctrl-C exits. Smaller terminals, redirected output, NO_COLOR (even empty),
    or a nonempty BANDICUSS_NO_ANIMATION skip it. This function does not fetch
    data or control the subsequent Horizon Observatory acquisition screen.
    """
    if not sys.stdout.isatty() or not sys.stdin.isatty():return
    if os.environ.get('NO_COLOR') is not None or os.environ.get('BANDICUSS_NO_ANIMATION'):return
    cols,rows=shutil.get_terminal_size()
    if cols<WIDTH+1 or rows<24:return
    duration=max(.5,min(15,float(duration)))
    import select
    import termios
    import tty
    fd=sys.stdin.fileno();previous=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[2J');sys.stdout.flush()
        start=time.monotonic();last_size=None
        while True:
            frame_started=time.monotonic()
            elapsed=frame_started-start
            if elapsed>=duration:break
            cols,rows=shutil.get_terminal_size()
            if cols<WIDTH+1 or rows<24:break
            if (cols,rows)!=last_size:
                sys.stdout.write('\x1b[2J');last_size=(cols,rows)
            pixels,scene=frame_at(elapsed/duration*DURATION)
            sys.stdout.write(ansi_frame(pixels,scene,cols,rows));sys.stdout.flush()
            wait=max(0,1/FPS-(time.monotonic()-frame_started))
            if select.select([sys.stdin],[],[],wait)[0]:
                os.read(fd,1);termios.tcflush(fd,termios.TCIFLUSH);break
    finally:
        try:
            termios.tcsetattr(fd,termios.TCSADRAIN,previous)
        finally:
            sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l');sys.stdout.flush()


if __name__=='__main__':
    play_intro()
