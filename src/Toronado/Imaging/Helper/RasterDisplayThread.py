# -*- coding: utf-8 -*-
# this is RasterDisplayThread.py  revised 28 Dec 2017 BWS

import os.path as path
import sys
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import Imaging.Helper.processImageData as PI
import Imaging.Helper.ImageDisplay.ImageWin_v1 as IM

class clsRasterDisplayThread(QtCore.QThread):
    # This class allows the image display windows work in separate thread from the main GUI
    def __init__(self, callingInstance, useNativeGUI):
        QtCore.QThread.__init__(self)
        self.useNativeGUI = useNativeGUI
        self.imageWindows = [IM.clsImageWin(self, 1, self.useNativeGUI)]
        self.callingInstance = callingInstance
        self.lastImageWindowNum = 1
        self.newDisplayItem = None
        self.guiLockOut = False
        self.minorParmsDirty = True
        self.lastMajorParms = None
        self.curMode = "idle"
        self.focusMode = False
        self.lastStartTime = None
        self.lastNumFrames = 1
        self.iTimer = QtCore.QTimer()
        self.iTimer.setSingleShot(True)
        self.iTimer.timeout.connect(self.displayNewItem)

    def run(self): # needs to be include to prevent error at closing
        pass

    def exportCursorPos(self, cursorXvolts, cursorYvolts, spotName, testMode):
        # intermediate function to pass information on to top level (toronado)
        self.callingInstance.passCurrentCursorPos(cursorXvolts, cursorYvolts, spotName, testMode)

    def addNewImageWindow(self):
        self.lastImageWindowNum += 1
        self.imageWindows.append(IM.clsImageWin(self, self.lastImageWindowNum, self.useNativeGUI))

    def requestNewDisplayItem(self, newItem):
        self.newDisplayItem = newItem
        self.iTimer.start(0)

    def closeImageWindows(self):
        for oneWindow in self.imageWindows:
            oneWindow.closeThisWindow()

    def displayNewItem(self):
        if self.newDisplayItem:
            for oneWindow in self.imageWindows:
                oneWindow.loadImageFile(self.newDisplayItem)
                #oneWindow.loadImageFromDict(self.newDisplayItem)
            self.newDisplayItem = None
