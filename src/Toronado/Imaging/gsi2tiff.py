# -*- coding: utf-8 -*-
""" gsi2tiff.py

This is a utility function that converts the Toronado output Zip file (typically with a .gsi extension)
into a TIFF file that can be viewed by standard image processing programs. The routine also prints
diag information to the terminal about the image shape and mean pixel value.

last revised 17 Dec 2017 BWS

"""

import sys, os, math
import socket
import zipfile
import numpy as np
import os.path as path
import datetime
import time
import importlib
import configparser as ConfigParser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import Helper.processImageData as PI

def convertFile(zipFileName):
    if not path.exists(zipFileName):
        print("  Cannot find requested .gsi file: " + zipFileName)
        return None

    # uncompress and read Zip file contents into a Dict
    tempDict = PI.loadRasterZipFile(zipFileName, lagPixelsAdjust=0, fastMode=False)
    infoStr = "  Image data: " + str(tempDict["Xsize"]) + " by " + str(tempDict["Ysize"]) + " pixels"
    infoStr += " by " + str(tempDict["numFrames"])
    numChannels = len(tempDict["channelLetters"])
    if numChannels == 1:
        infoStr += " frames (1 channel, " + tempDict["channelLetters"][0] + ")"
    else:
        infoStr += " frames (" + str(numChannels) + " channels)"
    print(infoStr)

    # save image data Dict as TIFF file
    retName = PI.saveProcessedImageData(tempDict, zipFileName, "tif", -1) # last -1 means save whole movie
    return retName

if __name__ == "__main__":
    if len(sys.argv) == 2:
        convertFile(sys.argv[1])
    else:
        print("You need to supply a path + file name to gsi2tiff.py")

