#!/usr/bin/env python

import os
import time
import sys
import signal
import numpy
import colorsys
from colorsys import hsv_to_rgb

# PIMORONI BREAKOUT GARDEN
import VL53L1X
from mote import Mote
from luma.core.interface.serial import i2c
from luma.core.error import DeviceNotFoundError
from luma.oled.device import sh1106

print("""
Press Ctrl+C to exit.
""")

# CONFIG
MIN_ON = 64
MAX_ON = 140
TOGGLE_GAMING = 10
RANGE_COP = 20
MAX_TIME_SHUTDOWN = 5

# VAR
running = True
gaming_enabled = False
time_sleep = 1
red_coplight = False
active_desk = False
tic = 0
toc = 0

# VL53L1X
tof = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=0x29)
tof.open()
tof.start_ranging(3) # Start ranging, 1 = Short Range, 2 = Medium Range, 3 = Long Range

# MOTE
mote = Mote()
mote.configure_channel(1, 16, False)
mote.configure_channel(2, 16, False)
mote.configure_channel(3, 16, False)
mote.configure_channel(4, 16, False)
mote.set_brightness(1)

# OLED
try:
    oled = sh1106(i2c(port=1, address=0x3C), rotate=2, height=128, width=128)
except DeviceNotFoundError:
    print('Did not find 1.12" OLED on 0x3d, trying 0x3d...')
    oled = sh1106(i2c(port=1, address=0x3D), rotate=2, height=128, width=128)

# FUNCTIONS
def exit_handler(signal, frame):
    global running
    running = False
    tof.stop_ranging() # Stop ranging
    mote.clear()
    mote.show()
    print()
    sys.exit(0)

def gaming_mode(mote):
    h = time.time() * 15
    for channel in range(4):
        for pixel in range(16):
            hue = (h + (channel * 64) + (pixel * 4)) % 360
            r, g, b = [int(c * 255) for c in hsv_to_rgb(hue/360.0, 1.0, 1.0)]
            mote.set_pixel(channel + 1, pixel, r, g, b)
    mote.show()

def make_gaussian(fwhm):
    x = numpy.arange(0, 16, 1, float)
    y = x[:, numpy.newaxis]
    x0, y0 = 3.5, 7.5
    fwhm = fwhm
    gauss = numpy.exp(-4 * numpy.log(2) * ((x - x0) ** 2 + (y - y0) ** 2) / fwhm ** 2)
    return gauss

signal.signal(signal.SIGINT, exit_handler)


while running:
    distance_in_cm = tof.get_distance() / 10 # mm to cm

    # TIMER
    tic = time.perf_counter()
    if distance_in_cm < MAX_ON:
        toc = time.perf_counter()
    if tic - toc > MAX_TIME_SHUTDOWN:
        active_desk = False
    else:
        active_desk = True
    
    # DEBUG
    print(f"Inactive time: {tic - toc:0.4f} seconds")
    print("Active desk: {}".format(active_desk))
    print("Distance: {}cm".format(distance_in_cm))
    
    # TOGGLE GAMING ON/OFF
    if distance_in_cm < TOGGLE_GAMING: # gaming mode
        if not gaming_enabled:
            print("GAMING TOGGLE ON")
            gaming_mode(mote) 
            time_sleep = 0.1
        else:
            print("GAMING TOGGLE OFF")
            mote.clear()
            mote.show()
            time_sleep = 1
        time.sleep(1)
        gaming_enabled = not gaming_enabled

    ## POSTURE MODE
    # elif distance_in_cm < MIN_ON and distance_in_cm > MIN_ON - RANGE_COP and not gaming_enabled: # too close
    #     print("POSTURE MODE")
        # red_coplight = not red_coplight
        # for z in list(range(1, 10)[::-1]) + list(range(1, 10)):
        #     fwhm = 7.0/z
        #     gauss = make_gaussian(fwhm)
        #     start = time.time()
        #     y = 4
        #     for x in range(16):
        #         h = 0 if red_coplight else 0.5
        #         s = 1.0
        #         v = gauss[x, y]
        #         rgb = colorsys.hsv_to_rgb(h, s, v)
        #         r, g, b = [int(255.0 * i) for i in rgb]
        #         mote.set_pixel(1, x, r, g, b)
        #         mote.set_pixel(2, x, r, g, b)
        #         mote.set_pixel(3, x, r, g, b)
        #         mote.set_pixel(4, x, r, g, b)
        #     mote.show()
        # mote.show()
        # time_sleep = 0.05
    
    # GAMING ON
    elif gaming_enabled == True and active_desk:
        print("GAMING MODE")
        gaming_mode(mote)
        time_sleep = 0.1
    
    # NORMAL LAMP
    elif (distance_in_cm < MAX_ON and not gaming_enabled) or active_desk: # on the desk
        print("NORMAL LAMP")
        mote.set_all(255, 141, 41)
        mote.show()
        time_sleep = 1

    # GAMING OFF
    elif (gaming_enabled and not active_desk) or not gaming_enabled:
        mote.clear()
        mote.show()
    time.sleep(time_sleep)

