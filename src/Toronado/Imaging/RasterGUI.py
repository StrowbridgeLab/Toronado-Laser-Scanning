# -*- coding: utf-8 -*-
"""Modeless dialog GUI for controlling raster scanning system.

This module generates a temp parm file and can add commands to the main hoper file that is shared with CentralCommand

Added preset files 30 Aug 2016 (folder location set in main INI file)
Changed to TCP socket interface 25 Mar 2017

last revised 29 Dec 2017 BWS

"""

import numpy as np
import scipy.stats as stats
from pyqtgraph.Qt import QtGui, QtCore
import os.path as path
import datetime
import time
import os
import sys
import zipfile
import shutil
import threading
import importlib
import configparser as ConfigParser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import Imaging.Helper.RasterDisplayThread as RDT
import Imaging.Helper.rasterPlots as RP
import traceback
import Imaging.doScan as DS

class clsRasterGUI(QtGui.QDialog):
    """The core scope window class

    The class is initiated with one variable: a reference to the main GUI window.The clsRasterGUI class
    needs the reference to the calling program instance because some functions executed within the
    RasterGUI window need to pass information back to parent program (eg, to pass the name of a newly
    acquired frame/movie to all the ImageDisplay windows controlled by the callingInstance window.)

    """
    def __init__(self, callingInstance, iniParameters):
        super(clsRasterGUI, self).__init__()
        self.callingInstance = callingInstance # save handle so we can use that instance to display images
        # read in required parameters and setup initial conditions; save the minor parameter dict
        self.minorParameters = self._initParms(iniParameters, versionNumber=0.982)
        if not self.minorParameters:
            sys.exit()
        self.minorParmsDirty = False
        self.lastMajorParms = None
        self.lastNumFrames = None
        self.lastEstSec = None
        self.falseStrings = ["false", "no", "0", "off"]
        self.focusMode = False
        self.lastStartTime = None
        self.runViaAxograph = False
        # start the Axograph file watcher if requested in system iniParameter file
        self._initAxographWatcher(iniParameters)
        # save the main system parameters dict
        self.systemParms = iniParameters
        if not path.exists(self.systemParms["tempFolder"]):
            os.mkdir(self.systemParms["tempFolder"])
        if "presetsFolder" in self.systemParms:
            if "~" in self.systemParms["presetsFolder"]:
                self.systemParms["presetsFolder"] = path.expanduser(self.systemParms["presetsFolder"])
            if not path.exists(self.systemParms["presetsFolder"]):
                print("Requested presetsFolder does not exist: " + self.systemParms["presetsFolder"])
                self.systemParms["presetsFolder"] = None
        else:
            self.systemParms["presetsFolder"] = None
        self._refreshPresetList()
        # start the user interface GUI
        self.showLaserControl = False
        self.showPhotometryControl = True
        self._initUI()
        self.guiLockOut = False


    # Core routines that commmunicate with hardware acquisition system via functions in the
    #    Imaging.doScan module. The functions here simply write control text files using the INI format
    #    and then call a specific function in Imaging.doScan to execute the socket connection to hardware

    def runScanner(self, retFunction, newFileName, numFrames=1, focusMode=False):
        # retFunction is routine that should be called once new image data is available
        #  (This routine communicates with hardware via the doRunScanner function in the Image.doScan module)
        QtGui.QApplication.processEvents()
        tempCmds = {}
        tempCmds["numFrames"] = str(numFrames)
        tempCmds["focusMode"] = str(int(focusMode)) # converts True to 1 but still allows 0 or 1 to be passed
        tempCmds["destFileName"] = newFileName
        if self.lastEstSec:
            tempCmds["estSecPerFrame"] = str(self.lastEstSec)
        tempCmds["doScanFunction"] = "runScanner"
        cmdFN = self._writeControlFile(tempCmds) # writes cmd.txt file with tempCmds key,value added to [Interface]
        # next line writes imageDesc file and waveforms, if needed, and communicates with hardwarePC
        if not cmdFN:
            print("ERROR - did not get back a proper cmdFN from writeControlFile inside runScanner")
            return None
        retDict = DS.doCommonEntry(cmdFN)
        if retDict["retOkay"]:
            retFileName = retDict["newFileName"]
            imageDescFN = retDict["imageDescFN"]
            echoStr = self.minorParameters["echostring"].strip()
            if len(echoStr) > 0:
                print(echoStr)
            postProcFuncName = self.minorParameters["postprocfunction"].lower().strip()
            if len(postProcFuncName) and int(self.minorParameters["postprocenable"]):
                postModuleName = self.minorParameters["postprocmodule"].strip()
                if len(path.split(postModuleName)[0]) == 0:
                    postModuleName = "Imaging.Helper." + postModuleName
                try:
                    postModule = importlib.import_module(postModuleName)
                except:
                    print("ERROR - problem importing module: " + postModuleName)
                try:
                    getattr(postModule, postProcFuncName)(retFileName)
                except:
                    print("ERROR - could not match requested postProcFunction: " + postProcFuncName)

            if int(self.minorParameters["calldisplay"]) == 1:
                retFunction(retFileName)
            if imageDescFN:
                curParms = self.callingInstance.processINIfile(imageDescFN) # full saved parm set
                self.lastEstSec = float(curParms["Derived"]["estimatedTotalSeconds"])
                if "statusMsg" in curParms["Derived"]:
                    self.statusLabel.setText(curParms["Derived"]["statusMsg"])
                else:
                    self.statusLabel("no returned status update from scan gen routine")
                if int(self.minorParameters["diagmode"]):
                    print("  updated lastEstSec to " + str(self.lastEstSec))
                return retFileName, curParms
            else:
                return retFileName, None
        else: # retOkay is False from RunScanner
            print("Problem running scanner.")
            self.lastNumFrames = -1 # to force regeneration of scan waveforms on next scan
            return "", None

    def sendGenericCommand(self, newCmdStr):
        # Main routine for sending mode change commands such as openShutter
        #  (This routine communicates with hardware via doGenericCommand)
        tempCmds = {}
        tempCmds["doScanFunction"] = "genericCommand"
        tempCmds["specificCommand"] = newCmdStr
        cmdFN = self._writeControlFile(tempCmds) # writes cmd.txt file
        if not cmdFN:
            print("ERROR - did not get back a proper cmdFN from writeControlFile")
            return None
        retDict = DS.doCommonEntry(cmdFN)
        return retDict["retOkay"]

    def loadPhotometryScans(self):
        # Arms the photometry system (Communicates with hardware via doArmPhotometry)
        if not self.photometryMode:
            print("Problem inside loadPhotometryScans because not in photometryMode")
            return False
        QtGui.QApplication.processEvents()
        self.minorParameters["forcenewscanwaveforms"] = "1" # to force all parameters to be written to text file
        tempCmds = {}
        tempCmds["doScanFunction"] = "armPhotometry"
        cmdFN = self._writeControlFile(tempCmds) # writes cmd.txt file
        # next line writes imageDesc file and waveforms, if needed, and communicates with hardwarePC
        if not cmdFN:
            print("ERROR - did not get back a proper cmdFN from writeControlFile inside loadPhotometryScans")
            return None, None
        retDict = DS.doCommonEntry(cmdFN)
        return retDict["retOkay"]

    def testPhotometryScan(self, xVolt, yVolt):
        # runs a brief photometry scan and retrieves output; allows testing different X offset adjustments
        #  (Communicates with hardware via doTestPhotometry)
        oldPhotometryMode = self.photometryMode
        oldMinorParms = self.minorParameters.copy()
        self.minorParameters["photometrydurms"] = "15" # do photometry spot test for 15 ms
        self.minorParameters["photometryspotname"] = "testSpot"
        self.minorParameters["photometrycurxvolts"] = str(xVolt)
        self.minorParameters["photometrycuryvolts"] = str(yVolt)
        QtGui.QApplication.processEvents()
        self.minorParameters["forcenewscanwaveforms"] = "1" # to force all parameters to be written to text file
        tempCmds = {}
        tempCmds["doScanFunction"] = "testPhotometry"
        cmdFN = self._writeControlFile(tempCmds) # writes cmd.txt file
        # next line writes imageDesc file and waveforms, if needed, and communicates with hardwarePC
        if not cmdFN:
            print("ERROR - did not get back a proper cmdFN from writeControlFile inside loadPhotometryScans")
            return None, None
        retDict = DS.doCommonEntry(cmdFN)

        self.minorParameters = oldMinorParms.copy()
        self.photometryMode = oldPhotometryMode
        self._disablePhotometryMode()

        if retDict["retOkay"]:
            self.lastTestPhotometryXvolts = xVolt
            self.lastTestPhotometryYvolts = yVolt
            return retDict["meanChanA"], retDict["meanChanB"]
        else:
            return None, None

    def _writeControlFile(self, doScanCommands, newFileName="", numFrames=1, focusMode=0):
        #  helper routine that is typically called before communicating with hardware computer
        #    this routine packages the current parameters and fileName/frame info if taking images
        #    required doScanCommands is a Dict with information about which routine inside DoScan.py
        #    should be called and provides any parameters the top-level DoScan function needs
        #    The doScanCommands Dict needs to provide a string value for the "doScanFunction" key
        cmdFileName = self.systemParms["tempFolder"] + "/DoScanInput.txt"
        with open(cmdFileName, "w") as fControl:
            refreshNeeded = self._checkForChangedMajorParms()
            numFramesChanged = numFrames != self.lastNumFrames
            requiredScanRefresh = 0
            if refreshNeeded or numFramesChanged or 1 == int(self.minorParameters["forcenewscanwaveforms"]):
                self.txtMsg = " new scan waveforms"
                majorParms = self._gatherMajorParameters()
                print("[Major]", file=fControl)
                for oneKey in sorted(majorParms.keys()):
                    print(oneKey + " = " + str(majorParms[oneKey]), file=fControl)
                print("[Minor]", file=fControl)
                for oneKey in sorted(self.minorParameters.keys()):
                    print(oneKey + " = " + str(self.minorParameters[oneKey]), file=fControl)
                self.minorParmsDirty = False
                self.lastNumFrames = numFrames
                if int(self.minorParameters["diagmode"]) == 1:
                    print("  generated new scan waveforms.")
                requiredScanRefresh = 1
            print("[Interface]", file=fControl)
            for oneKey in sorted(doScanCommands.keys()):
                # add DoScan control parameters to [Interface] section
                print(str(oneKey) + " = " + str(doScanCommands[oneKey]), file=fControl)
            print("updateScanWaveforms = " + str(requiredScanRefresh), file=fControl)
            print("positionData = " + str(self.minorParameters["positionepisode"]), file=fControl)
            print("diagMode = " + str(self.minorParameters["diagmode"]), file=fControl)
            print("systemini = " + self.systemParms["RasterIniFN"], file=fControl)
        self.minorParameters["forcenewscanwaveforms"] = "0"
        return cmdFileName


    # Main imaging GUI callback functions

    def doSingle(self):
        # GUI callback
        if self.photometryMode:
            self._disablePhotometryMode()
        if not self.guiLockOut:
            self.cmdSingle.setFocus(True)
            self.setWindowTitle("Single frame started with " + self.minorParameters["objective"])
            self.guiLockOut = True
            retFileName, curParms = self.runScanner(self.callingInstance.requestNewImageDisplayItem,
                                                       self._getNextSaveFileName(),
                                                       numFrames=1)
            self.guiLockOut = False

    def doMovie(self):
        # GUI callback
        if self.photometryMode:
            self._disablePhotometryMode()
        if not self.guiLockOut:
            self.cmdMovie.setFocus(True)
            self.setWindowTitle("Movie acquisition started ...")
            self.curMode = "movie"
            self.guiLockOut = True
            retFileName, curParms = self.runScanner(self.callingInstance.requestNewImageDisplayItem,
                                                       self._getNextSaveFileName(),
                                                       numFrames=int(self.numFrames.value()))
            self.guiLockOut = False

    def doFocus(self):
        # GUI callback
        if self.photometryMode:
            self._disablePhotometryMode()
        if not self.focusMode:
            self.cmdFocus.setText("Stop")
            self.cmdFocus.setFocus(True)
            self.setWindowTitle("Focus mode started ...")
            self.curMode = "focus"
            self.focusMode = True
            while self.focusMode:
                QtGui.QApplication.processEvents()
                retFileName, curParms = self.runScanner(self.callingInstance.requestNewImageDisplayItem,
                                                       self._getNextSaveFileName(forceTemp=True),
                                                       numFrames=1)
                if retFileName and int(self.minorParameters["diagmode"]):
                    print("Got frame at " + str(datetime.datetime.now()))
            self._stopFocusMode()
        else:
            self._stopFocusMode()

    def _stopFocusMode(self):
        # helper function for doFocus()
        self.focusMode = False
        self.cmdFocus.setText("Focus")
        self.setWindowTitle("Focus mode stopped.")
        QtGui.QApplication.processEvents()


    # NonRaster related functions

    def setCursorPos(self, xVolts, yVolts, spotName, testMode):
        # Photometry related function to store X and Y voltages in Dict assocated with GUI comboBox of spot names
        # called either by RasterGUI with X and Y volts and a spotName to be added to the comboBox or
        #   internally when a previous testSpot position should be added to the comboBox
        if testMode:
            meanA, meanB = self.testPhotometryScan(xVolts, yVolts)
            print("Single spot test: " + str(int(meanA * 10) /10.) + " and " + str(int(meanB * 10) /10.))
        else:
            if spotName.strip():
                newKey = spotName.strip().replace(" ", "_")
                self.photoSpotsDict[newKey] = (xVolts, yVolts)
                self.photoName.addItems([spotName])
                self.photoName.setCurrentIndex(self.photoName.count() - 1)
                # print("inside RasterGUI: " + str(xVolts) + " " + str(yVolts) + " " + spotName)
            else:
                print("Problem with empty spot name passed to setCursorPos in RasterGUI")

    def doPhotoArm(self):
        # GUI callback
        curKey = str(self.photoName.currentText()).replace(" ", "_")
        if curKey:
            self.photometryMode = True
            self.photoLabel.setStyleSheet("color: rgb(255, 0, 0)")
            self._updatePhotometryParameters()
            self.loadPhotometryScans()
            tempStr = "Armed "  + str(datetime.datetime.now()) + " - " + self.photoName.currentText() + " | RevPerMs: " + self.minorParameters["photometryrevperms"] + "  Diam: " + self.minorParameters["photometrydiameter"] + "  Pos: " + str(self.photoSpotsDict[curKey])
            self.minorParameters["photometryLastArmedDesc"] = tempStr
            print("  " + tempStr)

        else:
            print("Problem with no spot names registered from ImageDisplay window (use E key there)")

    def _updatePhotometryParameters(self):
        # helper function for commonly used code
        curKey = str(self.photoName.currentText()).replace(" ", "_")
        self.minorParameters["photometrycurxvolts"] = str(self.photoSpotsDict[curKey][0])
        self.minorParameters["photometrycuryvolts"] = str(self.photoSpotsDict[curKey][1])
        self.minorParameters["photometryspotname"] = self.photoName.currentText()
        self.minorParameters["photometrydurms"] = str(self.photoMs.value())

    def doPhotoDisable(self):
        # GUI callback
        self._disablePhotometryMode()

    def doPhotoAutoX(self):
        # GUI callback
        print("in photo autoX")
        curKey = str(self.photoName.currentText()).replace(" ", "_")
        if curKey:
            self.photometryMode = True
            self.photoLabel.setStyleSheet("color: rgb(255, 0, 0)")
            curPosX = self.photoSpotsDict[curKey][0]
            curPosY = self.photoSpotsDict[curKey][1]
            bestAsignal = 0.
            bestAoffset = 0.
            for ii in range(-10, 10):
                xOffset = ii * float(self.minorParameters["photometryautoinc"])
                self._updatePhotometryParameters()
                meanA, meanB = self.testPhotometryScan(curPosX + xOffset, curPosY)
                print("test offset: " + str(xOffset) + " meanA: " + str(meanA))
                if meanA > bestAsignal:
                    bestAsignal = meanA
                    bestAoffset = xOffset
            if bestAoffset != 0.:
                print("setting best offset to " + str(bestAoffset))

    def _disablePhotometryMode(self):
        # Helper function for commonly used code
        self.sendGenericCommand("DisarmPhotometry")
        self.photometryMode = False
        self.photoLabel.setStyleSheet("color: rgb(0, 0, 0)")
        self.minorParameters["forcenewscanwaveforms"] = "1"
        return True


    # Diagonistics functions

    def doTest(self):
        # GUI callback
        if not self.guiLockOut:
            if self.photometryMode:
                self._disablePhotometryMode()
            self.cmdTest.setFocus(True)
            QtGui.QApplication.processEvents()
            cmdFN = self._writeControlFile() # writes cmd.txt file
            if not cmdFN:
                print("ERROR - did not get back a proper cmdFN in runScanner")
                return None, None
            retOkay = DS.doGenericCommand(cmdFN)
            if False:
                newParms = self.runScanTest()
                if newParms:
                    if "statusMsg" in newParms["Derived"]:
                        self.statusLabel.setText("* " + newParms["Derived"]["statusMsg"] + " *")
                    print("  *** Test completed ***")
                    print("Estimated frame ms: " + newParms["Derived"]["estimatedFrameMs"])
                    print("Turn Length in pixels: " + newParms["Derived"]["turnLength"])
                    print(" ")
                    self._dictToStringList(newParms["derived"], printNow=True)

    def runScanTest(self):
        #  (Communicates with hardware via doRunScanner)
        self.minorParmsDirty = True
        cmdFN = self._writeControlFile(newFileName="test.gsi", numFrames=1) # writes cmd.txt file
        if cmdFN:
            retFileName, imageDescFN = DS.doRunScanner(cmdFN, estSecPerFrame=self.lastEstSec, testScanOnly=True)
            if imageDescFN:
                curParms = self.callingInstance.processINIfile(imageDescFN)
                if not curParms:
                    print("ERROR - did not get back a readable curParms Dict from ImageDesc file: " + imageDescFN)
                    curParms = None
            else:
                print("ERROR - problem reading parameters from ImageDesc file in test run.")
                curParms = None
        else:
            print("ERROR - did not get back a pr oper cmdFN in runScanner")
            curParms = None
        self.minorParmsDirty = True
        return curParms

    def plotRowPair(self):
        tempMinorParms = self.minorParameters.copy()
        self.minorParmsDirty = True
        self.minorParameters["saverowpair"] = "1"
        newParms = self.runScanTest()
        if newParms:
            rowData = np.fromfile(newParms["Derived"]["rowPairFileName"])
            tempStr = "Row Pair "
            if int(self.minorParameters["bidirectional"]) == 1:
                tempStr += "(BiDir: " + self.minorParameters["bidirends"] + "; turnLength = " + str(newParms["Derived"]["turnLength"])
            else:
                tempStr += "(UniDir: linear percentage = " + self.minorParameters["linearpercentage"]
            tempStr += " NumPoints = " + str(len(rowData)) + ")"
            scanFraction = 1. - ((2 * int(newParms["Derived"]["turnLength"])) / len(rowData))
            tempStr += " Scan " + str(int(100 * scanFraction)) + "%"
            RP.plotRowData(rowData, float(newParms["Derived"]["rowPairMs"]), int(newParms["Derived"]["turnLength"]), tempStr)
        else:
            print("ERROR - problem getting new parameters back from scan test")

    def takePositionFrame(self, positionFileName=None):
        # similar to doSingle but with flag set to return galvo position data and not open shutter
        if not positionFileName:
            positionFileName = self._getNextSaveFileName(forceTemp=True)
        oldSaveRowPair = self.minorParameters["saverowpair"]
        self.minorParameters["positionepisode"] = 1
        self.minorParameters["saverowpair"] = 1
        self.guiLockOut = True
        retFileName, curParms = self.runScanner(None, positionFileName, numFrames=1)
        self.guiLockOut = False
        self.minorParameters["positionepisode"] = 0
        self.minorParameters["saverowpair"] = oldSaveRowPair
        if retFileName:
            if self.minorParameters["diagmode"]:
                print("Position episode captured")
            return positionFileName
        else:
            print("ERROR - problem acquiring position frame.")
            return None


    # Ancillary GUI callback functions

    def doSaveFolder(self):
        # GUI callback
        if not self.guiLockOut:
            self.cmdSaveFolder.setFocus(True)
            myFile= QtGui.QFileDialog.getExistingDirectory(self, "Select folder for images")
            if myFile:
                print("Save folder update to " + str(myFile))
                self.imageSaveFolder = str(myFile)

    def doLoadPreset(self):
        # GUI callback
       # majorCmds = ["xsize","ysize","chanafullscale","chanbfullscale","chancfullscale","chandfullscale", "pixelus", "zoom"]
        presetFile = self.systemParms["presetsFolder"] + "/" + str(self.presetList.currentText()) + ".txt"
        if path.exists(presetFile):
            self._processPresetFile(presetFile)
            print("Executed statements in  " + str(self.presetList.currentText()) + ".txt")
        else:
            print("Requested preset file does not exist: " + presetFile)

    def _refreshPresetList(self):
        # helper function for presets
        if self.systemParms["presetsFolder"]:
            myPath = self.systemParms["presetsFolder"]
            if not path.exists(myPath):
                print("Preset folder supplied in INI file does not exist: " + myPath)
                self.systemParms["availablePresets"] = []
                return True
            temp = [f for f in os.listdir(myPath) if path.isfile(path.join(myPath, f))]
            parmFiles = [path.splitext(f)[0] for f in temp if path.splitext(f.lower())[1] == ".txt"]
            self.systemParms["availablePresets"] = parmFiles
            if int(self.minorParameters["diagmode"]):
                print("Presets: " + str(parmFiles))
        else:
            # presetsFolder key is in Dict but has no value so no presets are available
            self.systemParms["availablePresets"] = []


    # optional laserRemoteControl functions
    def doSetLaser5(self):
        # GUI callback
        self.laser.setValue(5)

    def doSetLaser10(self):
        # GUI callback
        self.laser.setValue(10)

    def doSetLaser20(self):
        # GUI callback
        self.laser.setValue(20)

    def laserChanged(self):
        print("dummy New laser cmd: " + str(self.laser.value()))


    def doCloseShutter(self):
        # GUI callback
        self.sendGenericCommand("CloseShutter")

    def doSpecialCmd(self):
        # GUI callback
        if not self.guiLockOut:
            self.cmdSpecialCmd.setFocus(True)
            text, ok = QtGui.QInputDialog.getText(self, "Enter command", "")
            if ok:
                self._processCmdLine(text, printMsg=True)

    def closeWindow(self):
        # GUI callback
        QtCore.QCoreApplication.instance().quit()


    # helper functions for processing command lines and script/preset files below here

    def _processCmdLine(self, oneLineIn, printMsg=False):
        # this is the main routine that processes a text line from the doCmd window or a preset file
        #  oneLineIn can be: (1) a presetFileName without ext, (2) a one-word command, (3) a Major
        #     parameter or (4) a Minor parameter - last two can be separated by = or a space from newValue
        oneLine = oneLineIn.split(";")[0].strip() # allow comments after a ; symbol
        retOkay = True
        if len(oneLine) > 0:
            if oneLine.lower() in (onePreset.lower() for onePreset in self.systemParms["availablePresets"]):
                # the text line is actually the name of script/preset file that should be processed
                if printMsg:
                    print("  processing preset file: " + oneLine)
                retOkay = self.processPresetFile(oneLine)
            else:
                # is it a command link Dump or Help?
                retOkay = self._executeSpecialCommand(oneLine)
                if retOkay and printMsg:
                    print("Processed command: " + oneLine)
                if not retOkay:
                    # so it must be an assignment operation to change a Major or Minor parameter
                    retStr = self._executeAssignmentCommand(oneLine)
                    if retStr and printMsg:
                        print("Changed value associated with: " + retStr)
                    if retStr:
                        retOkay = True
                    else:
                        print("  problem with Cmd line: " + oneLineIn)
        return retOkay

    def _executeSpecialCommand(self, actualCommand):
        retValue = True
        if actualCommand in ["help"]:
            print("Minor parameters: " + str(self.minorParameters.keys()))
            print("Special commands: help, dump, dumplow")
        elif actualCommand in ["dumpraw"]:
            print(self.minorParameters)
        elif actualCommand in ["dumpminor", "dump"]:
            print(" Minor ")
            self._dictToStringList(self.minorParameters, printNow=True)
        elif actualCommand in ["dumpall", "dumpparams"]:
            print(" Major ")
            self._dictToStringList(self._gatherMajorParameters(), printNow=True)
            print(" Minor ")
            self._dictToStringList(self.minorParameters, printNow=True)
            print(" System ")
            self._dictToStringList(self.systemParms, printNow=True)
        elif actualCommand in ["plotrowpair", "plotrow", "pr"]:
            self.plotRowPair()
        elif actualCommand in ["plotxpos", "plotxposition", "plotx"]:
            self.plotXpos()
        elif actualCommand in ["refresh", "refreshpresets"]:
            print("refreshing list of available preset/script files in: " + self.systemParms["presetsFolder"])
            self._refreshPresetList()
        elif actualCommand in ["default", "defaults", "reset"]:
             self.minorParameters = self.setupDefaultMinorParameters()
             self._setInitUIvalues()
             self.minorParmsDirty = True # to force remake scan wave files
             self.lastMajorParms = None
             print("Reset minor parameters to their default values.")
        elif actualCommand in ["spot", "savespot"]:
            # takes last testPhotometry X Y spot and adds that point to the photometry comboBox
            if self.lastTestPhotometryXvolts and self.lastTestPhotometryYvolts:
                spotName = self._msgBox("Enter spot name", "Using last saved X Y test spot")
                self.setCursorPos(self.lastTestPhotometryXvolts, self.lastTestPhotometryYvolts, spotName, False)
        elif actualCommand in ["clearspot", "clearspots", "resetspots", "photometryclear"]:
            # remove all entries in photometry spot comboBox
            self.photoName.clear()
            self.doPhotoDisable()
            print("  Cleared all stored photometry spots.")
        else:
            retValue = False
        return retValue

    def _executeAssignmentCommand(self, cmdLine):
        if "=" in cmdLine:
            parts = cmdLine.split("=")
        else:
            parts = cmdLine.split(" ")
        if len(parts) < 2:
            print("ERROR - attempted assignement operation without two items")
            return False
        cmd = parts[0].strip().lower()
        noun = cmdLine[len(parts[0]) + 1:].strip() # capture the rest of the line after the = or first space
        if cmd == "xsize":
            self.xPixels.setValue(int(noun))
            return "xSize"
        elif cmd == "ysize":
            self.yPixels.setValue(int(noun))
            return "ySize"
        elif cmd == "zoom":
            self.zoom.setValue(float(noun))
            return "Zoom"
        elif cmd == "pixelus":
            newIndex = None
            newValue = float(noun)
            if newValue == 0.5: # 2 MHz
                newIndex = 0
            elif newValue == 0.7: # 1.5 MHz
                newIndex = 1
            elif newValue == 0.8: # 1.25 MHz
                newIndex = 2
            elif newValue == 1: # 1 MHz
                newIndex = 3
            elif newValue == 1.3: # 750 kHz
                newIndex = 4
            elif newValue == 2: # 500 kHz
                newIndex = 5
            elif newValue == 4: # 250 kHz
                newIndex = 6
            elif newValue == 10: # 100 kHz
                newIndex = 7
            else:
                print("Nonstandard clock pixelUs request via preset file: " + str(noun))
            if newIndex is not None:
                self.pixelClock.setCurrentIndex(newIndex)
                return "pixelUs"
            else:
                print("Problem in setting pixelUs value: " + str(noun))
                return False
        elif "fullscale" in cmd:
            newIndex = None
            if noun.lower() == "off":
                newIndex = 6
            else:
                newValue = float(noun)
                if newValue == 10:
                    newIndex = 0
                elif newValue == 5:
                    newIndex = 1
                elif newValue == 2:
                    newIndex = 2
                elif newValue == 1:
                    newIndex = 3
                elif newValue == 0.5:
                    newIndex = 4
                elif newValue == 0.2:
                    newIndex = 5
            if newIndex is not None:
                if cmd == "chanafullscale":
                    self.chanArange.setCurrentIndex(newIndex)
                elif cmd == "chanbfullscale":
                    self.chanBrange.setCurrentIndex(newIndex)
                elif cmd == "chancfullscale":
                    if newIndex == 6:
                        self.chanCfullScale = 0
                    else:
                        self.chanCfullScale = float(noun)
                elif cmd == "chandfullscale":
                    if newIndex == 6:
                        self.chanDfullScale = 0
                    else:
                        self.chanDfullScale = float(noun)
                else:
                    print("Unknown channel to for gain setting: " + cmd)
            return cmd
        else:
            # if not a major parameter, assume it is a minor parameter that should be updated
            return self._updateMinorParameter(cmd, noun)

    def _processPresetFile(self, presetFileName):
        with open(presetFileName, "r") as fPreset:
            presetData = fPreset.read().splitlines()
            for oneReadLine in presetData:
                retOkay = self._processCmdLine(oneReadLine)


    # Routines for organizing parameter Dicts

    def _updateMinorParameter(self, parmName, newValue):
        # newValue is a string and minorParmameters values should also be strings
        goodName = ""
        if parmName in self.minorParameters:
            goodName = parmName
        else:
            goodName = self._cleanUpMinorName(parmName)
        if goodName:
            if goodName not in ["diagmode", "bidirectional", "forcenewscanwaveforms", "postprocenable", "waitfortrig", "saverowpair", "positionepisode"]:
                self.minorParameters[goodName] = newValue
            else:
                self.minorParameters[goodName] = str(int(newValue not in self.falseStrings)) # for a 0 or 1; changed to Str
            self.minorParmsDirty = True
            if "photometry" == (goodName.lower())[:10] and self.photometryMode:
                # self.doArmPhotometry # automatically re-arm photometry if already active
                pass
            return goodName
        else:
            print("Requested parameter is not valid: " + parmName)
            return None

    def _cleanUpMinorName(self, cleanKey):
        retKey = ""
        if cleanKey in ["lagt", "lw"]:
            retKey = "lagtweakus"
        elif cleanKey in ["accf", "acc", "af"]:
            retKey = "accelfactor"
        elif cleanKey in ["centerx", "cx"]:
            retKey = "centerxvolts"
        elif cleanKey in ["centery", "cy"]:
            retKey = "centeryvolts"
        elif cleanKey in ["rot", "r"]:
            retKey = "rotation"
        elif cleanKey in ["echo", "echostr"]:
            retKey = "echostring"
        elif cleanKey in ["obj", "o"]:
            retKey = "objective"
        elif cleanKey in ["bidir", "bi"]:
            retKey = "bidirectional"
        elif cleanKey in ["pmta", "pmtagain"]:
            retKey = "pmtagainpercentage"
        elif cleanKey in ["pmtb", "pmtbgain"]:
            retKey = "pmtbgainpercentage"
        elif cleanKey in ["forcenew", "forcenewscans", "newscans", "newwaveforms", "new"]:
            retKey = "forcenewscanwaveforms"
        elif cleanKey in ["diag", "dm"]:
            retKey = "diagmode"
        elif cleanKey in ["revperms", "revms"]:
            retKey = "photometryrevperms"
        elif cleanKey in ["pdiam", "pdiameter", "diam"]:
            retKey = "photometrydiameter"
        elif cleanKey in ["pshape", "shape", "pmode", "mode", "photometrymode"]:
            retKey = "photometryshape"
        elif cleanKey in ["autoxinc", "xinc", "autoinc"]:
            retKey = "photometryautoinc"
        return retKey

    def _checkForChangedMajorParms(self):
        if self.minorParmsDirty or not self.lastMajorParms:
            return True
        else:
            isDirty = False
            newestParms = self._gatherMajorParameters(testOnly=True)
            for oneKey in self.lastMajorParms:
                if self.lastMajorParms[oneKey] != newestParms[oneKey]:
                    isDirty = True
                    break
            return isDirty

    def _gatherMajorParameters(self, testOnly=False):
        # returns a Dict containing the visible GUI parameters
        retDict = {}
        retDict["Xsize"] = int(self.xPixels.value())
        retDict["Ysize"] = int(self.yPixels.value())
        retDict["zoom"] = float(self.zoom.value())
        tempV = str(self.chanArange.currentText())
        if tempV.lower() == "off":
            tempV = "0"
        retDict["chanAfullScale"] = float(tempV.split(" ")[0])
        tempV = str(self.chanBrange.currentText())
        if tempV.lower() == "off":
            tempV = "0"
        retDict["chanBfullScale"] = float(tempV.split(" ")[0])
        retDict["chanCfullScale"] = 0 # change when allow more than two ADC channels
        retDict["chanDfullScale"] = 0
        tempV = str(self.pixelClock.currentText())
        base, baseRange = tempV.split(" ")
        newValue = float(base)
        if baseRange.lower() == "khz":
            newValue = newValue / 1000. # to MHz
        tempPixelUs = 1.0 / newValue
        if tempPixelUs * 10. != int(tempPixelUs * 10.):
            if tempV.lower() == "750 khz":
                retDict["pixelUs"] = 1.3
            elif tempV.lower() == "1.5 mhz":
                retDict["pixelUs"] = 0.7
            else:
                print("Warning: cannot used selected clock frequency because it has irrational pixel microseconds")
                print("  defaulting to 500 kHz pixel clock frequency")
                retDict["pixelUs"] = 2.0
        else:
            retDict["pixelUs"] = tempPixelUs
        if not testOnly:
            self.lastMajorParms = retDict
        return retDict

    def setupDefaultMinorParameters(self):
        tempDict = {} # those with NA are not implemented yet

        # Okay to adjust these parameters using command GUI interface
        # all these key strings should be lower case since they can be entered in dialog text box
        # also values have to be strings not float/int
        #tempDict["scanmodule"] = "createStandardScans" # either imports standard scanning module or specialized ones
        tempDict["scanfunction"] = "standard" # allows specialized scans if not passed as standard
        tempDict["calldisplay"] = "1" # whether to update the ImageDisplay windows after aquiring new data
        tempDict["postprocenable"] = "0"
        tempDict["postprocmodule"] = "" # allows special routines to be called after acquiring images
        tempDict["postprocfunction"] = "" # subroutine name to be called after acquiring images
        tempDict["echostring"] = "" # this entry will be printed out after every run in DiagMode
        tempDict["macrofolder"] = "~/LabWorld" # where to look for macro text files
        tempDict["bidirends"] = "maxaccel" # what the turn-arounds look like during bidirectional scanning
        # (mostly use maxaccel or parabolic but also can use point, flat, or square though these are
        #  primarily for debugging/optmizing the scan system)
        tempDict["accelfactor"] = "13" # should be about 4 with attenutation of 0.25 and 16 with no attenuation
        # the accelfactor governs how long the turn-arounds around; higher numbers mean more time/points devoted
        # to turn-around and therefore a smaller % of the scan spent acquiring actual data. The actual turn-
        # around duration in influenced by the pixel clock and zoom level as well. Only used with bidirectional scans
        tempDict["rotation"] = "0" # image rotation in degrees
        tempDict["xbinning"] = "1" # compresses the final image after decoding; value of 2 turns 512 acquired
        # pixels into a final image with 256 X pixels; adjecent pixels are summed to form final image
        tempDict["ybinning"] = "1" # same as above for Y axis
        tempDict["bidirectional"] = "1" # flag to indicate whether scan should be unidirectional (value = 0)
        # or bidirectional (value = 1)
        tempDict["linearpercentage"] = "80" # what percent of scan is used for image in unidirectional mode
        tempDict["lagtweakus"] = "0" # extra microseconds to add or subtract from systemLag INI parameter
        # used to tweak scans at high frequency to get optimal meshing of odd and even lines
        tempDict["centerxvolts"] = "0" # offet in raw scanner volts to move center position left or right
        tempDict["centeryvolts"] = "0" # same as above to control up/down position relative to optical center
        tempDict["zlevel"] = "0" # a string to be used to indicate Z stack position in microns
        tempDict["zstackindex"] = "0" # to be used to indicate relative position within a z stack (NA)
        tempDict["waitfortrig"] = "0" # whether the scan system should wait for an ext trig (0 or 1; NA)
        tempDict["objective"] = "5x air" # a string to indicate current objective; keep to this format with space
        # between magX and string description. String will be split on the first space to determine magnfication
        tempDict["listentoaxograph"] = "1" # flag to control whether new text msg files from Axograph can trigger
        # rasterGUI image acquisition (1 or 0)
        tempDict["diagmode"] = "1" # whether verbose information is dumped to terminal window during scanning
        # Internal parameters that should not be manually adjusted
        tempDict["positionepisode"] = "0" # internal flag (1 or 0) for acquiring position data; tells remote system to
        # not open the shutter and also sets the DIO2 output TTL line to high (to control external analog switch)
        tempDict["saverowpair"] = "0" # internal flag to write binary file containing the first two scan lines
        tempDict["gatepockelscell"] = "0" # controls whether the DIO3 TTL output line goes high during episode (1 or 0)
        tempDict["pmtagainpercentage"] = "70" # controls output gain on PMT-A; range 0-100 as a percentage of max
        tempDict["pmtbgainpercentage"] = "70" # controls output gain on PMT-B
        tempDict["forcenewscanwaveforms"] = 0 # controls whether speed-up happens (==0) when redoing same parameters
        tempDict["photometrycurxvolts"] = ""
        tempDict["photometrycuryvolts"] = ""
        tempDict["photometrydiameter"] = "10"
        tempDict["photometryautoinc"] = "0.01" # autoX test increment in volts
        tempDict["photometryshape"] = "circle" # circle, halfspiral, spiral or lissajous
        tempDict["photometryrevperms"] = "2" # revolutions (or spirals/lissajous patterns) per millisecond
        #tempDict["photometryspiralsteps"] = 4 # number of steps in shrinking phase of spiral (2x - 1 total steps)
        tempDict["photometrydurms"] = ""
        tempDict["photometryspotname"] = ""
        return tempDict


    # Misc helper functions

    def _getNextSaveFileName(self, forceTemp=False):
        # Helper function to make sure imaging save does not overwrite an existing file
        saveFile = None
        curExtension = ".gsi"
        if not forceTemp and (self.saveImages.isChecked() or self.runViaAxograph):
            fileIndex = 0
            while True:
                fileIndex += 1
                saveFile = self.imageSaveFolder + "/" + self.fileRoot.text()
                if fileIndex > 1:
                    saveFile += "_" + str(fileIndex)
                saveFile += curExtension
                if not path.exists(saveFile):
                    break
        else:
            saveFile = self.systemParms["tempFolder"] + "/tempSavedImage" + curExtension
        return saveFile

    def _dictToStringList(self, passDict, fileHandle=None, printNow=False):
        # this routine generates a list of strings representing each key in the passDict
        retList = []
        for key, value in sorted(passDict.items()):
            if isinstance(value, str):
                tempStr = key + " = " + value
            else:
                # value is not a string, so need to convert it to a string for appending and printing
                tempStr = key + " = " + str(value)
            retList.append(tempStr)
            if printNow:
                print(tempStr)
            if fileHandle: # optional directly write each line to a text file
                print(tempStr, file=fileHandle)
        return retList

    def _msgBox(self, windowTitle, labelText, defaultText = None):
        dlg = QtGui.QInputDialog(self)
        dlg.setInputMode(QtGui.QInputDialog.TextInput)
        dlg.setLabelText(labelText)
        dlg.setWindowTitle(windowTitle)
        if defaultText:
            dlg.setTextValue(defaultText)
        dlg.resize(500,100)
        ok = dlg.exec_()
        text = str(dlg.textValue())
        if ok & (len(text.strip()) > 0):
            return str(text.strip())
        else:
            return None


    # Unsorted functions

    def processAxographMessage(self, msgText):
        if int(self.minorParameters["listentoaxograph"]) == 1:
            self.fileRoot.setText(msgText)
            self.runViaAxograph = True
            self.doMovie()
        else:
            print("Ignored signal from Axograph because listenToAxograph = 0 (in minor parameters)")

    def _displayThreadEnded(self):
        pass

    def plotXposOld(self):
        print("Collecting data for plot of x position vs command")
        fN = self.writeAllParameters() # fN is the name of the ini file without dervived parameters
        retDict = self.rasterLowLevel.prepareScan(fN, numFrames=1)
        rowPairLastIndex = (4 * retDict["turnLength"]) + (4 * int(self.xPixels.value())) - 1
        cmdX = np.fromfile(self.systemParms["transferfolder"] + "/Input/ScanPointsX_float64.bin", dtype="float64")
        posX = np.fromfile(self.systemParms["transferfolder"] + "/Output/ADCA_int16.bin", dtype="int16")
        # factor of 2048 will return volts assuming X ADC FS is 1 volt
        inCmd = cmdX[100:rowPairLastIndex]
        posFactor = float(self.systemParms["positionfactor"])
        bestR = 0.
        bestLagPoints = -1
        for lagPoints in range(200):
            inPos = (posX[lagPoints + 100:lagPoints + rowPairLastIndex]).astype("float64") * posFactor / 2048.
            R = stats.pearsonr(inCmd, inPos)[0]
            print(str(lagPoints) + " " + str(R))
            if R > bestR:
                bestR = R
                bestLagPoints = lagPoints
        inPos = (posX[100 + bestLagPoints:rowPairLastIndex + bestLagPoints]).astype("float64") * posFactor / 2048.
        print(bestLagPoints)
        lagStr = str(bestLagPoints * retDict["pixelUs"]) + " us"
        print("Mag: " + str(np.mean(inPos/inCmd)))
        RP.plotXpos(inCmd, inPos, retDict["rowPairMs"], lagStr)

    def plotXpos(self):
        self.takePositionFrame()
        #RP.plotXpos(cmdData, posData, rowPairMs, extraTitleStr="")


    # GUI and parameter setup functions

    def _initUI(self):
        if self.showPhotometryControl:
            self.setGeometry(10, 200, 460, 260)
        else:
            self.setGeometry(10, 200, 460, 225)
        self.setWindowTitle("Raster Controller (ver " + str(self.minorParameters["rasterversion"]) + ")")
        buttonSize = QtCore.QSize(70,35)
        cmdSize = QtCore.QSize(70, 25)

        # Bottom row
        xPos = 280 # do this one first so it gets default focus
        if self.showPhotometryControl:
            yPos = 197
        else:
            yPos = 162
        self.cmdTest = QtGui.QPushButton("Test", parent=self)
        self.cmdTest.setFixedWidth(70)
        self.cmdTest.move(xPos, yPos)
        self.cmdTest.clicked.connect(self.doTest)
        #self.connect(self.cmdTest, QtCore.SIGNAL("clicked()"), self.doTest)

        xPos += 65
        self.cmdCloseShutter = QtGui.QPushButton("Close", parent=self)
        self.cmdCloseShutter.setFixedWidth(70)
        self.cmdCloseShutter.move(xPos, yPos)
        self.cmdCloseShutter.clicked.connect(self.doCloseShutter)

        xPos = 20
        self.cmdFocus = QtGui.QPushButton("Focus", parent=self)
        self.cmdFocus.setFixedWidth(70)
        self.cmdFocus.move(xPos,yPos)
        self.cmdFocus.clicked.connect(self.doFocus)
        #self.connect(self.cmdFocus, QtCore.SIGNAL("clicked()"), self.doFocus)

        xPos += 70
        self.cmdSingle = QtGui.QPushButton("Single", parent=self)
        self.cmdSingle.setFixedWidth(70)
        self.cmdSingle.move(xPos, yPos)
        self.cmdSingle.clicked.connect(self.doSingle)
        #self.connect(self.cmdSingle, QtCore.SIGNAL("clicked()"), self.doSingle)

        xPos += 70
        self.cmdMovie = QtGui.QPushButton("Movie", parent=self)
        self.cmdMovie.setFixedWidth(70)
        self.cmdMovie.move(xPos, yPos)
        self.cmdMovie.clicked.connect(self.doMovie)
        #self.connect(self.cmdMovie, QtCore.SIGNAL("clicked()"), self.doMovie)

        xPos += 70
        self.numFrames = QtGui.QSpinBox(parent=self)
        self.numFrames.setAlignment(QtCore.Qt.AlignHCenter)
        self.numFrames.setFixedSize(QtCore.QSize(50, 20))
        self.numFrames.move(xPos, yPos+4)
        self.numFrames.setRange(1, 500)
        self.numFrames.setValue(3)
        self.numFrames.setSingleStep(1)

        # top row of command buttons
        xPos = 10
        yPos = 5
        self.cmdSaveFolder = QtGui.QPushButton("SaveFolder", parent=self)
        self.cmdSaveFolder.setFixedWidth(90)
        self.cmdSaveFolder.move(xPos,yPos)
        self.cmdSaveFolder.clicked.connect(self.doSaveFolder)
        #self.connect(self.cmdSaveFolder, QtCore.SIGNAL("clicked()"), self.doSaveFolder)

        xPos += 95
        self.cmdSpecialCmd = QtGui.QPushButton("Command", parent=self)
        self.cmdSpecialCmd.setFixedWidth(90)
        self.cmdSpecialCmd.move(xPos,yPos)
        self.cmdSpecialCmd.clicked.connect(self.doSpecialCmd)
        #self.connect(self.cmdSpecialCmd, QtCore.SIGNAL("clicked()"), self.doSpecialCmd)

        xPos += 100
        self.fileRoot = QtGui.QLineEdit(parent=self)
        self.fileRoot.setFixedWidth(200)
        self.fileRoot.setAlignment(QtCore.Qt.AlignCenter)
        self.fileRoot.move(xPos, yPos+4)
        font = self.fileRoot.font()
        font.setFamily("Helvetica")
        font.setPointSize(8)
        self.fileRoot.setText("defaultImageRoot")

        # Column #1
        xPos = 100
        yPos = 40
        xPixelsLabel = QtGui.QLabel("X pixels", parent=self)
        xPixelsLabel.move(50, yPos+5)
        self.xPixels = QtGui.QSpinBox(parent=self)
        self.xPixels.setAlignment(QtCore.Qt.AlignHCenter)
        self.xPixels.setFixedSize(cmdSize)
        self.xPixels.setRange(1, 2048)
        self.xPixels.setSingleStep(64)
        self.xPixels.move(xPos, yPos)

        yPos = 70
        yPixelsLabel = QtGui.QLabel("Y pixels", parent=self)
        yPixelsLabel.move(50, yPos+5)
        self.yPixels = QtGui.QSpinBox(parent=self)
        self.yPixels.setAlignment(QtCore.Qt.AlignHCenter)
        self.yPixels.setFixedSize(cmdSize)
        self.yPixels.setRange(1, 2048)
        self.yPixels.setSingleStep(10)
        self.yPixels.move(xPos, yPos)

        yPos = 100
        chanAlabel = QtGui.QLabel("PMT A " + self.systemParms["chananame"], parent=self)
        chanAlabel.move(18, yPos+5)
        rangeValues = [oneEntry.strip() for oneEntry in self.systemParms["adcRanges"].split(",")]
        self.chanArange = QtGui.QComboBox(parent=self)
        self.chanArange.setFixedSize(cmdSize)
        self.chanArange.setEditable(True)
        self.chanArange.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
        self.chanArange.lineEdit().setReadOnly(True)
        self.chanArange.addItems(rangeValues)
        self.chanArange.move(xPos, yPos)

        yPos = 130
        chanBlabel = QtGui.QLabel("PMT B " + self.systemParms["chanbname"], parent=self)
        chanBlabel.move(18, yPos+5)
        self.chanBrange = QtGui.QComboBox(parent=self)
        self.chanBrange.setFixedSize(cmdSize)
        self.chanBrange.setEditable(True)
        self.chanBrange.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
        self.chanBrange.lineEdit().setReadOnly(True)
        self.chanBrange.addItems(rangeValues)
        self.chanBrange.move(xPos, yPos)

        self.statusLabel = QtGui.QLabel("status ...", parent=self)
        self.statusLabel.setFixedSize( QtCore.QSize(400, 20))
        self.statusLabel.setAlignment(QtCore.Qt.AlignCenter)
        if self.showPhotometryControl:
            self.statusLabel.move(10, 232)
        else:
            self.statusLabel.move(10, 195)

        # optional photometry GUI items

        yPos = 162
        if self.showPhotometryControl:
            self.photoLabel = QtGui.QLabel("Photometry ", parent=self)
            self.photoLabel.move(18, yPos+5)
            self.photoName = QtGui.QComboBox(parent=self)
            self.photoName.setFixedWidth(120)
            self.photoName.setEditable(True)
            self.photoName.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
            self.photoName.lineEdit().setReadOnly(True)
            #self.photoName.currentIndexChanged.connect(self._disablePhotometryMode)
            self.photoName.currentIndexChanged.connect(self.doPhotoArm)
            self.photoName.move(100, yPos)
            self.photoMs = QtGui.QSpinBox(parent=self)
            self.photoMs.setAlignment(QtCore.Qt.AlignHCenter)
            self.photoMs.setFixedSize(cmdSize)
            self.photoMs.setRange(0, 10000)
            self.photoMs.setSingleStep(100)
            self.photoMs.move(220, yPos)
            #self.photoMs.valueChanged.connect(self._disablePhotometryMode)
            self.photoMs.valueChanged.connect(self.doPhotoArm)
            self.cmdPhotoArm = QtGui.QPushButton("Arm", parent=self)
            self.cmdPhotoArm.setFixedWidth(50)
            self.cmdPhotoArm.move(290,yPos-2)
            #self.cmdPhotoArm.clicked.connect(self.doPhotoArm)
            self.cmdPhotoArm.clicked.connect(self.doPhotoArm)
            self.cmdPhotoDisable = QtGui.QPushButton("Disable", parent=self)
            self.cmdPhotoDisable.setFixedWidth(70)
            self.cmdPhotoDisable.move(335,yPos-2)
            self.cmdPhotoDisable.clicked.connect(self.doPhotoDisable)
            self.cmdPhotoAutoX = QtGui.QPushButton("Ax", parent=self)
            self.cmdPhotoAutoX.setFixedWidth(50)
            self.cmdPhotoAutoX.move(400,yPos-2)
            self.cmdPhotoAutoX.clicked.connect(self.doPhotoAutoX)

        # Column #2

        if self.systemParms["availablePresets"]:
            self.loadPreset = QtGui.QPushButton("Run", parent=self)
            self.loadPreset.setFixedWidth(50)
            self.loadPreset.move(300,38)
            self.loadPreset.clicked.connect(self.doLoadPreset)
            #self.connect(self.loadPreset, QtCore.SIGNAL("clicked()"), self.doLoadPreset)
            self.presetList = QtGui.QComboBox(parent=self)
            self.presetList.move(180, 39)
            self.presetList.setEditable(True)
            self.presetList.setFixedWidth(125)
            self.presetList.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
            self.presetList.lineEdit().setReadOnly(True)
            self.presetList.addItems(self.systemParms["availablePresets"])
        self.saveImages = QtGui.QCheckBox("Save", parent=self)
        self.saveImages.move(350, 44)

        yPos = 70
        if self.showLaserControl:
            laserLabel = QtGui.QLabel("Laser", parent=self)
            laserLabel.setAlignment(QtCore.Qt.AlignRight)
            laserLabel.move(190, yPos + 5)
            self.laser = QtGui.QSpinBox(parent=self)
            self.laser.setAlignment(QtCore.Qt.AlignCenter)
            self.laser.move(230, yPos)
            self.laser.setFixedWidth(50)
            self.laser.setRange(0, 100)
            self.laser.setSingleStep(5)
            self.laser5 = QtGui.QPushButton("L5", parent=self)
            self.laser5.setFixedWidth(50)
            self.laser5.move(280,yPos-2)
            self.laser10 = QtGui.QPushButton("L10", parent=self)
            self.laser10.setFixedWidth(50)
            self.laser10.move(320,yPos-2)
            self.laser20 = QtGui.QPushButton("L20", parent=self)
            self.laser20.setFixedWidth(50)
            self.laser20.move(360,yPos-2)
            self.laser5.clicked.connect(self.doSetLaser5)
            self.laser10.clicked.connect(self.doSetLaser10)
            self.laser20.clicked.connect(self.doSetLaser20)
            self.laser.valueChanged.connect(self.laserChanged)


        zoomLabel = QtGui.QLabel("Zoom", parent=self)
        zoomLabel.setAlignment(QtCore.Qt.AlignRight)
        zoomLabel.move(235, 105)
        self.zoom = QtGui.QDoubleSpinBox(parent=self)
        self.zoom.setAlignment(QtCore.Qt.AlignCenter)
        self.zoom.move(285, 100)
        self.zoom.setFixedWidth(80)
        self.zoom.setRange(1, 9)
        self.zoom.setSingleStep(0.5)

        pixelClockLabel = QtGui.QLabel("Clock Freq", parent=self)
        pixelClockLabel.setAlignment(QtCore.Qt.AlignRight)
        pixelClockLabel.move(215, 135)
        rangeValues = [ "2.0 MHz", "1.5 MHz", "1.25 MHz",  "1 MHz", "750 kHz", "500 kHz", "250 kHz", "100 kHz"]
        self.pixelClock = QtGui.QComboBox(parent=self)
        self.pixelClock.move(280, 130)
        self.pixelClock.setEditable(True)
        self.pixelClock.setFixedWidth(100)
        self.pixelClock.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
        self.pixelClock.lineEdit().setReadOnly(True)
        self.pixelClock.addItems(rangeValues)
        self._setInitUIvalues()
        self.show()

    def _setInitUIvalues(self):
        # must be a separate function because it is called during start-up and also can be called by typed cmd
        self.xPixels.setValue(512)
        self.yPixels.setValue(400)
        self.chanArange.setCurrentIndex(4)
        self.chanBrange.setCurrentIndex(self.chanBrange.count() - 1)
        if "defaultzoom" in self.systemParms:
            self.zoom.setValue(float(self.systemParms["defaultzoom"]))
        else:
            self.zoom.setValue(2.)
        if self.showLaserControl:
            self.laser.setValue(5)
        self.pixelClock.setCurrentIndex(5)
        if self.showPhotometryControl:
            self.photoMs.setValue(100)
        self.photoSpotsDict = {}
        self.photometryMode = False
        self.lastTestPhotometryXvolts = None
        self.lastTestPhotometryYvolts = None

    def _initParms(self, iniParameters, versionNumber):
        # this routine setups up the minorParameters and initial conditions
        try:
            self.imageSaveFolder = path.expanduser(iniParameters["defaultsavefolder"])
            if not path.exists(self.imageSaveFolder):
                os.makedirs(self.imageSaveFolder)
            minorParameters = self.setupDefaultMinorParameters()
            minorParameters["rasterversion"] = str(versionNumber)
            minorParameters["objective"] = iniParameters["defaultobjective"].upper()
            return minorParameters
        except BaseException as e:
            print(" ")
            print("Problem in RasterGUI in initParms: ")
            traceback.print_exc()
            return None

    def _initAxographWatcher(self, iniParameters):
        try:
            axographFname = path.expanduser(iniParameters["axographfilename"])
            if len(axographFname) > 0:
                if path.exists(axographFname):
                    os.remove(axographFname)
                watchFolder, watchRoot = path.split(axographFname)
                self.axoGraphObserver = Observer()
                self.axoGraphHandler = clsWatchForFile(self, watchRoot, "axograph")
                self.axoGraphObserver.schedule(self.axoGraphHandler, path=watchFolder)
                self.axoGraphObserver.start()
                print("Watching for Axograph files: " + watchFolder)
        except BaseException as e:
            print(" ")
            print("Problem starting RasterGUI: ")
            traceback.print_exc()

class clsWatchForFile(FileSystemEventHandler):
    def __init__(self, callingInstance, fileRootToWatch, funcName):
        super(clsWatchForFile, self).__init__()
        self.callingInstance = callingInstance
        self.fileRoot = fileRootToWatch.lower()
        self.funcName = funcName.lower()

    def on_created(self, event):
        fName = event.src_path
        fRoot = path.split(fName)[1]
        if fRoot.lower() == self.fileRoot:
            time.sleep(0.1)
            with open(fName, "r") as fRemote:
                remoteText = fRemote.read()
            os.remove(fName)
            if self.funcName == "axograph":
                self.callingInstance.processAxographMessage(remoteText)
            else:
                print("Unknown funcName passed to clsWatchForFile: " + self.funcName)
