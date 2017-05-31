#!/usr/bin/env python

import os
import sys

import socket

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import datetime
import time
from papirus import Papirus

import RPi.GPIO as GPIO

# Assume Papirus Zero
SW1 = 21

# Check EPD_SIZE is defined
EPD_SIZE=0.0
if os.path.exists('/etc/default/epd-fuse'):
    execfile('/etc/default/epd-fuse')
if EPD_SIZE == 0.0:
    print("Please select your screen size by running 'papirus-config'.")
    sys.exit()

# Running as root only needed for older Raspbians without /dev/gpiomem
if not (os.path.exists('/dev/gpiomem') and os.access('/dev/gpiomem', os.R_OK | os.W_OK)):
    user = os.getuid()
    if user != 0:
        print("Please run script as root")
        sys.exit()

WHITE = 1
BLACK = 0

# fonts are in different places on Raspbian/Angstrom so search
possible_fonts = [
    '/usr/share/fonts/truetype/ttf-dejavu/DejaVuSansMono-Bold.ttf',   # R.Pi
    '/usr/share/fonts/truetype/freefont/FreeMono.ttf',                # R.Pi
    '/usr/share/fonts/truetype/LiberationMono-Bold.ttf',              # B.B
    '/usr/share/fonts/truetype/DejaVuSansMono-Bold.ttf',              # B.B
    '/usr/share/fonts/TTF/FreeMonoBold.ttf',                          # Arch
    '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf'                        # Arch
]


FONT_FILE = ''
for f in possible_fonts:
    if os.path.exists(f):
        FONT_FILE = f
        break

if '' == FONT_FILE:
    raise 'no font file found'

CLOCK_FONT_SIZE = 16

MAX_START = 0xffff

def main(argv):
    """main program - draw and display a test image"""

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SW1, GPIO.IN)

    papirus = Papirus()

    print('panel = {p:s} {w:d} x {h:d}  version={v:s} COG={g:d} FILM={f:d}'.format(p=papirus.panel, w=papirus.width, h=papirus.height, v=papirus.version, g=papirus.cog, f=papirus.film))

    papirus.clear()

    demo(papirus)


def demo(papirus):
    """simple partial update demo - draw draw a clock"""

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(10)
    try:
        s.connect(("8.8.8.8", 80))
        ip=s.getsockname()[0]
        print ip
        socketok = 1
    except socket.error, e:
        print 'IP Address Error.'
        socketok = 0

    # initially set all white background
    image = Image.new('1', papirus.size, WHITE)

    # prepare for drawing
    draw = ImageDraw.Draw(image)
    width, height = image.size

    clock_font = ImageFont.truetype(FONT_FILE, CLOCK_FONT_SIZE)

    # clear the display buffer
    draw.rectangle((0, 0, width, height), fill=WHITE, outline=WHITE)
    previous_second = 0

    eee = 0
    while True:
        while True:
            now = datetime.datetime.today()
            if now.second != previous_second:
                break
            time.sleep(0.1)

        if GPIO.input(SW1) == False:
            eee = 1
            time.sleep(0.2)

        draw.rectangle((2, 2, width - 2, height - 2), fill=WHITE, outline=BLACK)
        if socketok == 1:
            draw.text((5, 10), ip, fill=BLACK, font=clock_font)
        else:
            draw.text((5, 10), 'Network Error !', fill=BLACK, font=clock_font)
        
        draw.text((5, 30), '{y:04d}-{m:02d}-{d:02d} {h:02d}:{f:02d}:{s:02d}'.format(y=now.year, m=now.month, d=now.day, h=now.hour, f=now.minute, s=now.second), fill=BLACK, font=clock_font)
        
        if eee == 0:
            draw.text((5, 50), 'SW1 : Shut Down', fill=BLACK, font=clock_font)
        else:
            draw.text((5, 50), 'System Shut Down...', fill=BLACK, font=clock_font)

        # display image on the panel
        papirus.display(image)
        if now.second < previous_second:
            papirus.update()    # full update every minute
        else:
            papirus.partial_update()
        previous_second = now.second

        if eee == 1:
            os.system("sudo shutdown -h now")
            sys.exit()
            eee = 2

# main
if "__main__" == __name__:
    if len(sys.argv) < 1:
        sys.exit('usage: {p:s}'.format(p=sys.argv[0]))

    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit('interrupted')
        pass
