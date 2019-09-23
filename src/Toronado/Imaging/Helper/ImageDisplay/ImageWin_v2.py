# -*- coding: utf-8 -*-
"""Image window for viewing scanImage TIFF, IMG and ZIP files.

This module represents a core of the Synapse sytem. It defines the clsImageWin class that can
be used repeatedly to generate multiple viewing windows. Each window is self-contained and so can
display the same image in differnet panels.

on 25 May 2016 BWS now flip chan/frame order. New retDict arrays are [channel][frame][each x by y image]
on 29 May 2016 BWS change to retDict[data][A] is [frame][one x by y numpy image]
on 17 Feb 2017 BWS change to enable zipped image files to use .bif extension
on 28 Mar 2017 BWS change from .bif to .gsi for new style renamed zip image files
on 26 Nov 2017 BWS add epilpse ROI for photometry mode
on 9 Dec 2017 BWS added top line GUI command/status line above image
last revised 16 Dec 2017 BWS v1.1

"""

import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.exporters
import os.path as path
import glob
import os
import Imaging.Helper.processImageData as PI
import Imaging.Helper.rasterPlots as RP
import pyperclip
import functools
import datetime

class clsImageWin(QtGui.QMainWindow):
    """The core image window class

    The class is initiated with two variables: a reference to the main window and an integer
    value that is the number assigned to this particular scope window. Typically the first window
    that the Synapse program creates is assigned a winNum of 1. The clsImageWin class needs the reference
    to the calling instance because some functions executed within the scope window need to
    pass information back to parent program.

    """
    def __init__(self, callingInstance, winNum, useNativeGUI=True):
        super(clsImageWin, self).__init__()
        self.callingInstance = callingInstance
        self.thisImageWinNumber = winNum
        self.imageDisplayVersion = 1.01
        self.initUI(winNum)
        self.loadedFileName = None
        self.lastLoadFileFolder = None
        self.allowFileLoad = True
        self.autoAverage = False
        self.postLagTweakPixels = 0
        self.useNativeGUI = useNativeGUI

    # core image display function

    def refreshImageDisplay(self, passDict=None):
        print("Refresh run at " + str(datetime.datetime.now()))
        if not passDict:
            passDict = self.retDict
        if not passDict["data"]:
            print("Data field in passDict is None")
            return None
        if self.displayZoom == 0:
            print("Inside refresh with displayZ = 0")
            self.changeZoom(1) # added 25 May 2016

        if self.autoDisplayLevel:
            self.maxDisplayLevel = self._autoMaxDisplayedValue()
        else:
            self.maxDisplayLevel = int(self.toolMaxScale.value())

        if self.displayColorScheme:
            parts = self.displayColorScheme.lower().strip().split(" ")
            if len(parts) == 2:
                satCode = parts[1]
            else:
                satCode = None
            if parts[0] in ["cubehelix", "helix"]:
                self.curImage.setLookupTable(self.cubehelix())
            elif parts[0] in ["rainbow"]:
                self.curImage.setLookupTable(self.rainbow())
            elif parts[0] in ["white", "w"]:
                self.curImage.setLookupTable(self.singleColor("w", satCode, self.saturationPercentage))
            elif parts[0] in ["default", "normal"]: # white with red above 95%
                self.saturationPercentage = 95.
                print("default LUT size")
                self.curImage.setLookupTable(self.singleColor("w", satCode, self.saturationPercentage))
            elif parts[0] in ["red", "r"]:
                self.curImage.setLookupTable(self.singleColor("r", satCode, self.saturationPercentage))
            elif parts[0] in ["green", "g"]:
                self.curImage.setLookupTable(self.singleColor("g", satCode, self.saturationPercentage))
            elif parts[0] in ["blue", "b"]:
                self.curImage.setLookupTable(self.singleColor("b", satCode, self.saturationPercentage))
            elif parts[0] in ["black", "k"]:
                self.curImage.setLookupTable(self.singleColor("k", satCode, self.saturationPercentage))
            else:
                print("unknown color scheme: " + parts[0])
            if len(parts) >= 2:
                if parts[1] == "redsat":
                    pass
        if 0 < self.saturationPercentage < 100:
            satLevel = int((self.saturationPercentage / 100.) * 2048) # default
            if "hardware" in passDict["parms"]:
                if "maxadcvalue" in passDict["parms"]["hardware"]:
                    satLevel = int((self.saturationPercentage / 100.) * int(passDict["parms"]["hardware"]["maxadcvalue"])) # replace with real value if provided
          # self.curSatMask.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
            tempData = passDict["data"][self.curChannel][self.curFrame]
            tempMask = tempData >= satLevel
           # tempData[tempMask] = 0
            self.curImage.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
            self.curImage.setImage(tempData.astype("float"), levels=(self.minDisplayLevel, self.maxDisplayLevel))
            self.curSatMask.setCompositionMode(QtGui.QPainter.RasterOp_SourceAndDestination)
            self.curSatMask.setLookupTable(self.binaryColorBlackWhite())
            self.curSatMask.setImage(tempMask.astype("int")) # to turn saturated pixels black
            self.curSatColor.setCompositionMode(QtGui.QPainter.RasterOp_SourceOrDestination)
            self.curSatColor.setLookupTable(self.binaryColorRed()) # now can do OR since sat pixels are zeros
            self.curSatColor.setImage(tempMask.astype("int"))
        else:
            self.curImage.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
            self.curSatMask.setCompositionMode(QtGui.QPainter.CompositionMode_Destination) # now mask does nothing
            self.curSatColor.setCompositionMode(QtGui.QPainter.CompositionMode_Destination)
            self.curImage.setImage((passDict["data"][self.curChannel][self.curFrame]).astype("float"), levels=(self.minDisplayLevel, self.maxDisplayLevel))
        self._displayWindowTitle(passDict)
        self.displayCursorInfo()


    def _autoMaxDisplayedValue(self):
        # find max in current image and display that value in toolbar as well as return it to refreshDisplay routine
        newMaxValue = self.retDict["channelMaxValues"][self.curChannel] # max in this particular image
        self.toolMaxScale.setValue(newMaxValue)
        return newMaxValue

    def enableAutoScale(self, newBoolValue, manualSetMax=False):
        # called by toolbar click and text/key commands
        self.autoDisplayLevel = newBoolValue
        if newBoolValue:
            self.topScaleLabel.setText("AutoScale")
        else:
            self.topScaleLabel.setText("  Manual  ")
        if not newBoolValue and manualSetMax:
            # if request was for manual scale set to max possible value
            self.toolMaxScale.setValue(self.retDict["maxPossibleValue"])
        self.refreshImageDisplay()


    def _displayWindowTitle(self, passDict):
        if "imageTitleStr" in passDict:
            tempStr = passDict["imageTitleStr"] # default text if cursor is outside image
            if not self.allowFileLoad:
                tempStr += " ISOLATED"
        else:
            tempStr = "no image title"
        self.win.setWindowTitle(tempStr)

    # image loading routines

    def loadImageStack(self, stackFolder, colorizeDepth=False):
        # added 17 Feb 2017 to match feature in old ImageDisplay program
        tempColor = self.displayColorScheme
        imageList = []
        for oneImageFN in sorted(glob.glob(stackFolder + "/*.*")):
            tempDict = self.getImageDict(oneImageFN)
            if tempDict:
                imageList.append(tempDict)
        if not imageList:
            print("Could not find any image files in folder: " + stackFolder)
            return None
        newDict = imageList[0].copy()
        for oneChanLetter in imageList[0]["channelLetters"]:
            tempStack = []
            for oneImageDict in imageList:
                if len(oneImageDict["data"][oneChanLetter]) == 1:
                    tempStack.append(oneImageDict["data"][oneChanLetter][0]) # single image
                else:
                    tempStack.append(np.mean(np.array(tempDict["data"][oneChanLetter]), 0)) # a movie so average
                    print("Average movie to get one frame xx")
            # tempArray = np.asarray(tempStack) # convert from a list of 2D images into a 3D array
            if not colorizeDepth:
                newDict["data"][oneChanLetter] = np.amax(np.asarray(tempStack), 0, keepdims=True)
            else:
                tempArray = np.asarray(tempStack)
                tempProc = int(2047/(1+len(tempStack))) * (1 + np.argmax(tempArray, 0))
                print(np.shape(tempProc))
                newDict["data"][oneChanLetter] = [tempProc]
                self.displayColorScheme = "rainbow"
        self.retDict = newDict # returned Dict is valid so replace current Dict stored in class instance
        self._agumentDictWithInfoStrings(self.retDict) # add display border information
        self.loadedFileName = "zStack " + path.split(stackFolder)[1]
        if self.curChannelIndex >= len(self.retDict["channelLetters"]):
            self.curChannelIndex = 0 # reset if now impossible to display previous channelIndex
        self.curChannel = self.retDict["channelLetters"][self.curChannelIndex]
        self.curFrame = 0
        self.refreshImageDisplay()
        # self.displayColorScheme = tempColor # restore LUT


    def getImageDict(self, fileName, lagPixelsAdjust=0):
        # refactored 17 Feb 2017 to enable reading multiple types of image files
        fileType = path.splitext(fileName)[1].lower()
        tempDict = None
        if fileType in [".zip", ".gsi"]:
            tempDict = PI.loadRasterZipFile(fileName, lagPixelsAdjust=lagPixelsAdjust, fastMode=False)
        elif fileType in [".img"]:
            print("img load not implemented yet")
        elif fileType in [".tif", ".tiff"]:
            print("tiff load not implemented yet")
        else:
            print("Unknown image read file type")
        return tempDict

    def loadImageFile(self, fileName):
        if self.allowFileLoad:
            tempDict = self.getImageDict(fileName, lagPixelsAdjust=self.postLagTweakPixels)
            if tempDict:
                if self.autoAverage and tempDict["numFrames"] > 1:
                    for oneChanLetter in tempDict["channelLetters"]:
                        tempDict["data"][oneChanLetter] = [np.mean(np.array(tempDict["data"][oneChanLetter]), 0)]
                    tempDict["numFrames"] = 1
                self.retDict = tempDict # returned Dict is valid so replace current Dict stored in class instance
                self._agumentDictWithInfoStrings(self.retDict) # add display border information
                self.loadedFileName = fileName
                if self.curChannelIndex >= len(self.retDict["channelLetters"]):
                    self.curChannelIndex = 0 # reset if now impossible to display previous channelIndex
                self.curChannel = self.retDict["channelLetters"][self.curChannelIndex]
                self.curFrame = 0
                self.refreshImageDisplay()

    def loadImageFileOld(self, fileName):
        # not called anymore
        if self.allowFileLoad:
            fileType = path.splitext(fileName)[1].lower()
            retDictUpdated = False
            if fileType in [".zip", ".bif"]:
                tempDict = PI.loadRasterZipFile(fileName, lagPixelsAdjust=self.postLagTweakPixels, fastMode=False)
                if self.autoAverage and tempDict["numFrames"] > 1:
                    for oneChanLetter in tempDict["channelLetters"]:
                        tempDict["data"][oneChanLetter] = [np.mean(np.array(tempDict["data"][oneChanLetter]), 0)]
                    tempDict["numFrames"] = 1
                if tempDict:
                    self.retDict = tempDict # returned Dict is valid so replace current Dict stored in class instance
                    self._agumentDictWithInfoStrings(self.retDict) # add display border information
                    retDictUpdated = True
            elif fileType in [".img"]:
                print("img load not implemented yet")
            elif fileType in [".tif", ".tiff"]:
                print("tiff load not implemented yet")
            else:
                print("Unknown image read file type")
            if retDictUpdated:
                # one of these load options was successful, so now reset display flags and show new image
                self.loadedFileName = fileName
                if self.curChannelIndex >= len(self.retDict["channelLetters"]):
                    self.curChannelIndex = 0 # reset if now impossible to display previous channelIndex
                self.curChannel = self.retDict["channelLetters"][self.curChannelIndex]
                self.curFrame = 0
                self.refreshImageDisplay()

    def _agumentDictWithInfoStrings(self, retDict):
        # makes changes to passed retDict in-place so no need to return retDict
        retDict["descStr"] = self._generateDescString(retDict)
        retDict["toolTipStr"] = self._generateToolTipString(retDict)
        retDict["imageTitleStr"] = "Image Display - " + retDict["parms"]["objective"]
        if retDict["numFrames"] > 1:
            retDict["imageTitleStr"] += " (" + str(retDict["numFrames"]) + " frames)"
        fileRoot = path.split(retDict["loadedFileName"])[1]
        if fileRoot.lower() != "tempraster.zip":
            retDict["imageTitleStr"] += " - " + fileRoot
       # retDict["imageTitleStr"] += "  Mean " + str(int(np.mean(retDict["data"]["A"][0])))

    def _generateDescString(self, retDict):
        tempStr = str(retDict["Xsize"]) + " x " + str(retDict["Ysize"]) + " by "
        tempStr += str(retDict["numFrames"]) + " frame"
        if retDict["numFrames"] > 1:
            tempStr += "s"
        return tempStr

    def _generateToolTipString(self, retDict):
        try:
            tempStr = "Zoom=" + retDict["parms"]["zoom"]
            if int(retDict["parms"]["bidirectional"]) == 1:
                tempStr += ", bidirect " + retDict["parms"]["bidirends"] + " " + retDict["parms"]["accelfactor"]
            else:
                tempStr += ", unidirect " + retDict["parms"]["linearpercentage"] + "% used"
            if int(retDict["parms"]["rotation"]) != 0:
                tempStr += ", rotation=" + str(retDict["parms"]["rotation"])
        except:
            tempStr = " (no header info)"
        return tempStr

    # core display functions

    def closeThisWindow(self):
        QtCore.QCoreApplication.instance().quit()

    # GUI functions

    def mouseMoved(self, evt):
        if self.retDict:
            self.displayCursorInfo(evt[0])

    def displayCursorInfo(self, posIn=None, passDict=None):
        if not passDict:
            passDict = self.retDict
        if "imageTitleStr" in passDict and "channelMaxValues" in passDict:
            #curLetter = self.retDict["channelLetters"][self.curChannel]
            tempStr = "Channel " + self.curChannel + " (" + self.retDict["channelNames"][self.curChannel] + ")"
            if self.retDict["numFrames"] > 1:
                tempStr += " Frame " + str(self.curFrame)
            if passDict["channelMaxValues"][self.curChannel] > 1945:
                tempStr += " SATURATE" # warn if within 5% of max possible pixel value
            if self.postLagTweakPixels != 0:
                tempStr += " - PostLag " + str(self.postLagTweakPixels) + " pixels"
            if not self.allowFileLoad:
                tempStr += "  ISOLATED"
            if self.autoAverage:
                tempStr += "  autoAverage"
        else:
            tempStr = "no channel max value info"

        displayedPixelInfo = False
        if posIn:
            pos = self.curImage.mapFromScene(posIn)
            if pos.x() >= 0 and pos.x() < passDict["Xsize"]:
                if pos.y() >= 0 and pos.y() < passDict["Ysize"]:
                    curX = int(pos.x())
                    self.lastX = curX
                    curY = int(pos.y())
                    self.lastY = curY
                    pixelValue = passDict["data"][self.curChannel][self.curFrame][curX, curY]
                    tempStr += " pixel at " + str(curX) + "  " + str(curY) + " = " + str(10 * int(pixelValue/10))
                    self.lastPos = posIn
                    displayedPixelInfo = True

            if not displayedPixelInfo:
                tempStr = ""
                if "toolTipStr" in passDict:
                    tempStr += " " + passDict["toolTipStr"]
                else:
                    tempStr += " (no tool tip info)"
                tempStr += "; Display Mag " + str(self.displayZoom) + "X"
                if self.displayColorScheme:
                    tempStr += " (" + self.displayColorScheme
                    if " " in self.displayColorScheme:
                        tempStr += " with " + str(int(self.saturationPercentage)) + "% max"
                    tempStr += ")"

        self.staticStatusText = tempStr
        self.win.statusBar().showMessage(self.staticStatusText)
        return True

        if not posIn:
            posIn = self.lastPos
        if posIn:
            pos = self.curImage.mapFromScene(posIn)
            self.lastPos = posIn
            infoQuad = -1
            if pos.x() >= 0 and pos.x() < passDict["Xsize"]:
                if pos.y() >= 0 and pos.y() < passDict["Ysize"]:
                    curX = int(pos.x())
                    self.lastX = curX
                    curY = int(pos.y())
                    self.lastY = curY
                    pixelValue = passDict["data"][self.curChannel][self.curFrame][curX, curY]
                    tempStr = str(10 * int(pixelValue/10)) + " at " + str(curX) + " x " + str(curY) + " (chan "
                    tempStr += str(self.curChannel) + " " + passDict["channelNames"][self.curChannel] + ", frame " + str(self.curFrame) + ")"
                    if "channelMaxValues" in passDict:
                        tempStr += "  max " + str(passDict["channelMaxValues"][self.curChannel])
                else:
                    if pos.y() < 0:
                       infoQuad = 0 # bottom
                    elif pos.y() >= passDict["Ysize"]:
                        infoQuad = 1 # top
            else:
                if pos.x() < 0:
                    infoQuad = 2 # left
                elif pos.x() >= passDict["Xsize"]:
                    infoQuad = 3 # right
            if self.cursorMode:
                if infoQuad >= 0:
                    if infoQuad == 0:
                        if "loadedFileName" in passDict:
                            tempStr = passDict["loadedFileName"]
                        else:
                            tempStr = "no loaded file info"
                    elif infoQuad == 1:
                        if "imageTitleStr" in passDict and "channelMaxValues" in passDict:
                            tempStr = passDict["imageTitleStr"]
                            if passDict["channelMaxValues"][self.curChannel] > 1945:
                                tempStr += " SATURATE" # warn if within 5% of max possible pixel value
                            if self.postLagTweakPixels != 0:
                                tempStr += " - PostLag " + str(self.postLagTweakPixels) + " pixels"
                            if not self.allowFileLoad:
                                tempStr += "  ISOLATED"
                            if self.autoAverage:
                                tempStr += "  autoAverage"
                        else:
                            tempStr = "no channel max value info"
                    elif infoQuad == 2 and self.maxDisplayLevel:
                        tempStr = "Display from " + str(self.minDisplayLevel) + " to " + str(self.maxDisplayLevel)
                        if self.autoDisplayLevel:
                            tempStr += " autoLevel"
                        else:
                            tempStr += " manual"
                        tempStr += "; mag " + str(self.displayZoom) + "X"
                        if self.displayColorScheme:
                            tempStr += " (" + self.displayColorScheme
                            if " " in self.displayColorScheme:
                                tempStr += " with " + str(int(self.saturationPercentage)) + "% max"
                            tempStr += ")"
                    elif infoQuad == 3:
                        if "toolTipStr" in passDict:
                            tempStr = passDict["toolTipStr"]
                        else:
                            tempStr = "no tool tip info"
                    else:
                        print("error in computing position in border region")
                # self.mw.setWindowTitle(tempStr) xx

    def keyPressEvent(self, evt):
        modifiers = QtGui.QApplication.keyboardModifiers()
        if evt.key() == QtCore.Qt.Key_L:
            if self.allowFileLoad:
                self.loadImageFileviaPopUp()
            else:
                print("File loading is disabled in ISOLATED mode; enter 'hook' to re-enable.")
        if evt.key() == QtCore.Qt.Key_Space:
            self.runGenericCommandGUI()
        if evt.key() == QtCore.Qt.Key_QuoteLeft and self.retDict:
            self.changeZoom(0.5)
        if evt.key() == QtCore.Qt.Key_1 and self.retDict:
            self.changeZoom(1)
        if evt.key() == QtCore.Qt.Key_2 and self.retDict:
            self.changeZoom(2)
        if evt.key() == QtCore.Qt.Key_3 and self.retDict:
            self.changeZoom(3)
        if evt.key() == QtCore.Qt.Key_B and self.retDict:
            # B for ROI Box
            self.toggleCursorMode()
        if evt.key() == QtCore.Qt.Key_C and self.retDict:
            # toggle which channel is displayed
            self.curChannelIndex += 1
            if self.curChannelIndex > len(self.retDict["channelLetters"]) - 1:
                self.curChannelIndex = 0 # reset back to 0 if exceeded the number of extracted channels
            self.curChannel = self.retDict["channelLetters"][self.curChannelIndex]
            self.refreshImageDisplay()
        if evt.key() == QtCore.Qt.Key_Right and self.retDict:
            self.curFrame += 1
            if self.curFrame >= self.retDict["numFrames"]:
                self.curFrame = self.retDict["numFrames"] - 1 # last possible index
            self.refreshImageDisplay()
        if evt.key() == QtCore.Qt.Key_Left and self.retDict:
            self.curFrame -= 1
            if self.curFrame < 0:
                self.curFrame = 0
            self.refreshImageDisplay()
        if evt.key() == QtCore.Qt.Key_A and self.retDict:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.minDisplayLevel = 0 # reset min level if added Shift key
            self.autoDisplayLevel = True
            self.refreshImageDisplay()
        if evt.key() == QtCore.Qt.Key_Up and self.retDict:
            self.autoDisplayLevel = False
            span = self.maxDisplayLevel - self.minDisplayLevel
            self.maxDisplayLevel = int(self.minDisplayLevel + (1.25 * span))
            if self.maxDisplayLevel >= 2048:
                self.maxDisplayLevel = 2048
            self.refreshImageDisplay()
        if evt.key() == QtCore.Qt.Key_PageUp and self.retDict:
                self.minDisplayLevel = self.minDisplayLevel + 10
                self.refreshImageDisplay()
        if evt.key() == QtCore.Qt.Key_Down and self.retDict:
            self.autoDisplayLevel = False
            span = self.maxDisplayLevel - self.minDisplayLevel
            self.maxDisplayLevel = int(self.minDisplayLevel + (0.75 * span))
            self.refreshImageDisplay()
        if evt.key() == QtCore.Qt.Key_PageDown and self.retDict:
            self.minDisplayLevel = self.minDisplayLevel - 10
            if self.minDisplayLevel < 0:
                self.minDisplayLevel = 0
        if evt.key() == QtCore.Qt.Key_R and self.retDict:
            self.refreshImageDisplay()
        if evt.key() == QtCore.Qt.Key_S and self.retDict:
            self.saveCurrent()
        if evt.key() == QtCore.Qt.Key_W and self.retDict:
            RP.plotLag(self.retDict, self.postLagTweakPixels)
        if evt.key() == QtCore.Qt.Key_K:
            self.loadImageStackviaPopUp()
        if evt.key() == QtCore.Qt.Key_E and self.retDict:
            self.exportCurPosImageWin()
        if evt.key() == QtCore.Qt.Key_Q and self.retDict:
            self.exportCurPosImageWin(testMode=True)



    def exportCurPosImageWin(self, testMode=False):
        requiredKeys = ["centerxvolts", "centeryvolts", "zoomasvolts", "pixelus"]
        okayToExport = True
        for testKey in requiredKeys:
            if testKey not in self.retDict["parms"]:
                okayToExport = False
        if not okayToExport:
            print("Cannot export spot location because required information not saved.")
            return False
        formatStr = "{:.4f}"
        if self.lastX >= 0 and self.lastY >= 0:
            spotName ="Default Spot"
            if not testMode:
                spotName = self.msgBox("Enter spot name", "Center: " + str(self.lastX) + " by "
                                       + str(self.lastY) + " pixels")
            # call has to go up to callingThread, then Toronado and finally to RasterGUI
            spotXvolts, spotYvolts = self._calculateSpotVolts(self.lastX, self.lastY, self.retDict)
            self.callingInstance.exportCursorPos(spotXvolts, spotYvolts, spotName, testMode=testMode)
            print("Exported spot: " + spotName + " with testMode = " + str(testMode))
            return True
        else:
            print("no cursor data available")
            return False

    def _calculateSpotVolts(self, curPixelX, curPixelY, mainDict):
        # this routine will return the estimated X and Y cmd voltage that corresponds to the indicated cursor pos
        xSize = mainDict["Xsize"]
        fractionalX = (xSize - curPixelX) / xSize
        ySize = mainDict["Ysize"]
        fractionalY = (ySize - curPixelY) / ySize
        centerX = float(mainDict["parms"]["centerxvolts"])
        centerY = float(mainDict["parms"]["centeryvolts"])
        zoomAsVolts = float(mainDict["parms"]["zoomasvolts"])
        pixelUs = float(mainDict["parms"]["pixelus"])
        xVoltExt = zoomAsVolts
        retVoltsX = centerX + (fractionalX * xVoltExt) - (xVoltExt / 2.0)
        yVoltExt = zoomAsVolts * (ySize / xSize)
        retVoltsY = (fractionalY * yVoltExt) - (yVoltExt / 2.0)
        #print("Inside _calcSpotVolts: " + str(retVoltsX) + " " + str(retVoltsY))
        return retVoltsX, retVoltsY

    def changeZoom(self, newDisplayZoom):
        print("New requested zoom: " + str(newDisplayZoom))
        allowedZooms = [0.25, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
        if newDisplayZoom in allowedZooms:
            # self.mw.resize(int(newDisplayZoom * self.retDict["Xsize"]), 100 + int(newDisplayZoom * self.retDict["Ysize"]))
            self.displayZoom = float(newDisplayZoom)
        else:
            print("Allowed display zooms: " + str(allowedZooms))

    def togglePhotometryMode(self):
        if not self.rois:
            self.rois = []
        self.rois.append(pg.EllipseROI([100, 150], [30, 20], pen=(7 , 3)) )
        for roi in self.rois:
           # roi.sigRegionChanged.connect(self.updateROIs)
            self.view.addItem(roi)
        #self.updateROIs(self.rois[-1])

    def toggleCursorMode(self):
        if self.cursorMode:
            # was crossCursor so switch to ROI mode xx obsolete?
            if not self.rois:
                self.rois = []
                self.rois.append(pg.RectROI([100, 150], [20, 20], pen=(0,9)))
            for roi in self.rois:
                roi.sigRegionChanged.connect(self.updateROIs)
                self.view.addItem(roi)
            self.view.setCursor(QtCore.Qt.ArrowCursor)
            self.cursorMode = False
            self.updateROIs(self.rois[-1])
        else:
            # ROI mode so switch to crossCursor mode
            for roi in self.rois:
                self.view.removeItem(roi)
            self.view.setCursor(QtCore.Qt.CrossCursor)
            self.cursorMode = True


    def dictToStringList(self, passDict, fileHandle=None, printNow=False):
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

    def runGenericCommandGUI(self, defaultCommand=""):
        newCmd = self.msgBox("Enter ImageWindow command", "", "")
        if newCmd:
            self.processGenericScopeCommand(newCmd, forceImageRefresh=True)
            self.commandHistory = newCmd

    def processGenericScopeCommand(self, newCmd, forceImageRefresh=False):
        # main routine for processing all text commands
        falseStrings = ["none", "off", "false", "no", "0"]
        parts = newCmd.strip().split("|")
        for oneCmd in parts:
            cleanCmd = oneCmd.strip()
            if "=" in cleanCmd:
                subparts = cleanCmd.split("=")
                # print(len(subparts))
            else:
                subparts = cleanCmd.split(" ")
            actualCommand = subparts[0].lower()
            textAfterCmd = cleanCmd[len(actualCommand):].strip()
            if actualCommand in ["displaymax", "max"]:
                self.maxDisplayLevel = int(subparts[1])
                self.autoDisplayLevel = False
                self.refreshImageDisplay()
            elif actualCommand in ["displaymin", "min"]:
                self.minDisplayLevel = int(subparts[1])
                self.refreshImageDisplay()
            elif actualCommand in ["color", "colorscheme", "lut"]:
                if "=" in cleanCmd:
                    self.displayColorScheme = cleanCmd.split("=")[1]
                else:
                    self.displayColorScheme = textAfterCmd
                self.refreshImageDisplay()
            elif actualCommand in ["saturationpercentage", "saturationpercent", "satpercent", "sat"]:
                tempV = float(subparts[1])
                if tempV < 0:
                    print("Negative saturation percentages are not allowed.")
                    return None
                elif tempV == 0:
                    self.saturationPercentage = 0
                elif tempV <= 1.:
                    self.saturationPercentage = 100. * tempV
                else:
                    self.saturationPercentage = tempV
                self.refreshImageDisplay()
            elif actualCommand in ["togglecursor", "changecursor", "cur"]:
                self.toggleCursorMode()
            elif actualCommand in ["save", "saveimage", "saveframe", "saveseries"]:
                if len(subparts) == 2:
                    self.saveCurrent(saveFormat=subparts[1].strip(), wholeMovie=False)
                else:
                    print("You need to specify a file type to save the image to (eg, mat, pickle, jpeg, pdf)")
            elif actualCommand in ["savemovie", "savestack"]:
                if len(subparts) == 2:
                    self.saveCurrent(saveFormat=subparts[1].strip(), wholeMovie=True)
                else:
                    print("You need to specify a file type to save the image stack to (eg, mat, pickle)")
            elif actualCommand in ["workingdirectory", "workingfolder", "curfolder", "curdir", "setdir", "setpath", "curpath", "path"]:
                if len(subparts) == 1:
                    if self.curWorkingFolder:
                        print("Working folder: " + self.curWorkingFolder)
                    else:
                        print("Working folder has not been set yet.")
                else:
                    if "~" in textAfterCmd:
                        textAfterCmd = textAfterCmd.replace("~", path.expanduser("~"))
                    if path.exists(textAfterCmd):
                        self.curWorkingFolder = textAfterCmd
                        print("Working folder changed to: " + self.curWorkingFolder)
                    else:
                        print("Text after command is not a valid path: " + textAfterCmd)
            elif actualCommand in ["displayzoom", "zoom", "z"]:
                if len(subparts) == 2:
                    self.changeZoom(float(subparts[1]))
                else:
                    print("Zoom parameter (eg, 0.5 or 2) needed to change display zoom")
            elif actualCommand in ["lag", "postlag", "lagtweak"]:
                if len(subparts) == 2:
                    self.postLagTweakPixels = int(subparts[1])
                    self.loadImageFile(self.loadedFileName) # reload zip file to change lag decoding
                    print("Refreshed display to reflect adjusted lag of " + str(self.postLagTweakPixels) + " pixels.")
            elif actualCommand in ["dump", "dumpparms", "dumpparameters"]:
                print(" ")
                print(" Dump of stored image parameters:")
                self.dictToStringList(self.retDict["parms"], printNow=True)
            elif actualCommand in ["unhook", "nolisten"]:
                self.allowFileLoad = False
            elif actualCommand in ["hook", "listen"]:
                self.allowFileLoad = True
            elif actualCommand in ["colorizedepth", "colordepth", "depth"]:
                self.colorizeDepth = subparts[1].lower() not in falseStrings
                print("Set colorizeDepth to " + str(self.colorizeDepth))
            elif actualCommand in ["autoaverage", "average", "ave"]:
                if int(subparts[1]) == 1:
                    self.autoAverage = True
                    print("Auto-average of movies is on.")
                    self.loadImageFile(self.loadedFileName)
                else:
                    self.autoAverage = False
                    print("Disabled auto-average of movie stacks")
                    self.loadImageFile(self.loadedFileName)
            else:
                print("Unknown command: " + actualCommand)

    def loadImageFileviaPopUp(self):
        if self.lastLoadFileFolder:
            startFolder = self.lastLoadFileFolder
        else:
            startFolder = path.expanduser("~") + "/Dropbox/Lab Data"
        options = QtGui.QFileDialog.Options()
        if not self.useNativeGUI:
            options |= QtGui.QFileDialog.DontUseNativeDialog
        fileName = QtGui.QFileDialog.getOpenFileName(self, "Please select an image file to load.",
                                                     startFolder, options=options)[0]
        if fileName:
            print("Filename: " + fileName)
            if path.splitext(fileName)[1].lower() in [".tif", ".tiff", ".zip", ".img", ".gsi"]:
                self.lastLoadFileFolder = path.split(fileName)[0]
                self.loadImageFile(fileName)
            else:
                print("Unknown type of Image file: " + fileName)

    def loadImageStackviaPopUp(self):
        startFolder = path.expanduser("~") + "/Dropbox/Lab Data"
        folderName = str(QtGui.QFileDialog.getExistingDirectory(self, "Select folder containing zStack", startFolder))
        if folderName:
            self.loadImageStack(folderName, colorizeDepth=self.colorizeDepth)

    def saveCurrent(self, saveFormat="JPEG", wholeMovie=False):
        codeStr = saveFormat.lower()
        if codeStr[0] == ".":
            codeStr = codeStr[1:] # remove leading . if included
        if codeStr in ["pickle", "pk", "p"]:
            newFormat = "pk"
        elif codeStr in ["mat", "matlab", "m"]:
            newFormat = "mat"
       # elif codeStr in ["jpeg", "jpg"]:
         #   newFormat = "jpeg"
        elif codeStr in ["bin", "binary", "raw"]:
            newFormat = "bin"
        elif codeStr in ["tif", "tiff"]:
            newFormat = "tif"
        elif codeStr in ["png"]:
            newFormat = "png"
        else:
            newFormat = None
            print("Unknown saveFormat type.")
        if newFormat:
            if wholeMovie:
                frameVar = -1
            else:
                frameVar = self.curFrame
            if newFormat in ["jpg", "png"]:
                # done locally in ImageWindow based on current display settings
                finalName = path.splitext(self.loadedFileName)[0] + "." + newFormat
                exporter = pg.exporters.ImageExporter(self.curImage)
                exporter.export(finalName)
                print("Saved " + finalName)
            else:
                # done with save method within PI module since saves raw image data
                PI.saveProcessedImageData(self.retDict, self.loadedFileName, newFormat, frameVar)


    def cubehelix(self, gamma=1.0, s=0.5, r=-1.5, h=1.0):
        def get_color_function(p0, p1):
            def color(x):
                xg = x ** gamma
                a = h * xg * (1 - xg) / 2
                phi = 2 * np.pi * (s / 3 + r * x)
                return xg + a * (p0 * np.cos(phi) + p1 * np.sin(phi))
            return color

        array = np.empty((256, 3))
        abytes = np.arange(0, 1, 1/256.)
        array[:, 0] = get_color_function(-0.14861, 1.78277)(abytes) * 255
        array[:, 1] = get_color_function(-0.29227, -0.90649)(abytes) * 255
        array[:, 2] = get_color_function(1.97294, 0.0)(abytes) * 255
        return array

    def binaryColorRed(self):
        tableSize = 2
        array = np.zeros((tableSize,3))
        array[1,0] = 255
        return array

    def binaryColorBlackWhite(self):
        tableSize = 2
        array = np.zeros((tableSize,3))
        array[0,0] = 255
        array[0,1] = 255
        array[0,2] = 255
        return array

    def singleColor(self, colorCode="w", satCode=None, saturationPercent=95.):
        tableSize = 256
        array = np.zeros((tableSize,3))
        abytes = np.arange(0, tableSize)
        colorCodeFixed = colorCode.lower()
        if colorCodeFixed =="k": # for Black
            abytes = sorted(abytes, reverse=True)
        if colorCodeFixed in ["w", "k"]:
            array[:, 0] = abytes
            array[:, 1] = abytes
            array[:, 2] = abytes
        elif colorCodeFixed == "r":
            array[:, 0] = abytes
        elif colorCodeFixed == "g":
            array[:, 1] = abytes
        elif colorCodeFixed == "b":
            array[:, 2] = abytes
        else:
            print("Unkown color code in SingleColor: " + colorCode) # return white
            array[:, 0] = abytes
            array[:, 1] = abytes
            array[:, 2] = abytes

        if False == True: # To disable--was satCode
            satCodeFixed = satCode.lower()
            satStart = int((saturationPercent/100.) * 256)
            if satCodeFixed == "none":
                pass
            if satCodeFixed == "r":
                for ii in range(255,256): # was (statStart,255)
                    array[ii, 0] = 255
                    array[ii, 1] = 0
                    array[ii, 2] = 0
            elif satCodeFixed == "g":
                for ii in range(255,256):
                    array[ii, 0] = 0
                    array[ii, 1] = 255
                    array[ii, 2] = 0
            elif satCodeFixed == "b":
                for ii in range(255,256):
                    array[ii, 0] = 0
                    array[ii, 1] = 0
                    array[ii, 2] = 255
            else:
                print("Unknown saturation code: " + satCode)
        return array

    def rainbow(self):
        array = np.empty((256, 3))
        abytes = np.arange(0, 1, 0.00390625)
        array[:, 0] = np.abs(2 * abytes - 0.5) * 255
        array[:, 1] = np.sin(abytes * np.pi) * 255
        array[:, 2] = np.cos(abytes * np.pi / 2) * 255
        return array

    def lukeColors(self):
        lut = np.zeros((256,3), dtype=np.ubyte)
        lut[:128,0] = np.arange(0,255,2)
        lut[128:,0] = 255
        lut[:,1] = np.arange(255)
        return lut

    def updateROIs(self, roi):
        pass
       # self.mw.setWindowTitle(str(np.mean(roi.getArrayRegion(self.retDict["data"][0][0], self.curImage)))) xx

    def msgBox(self, windowTitle, labelText, defaultText = None):
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

    def doCloseShutter(self):
        print("got to closeShutter")

    def intializeMainSettings(self):
        self.commandHistory = ""
        self.curChannel = None
        self.curChannelIndex = 0
        self.curFrame = 0
        self.curWorkingFolder = None
        self.cursorMode = True # False for moving ROI mode
        self.retDict = None
        self.tableau20 = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40),
            (148, 103, 189), (140, 86, 75), (227, 119, 194), (127, 127, 127),
            (188, 189, 34), (23, 190, 207), (174, 199, 232), (255, 187, 120),
            (152, 223, 138), (255, 152, 150),  (197, 176, 213),
            (197, 176, 213), (196, 156, 148), (247, 182, 210), (199, 199, 199),
            (219, 219, 141), (158, 218, 229)]
        self.tableau20Norm = [(31/255, 119/255, 180/255), (255/255, 127/255, 14/255), (44/255, 160/255, 44/255), (214/255, 39/255, 40/255),
            (148/255, 103/255, 189/255), (140/255, 86/255, 75/255), (227/255, 119/255, 194/255), (127/255, 127/255, 127/255),
            (188/255, 189/255, 34/255), (23/255, 190/255, 207/255), (174/255, 199/255, 232/255), (255/255, 187/255, 120/255),
            (152/255, 223/255, 138/255), (255/255, 152/255, 150/255),  (197/255, 176/255, 213/255),
            (197/255, 176/255, 213/255), (196/255, 156/255, 148/255), (247/255, 182/255, 210/255), (199/255, 199/255, 199/255),
            (219/255, 219/255, 141/255), (158/255, 218/255, 229/255)]
        self.tableau20evenOdd = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
             (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
             (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
             (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
             (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]

    def initUI(self, winNum):
        self.intializeMainSettings()

        self.win = QtGui.QMainWindow()
        self.win.setGeometry(490, 320, 800, 900)
        self.GUIlockOut = True

        self.GLW = pg.GraphicsLayoutWidget()

        self.lastPos = None
        self.view = self.GLW.addViewBox(enableMouse=False)
        self.view.setCursor(QtCore.Qt.CrossCursor)
        self.view.setAspectLocked(True)
        self.curImage = pg.ImageItem(border="w")
        self.curSatMask = pg.ImageItem(border= "w") # xx
        self.curSatColor = pg.ImageItem(border="w")
        self.view.addItem(self.curImage)
        self.view.addItem(self.curSatMask) # xx
        self.view.addItem(self.curSatColor)
        self.GLW.keyPressEvent = self.keyPressEvent
        self.proxy = pg.SignalProxy(self.view.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.rois = []
        self.minDisplayLevel = 0
        self.maxDisplayLevel = 2048
        self.lastMaxPossibleDisplayLevel = 2048
        self.autoDisplayLevel = True
        self.displayZoom = 1. # changed 25 May 2016 now need to check on refresh
        self.displayColorScheme = "w r"
        self.colorizeDepth = False
        self.filterString = ""
        self.saturationPercentage = 95.

        self.win.setCentralWidget(self.GLW)
        self.win.setWindowTitle("Image Display (window " + str(winNum) + "; version " + str(self.imageDisplayVersion) + ")")

        buttonSize = QtCore.QSize(70,35)
        cmdSize = QtCore.QSize(70, 25)
        tb = QtGui.QToolBar()

        self.toolLoad = QtGui.QPushButton("Load", parent=self)
        self.toolLoad.setFixedWidth(70)
        self.toolLoad.clicked.connect(self.loadImageFileviaPopUp)
        tb.addWidget(self.toolLoad)

        self.topScaleLabel = QtGui.QLabel("AutoScale", parent=self)
        tb.addWidget(self.topScaleLabel)
        self.toolMaxScale = QtGui.QSpinBox(parent=self)
        self.toolMaxScale.setAlignment(QtCore.Qt.AlignHCenter)
        self.toolMaxScale.setFixedSize(cmdSize)
        self.toolMaxScale.setRange(-65600, 65600)
        self.toolMaxScale.setSingleStep(50)
        tb.addWidget(self.toolMaxScale)
        self.toolUpdateDisplay = QtGui.QPushButton("Update", parent=self)
        self.toolUpdateDisplay.setFixedWidth(70)
        self.toolUpdateDisplay.clicked.connect(functools.partial(self.enableAutoScale, False)) # triggers call to refreshDisplay
        tb.addWidget(self.toolUpdateDisplay)
        self.toolMaxDisplay = QtGui.QPushButton("Max", parent=self)
        self.toolMaxDisplay.setFixedWidth(50)
        self.toolMaxDisplay.clicked.connect(functools.partial(self.enableAutoScale, False, True)) # triggers call to refreshDisplay
        tb.addWidget(self.toolMaxDisplay)
        self.toolAutoDisplay = QtGui.QPushButton("Auto", parent=self)
        self.toolAutoDisplay.setFixedWidth(50)
        self.toolAutoDisplay.clicked.connect(functools.partial(self.enableAutoScale, True))
        tb.addWidget(self.toolAutoDisplay)

        zoomLabel = QtGui.QLabel("Mag", parent=self)
        tb.addWidget(zoomLabel)
        self.toolZoom1 = QtGui.QPushButton("1X", parent=self)
        self.toolZoom1.setFixedWidth(50)
        self.toolZoom1.clicked.connect(functools.partial(self.changeZoom, 1))
        tb.addWidget(self.toolZoom1)
        self.toolZoom2 = QtGui.QPushButton("2X", parent=self)
        self.toolZoom2.setFixedWidth(50)
        self.toolZoom2.clicked.connect(functools.partial(self.changeZoom, 2))
        tb.addWidget(self.toolZoom2)

        cmdLabel = QtGui.QLabel("  ", parent=self)
        tb.addWidget(cmdLabel)
        self.toolCmd = QtGui.QPushButton("Cmd", parent=self)
        self.toolCmd.setFixedWidth(70)
        self.toolCmd.clicked.connect(self.runGenericCommandGUI)
        tb.addWidget(self.toolCmd)

        self.win.addToolBar(tb)

        self.defaultStatus = "Preparing ..."
        self.win.statusBar().showMessage(self.defaultStatus)

        self.GUIlockOut = False
        self.win.show()

