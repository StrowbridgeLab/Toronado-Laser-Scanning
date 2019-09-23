#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Main window.

This is toronado.py -- the core GUIs for viewing image files and controlling scans

last revised 30 Dec 2017 BWS

"""

from pyqtgraph.Qt import QtGui, QtCore
import sys, os, time, traceback, shutil
import os.path as path
import socket
import configparser as ConfigParser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Imaging.Helper.EasyDict import EasyDict
import Imaging.RasterGUI as RGUI
import Imaging.Helper.RasterDisplayThread as RDT

class clsMainWindow(QtGui.QMainWindow):

    def __init__(self, iniFN):
        super(clsMainWindow, self).__init__()
        self.coreParms = self.processINIfile(iniFN)
        self.coreParms["Raster"]["RasterIniFN"] = iniFN
        if not self.coreParms:
            print("Problem in toronado.ini file.")
            self.coreParms = None
        self._initUI(versionNum = 0.833)
        self.rasterGUI = None
        self.imageDisplayThread = None

    def closeEvent(self, event):
       self._endToronadoProgram()

    # interface functions are here

    def requestNewImageDisplayItem(self, newItem):
        # pass request through to imageDisplay window via the separate thread where it runs
        if self.imageDisplayThread:
            self.imageDisplayThread.requestNewDisplayItem(newItem)

    def passCurrentCursorPos(self, xVolts, yVolts, spotName, testMode):
        # now pass information down to RasterGUI instance
        self.rasterGUI.setCursorPos(xVolts, yVolts, spotName, testMode)

    def processINIfile(self, iniFileName):
        # returns a Dict
        try:
            if path.exists(iniFileName):
                config = ConfigParser.ConfigParser()
                config.read(iniFileName)
                coreDict = EasyDict()
                for oneSection in config.sections():
                    if config[oneSection]:
                        coreDict[oneSection] = EasyDict()
                        for key in config[oneSection]:
                            coreDict[oneSection][key] = config[oneSection][key].split(";")[0].strip()
                return coreDict
            else:
                return None
        except:
            return None

    # internal routines below here

    def _initUI(self, versionNum):
        self._initToolbar()
        self.sb = self.statusBar()
        self.setCentralWidget(self.tb)
        self.setGeometry(10, 60, 280, 70)
        pVer = str(sys.version_info[0]) + "." + str(sys.version_info[1])
        self.setWindowTitle("Toronado ver " + str(versionNum) + " Python " + pVer)
        #self.connect(self, QtCore.SIGNAL('triggered()'), self.closeEvent) # fix me

    def _initToolbar(self):
        self.tb = self.addToolBar("Command")

        self.imageAction = QtGui.QAction(QtGui.QIcon("Icons/crop.png"), "ImageWin", self)
        self.imageAction.setStatusTip("Open a new image display window")
        self.imageAction.triggered.connect(self._doNewImageWin)

        self.rasterGUIAction = QtGui.QAction(QtGui.QIcon("Icons/flashlight.png"), "Raster", self)
        self.rasterGUIAction.setStatusTip("Open a Raster scanning control panel")
        self.rasterGUIAction.triggered.connect(self._doNewRasterWin)

        self.endAction = QtGui.QAction(QtGui.QIcon("Icons/time.png"), "End", self)
        self.endAction.setStatusTip("End Toronado program")
        self.endAction.triggered.connect(self._endToronadoProgram)

        self.tb.addAction(self.rasterGUIAction)
        self.tb.addAction(self.imageAction)
        self.tb.addSeparator()
        self.tb.addAction(self.endAction)

    def _doNewImageWin(self):
        if not self.imageDisplayThread:
            # create new thread for ImageDisplay and display one window
            falseStrings = ["none", "off", "false", "no", "0"]
            useNativeGUI = self.coreParms["Raster"]["useNativeGUI"].lower() not in falseStrings
            self.imageDisplayThread = RDT.clsRasterDisplayThread(self, useNativeGUI)
            self.imageDisplayThread.start()
        else:
            # thread exists, so request that it adds another display window
            self.imageDisplayThread.addNewImageWindow()

    def _doNewRasterWin(self):
        transferDict = EasyDict()
        for key in self.coreParms["IPC"]:
            transferDict[key] = self.coreParms["IPC"][key]
        for key in self.coreParms["Raster"]:
            transferDict[key] = self.coreParms["Raster"][key]
        self.rasterGUI = RGUI.clsRasterGUI(self, transferDict)

    def _endToronadoProgram(self):
        if self.rasterGUI:
            self.rasterGUI.closeWindow()
        if self.imageDisplayThread:
            self.imageDisplayThread.closeImageWindows()
        QtGui.QApplication.quit()


if __name__ == "__main__":
    if os.name == "posix":
        tempStr = ["~/LabWorld/", "~/LabWorld/INIs/", "~"]
        searchFolders = [path.expanduser(oneFolder) for oneFolder in tempStr]
        iniFileName = path.expanduser("~") + "/LabWorld/Toronado.ini"
    else:
        searchFolders = ["D:/LabWorld/", "D:/LabWorld/INIs/", "D:/", "C:/"]
        iniFileName = "D:/LabWorld/Toronado.ini"
    iniFileName = None
    for oneFolder in searchFolders:
        tempStr = oneFolder + "Toronado.ini"
        if path.exists(tempStr):
            iniFileName = tempStr
            print("  reading parameters from " + iniFileName)
            break
    if iniFileName:
        app = QtGui.QApplication(sys.argv)
        thisInstance = clsMainWindow(iniFileName)
        thisInstance.show()
        sys.exit(app.exec_())
    else:
        print("ERROR - Could not find required Toronado.ini file")
        print("  looked in: " + str(searchFolders))



