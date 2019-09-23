# -*- coding: utf-8 -*-
""" samplePostProcessing.py

This is an example of a special processing routine following acquiring image data

last revised 1 Apr 2017 BWS

"""

import sys, os, math
import os.path as path
import numpy as np

def special1(newImageFN):
    print("Here inside special1: " + newImageFN)
