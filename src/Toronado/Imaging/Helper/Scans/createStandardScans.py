# -*- coding: utf-8 -*-
""" createScanWaveforms.py

This routine calls either the standard sawtooth or bidirectional scan routines or specialized ones.
  The entry routine returns a Dict that will become the [Derived] section of the ImageDescription.txt file.
This scan generation routine is required for the default modes in Toronado (ie, do not delete this file)

last revised 1 Apr 2017 BWS

"""

import sys, os, math
import os.path as path
import numpy as np

def standard(allParms, newParms):
    localInputFolder = allParms["Interface"]["localInputFolder"]
    pixelsX = int(allParms["Major"]["Xsize"])
    pixelsY = int(allParms["Major"]["Ysize"])
    numFrames = int(allParms["Interface"]["numFrames"])
    pixelUs = float(allParms["Major"]["pixelUs"])
    voltsX = float(newParms["zoomAsVolts"])
    voltsY = voltsX * (pixelsY / pixelsX)
    lagUs = float(newParms["lagUs"])
    lagPixels = int(newParms["lagPixels"])
    tempAccel = (1. / float(allParms["Minor"]["accelfactor"]) * pixelUs * pixelUs) / 1000.0
    accelAdjustFactor = 1. / (4. * float(allParms["System"]["scancmdattenuation"]))
    # this factor added to enable system to work with scanners that do not attenuate inputs
    # typical system use 1:4 attenuations, so this factor will be 1; on 1:1 systems, this
    # factor will be 0.25, reducing the maxAccelAdjusted and increasing the turnLength
    maxAccelAdjusted = tempAccel * accelAdjustFactor
    newParms["voltsX"] = str(voltsX)
    newParms["voltsY"] = str(voltsY)
    newParms["tempAccel"] = str(tempAccel)
    newParms["maxAccelAdjusted"] = str(maxAccelAdjusted)
    newParms["statusMsg"] = ""
    
    # create row pair
    centerX = float(allParms["Minor"]["centerxvolts"])
    halfVoltsX = voltsX / 2.0
    linearPortion = np.linspace(centerX + halfVoltsX, centerX - halfVoltsX, pixelsX)
    linearPortionRev = linearPortion[::-1] # reversed view onto original array
    if int(allParms["Minor"]["bidirectional"]) == 1:
        # bidirectional scan modes
        bidirectionalMode = allParms["Minor"]["bidirends"].lower()
        if bidirectionalMode == "point":
            rowPair = np.concatenate((linearPortion, linearPortionRev))
            turnLength = 0
            newParms["statusMsg"] = "Standard bidir/point (TL 0"
        elif bidirectionalMode == "flat":
            turnLength = 100
            turnAround = linearPortion[0] * np.ones(turnLength)
            turnAroundRev = linearPortionRev[0] * np.ones(turnLength)
            rowPair = np.concatenate((turnAround, linearPortion, turnAroundRev, linearPortionRev))
            newParms["statusMsg"] = "Standard bidir/flat (TL " + str(turnLength) 
        elif bidirectionalMode == "square":
            turnLength = 100
            tempLinear = np.ones(np.size(linearPortion))
            turnAround = linearPortion[0] * np.ones(turnLength)
            turnAroundRev = linearPortionRev[0] * np.ones(turnLength)
            rowPair = np.concatenate((turnAround, linearPortion[0] * tempLinear,
                                     turnAroundRev, linearPortionRev[0] * tempLinear))
            newParms["statusMsg"] = "Standard bidir/square (TL " + str(turnLength) 
        elif bidirectionalMode == "parabolic":
            Factor = 0.5 * maxAccelAdjusted
            lineSlope = voltsX / pixelsX
            endPoint = lineSlope / (2 * Factor)
            tempVec = np.arange(int(-1 * endPoint), int(endPoint + 1))
            endPortion = -1.0 * Factor * tempVec * tempVec
            endPortion = endPortion - endPortion[0]
            turnLength = len(endPortion) - pixelsX
            if turnLength > 0:
                turnAround = linearPortion[0] + endPortion[1:-1]
                turnAroundRev = linearPortionRev[0] - endPortion[1:-1]
                rowPair = np.concatenate((turnAround, linearPortion, turnAroundRev, linearPortionRev))
            else:
                rowPair = np.concatenate((linearPortion, linearPortionRev))
                turnLength = 0
            newParms["statusMsg"] = "Standard bidir/parabolic (TL " + str(turnLength) + ", F " + allParms["Minor"]["accelfactor"] 
        elif bidirectionalMode == "maxaccel":
            Factor = maxAccelAdjusted
            lineSlope = voltsX / pixelsX
            turnLength = int(2 * lineSlope / Factor) + 1
            if turnLength > 0:
                accelData = np.concatenate((-1.0 * Factor * np.ones(turnLength), np.zeros(pixelsX),
                                           Factor * np.ones(turnLength), np.zeros(pixelsX)))
                velocityData = np.cumsum(accelData)
                velocityData = velocityData - np.mean(velocityData)
                rowPair = np.cumsum(velocityData)
                rowPair = rowPair - np.mean(rowPair) + centerX
            else:
                rowPair = np.concatenate((linearPortion, linearPortionRev))
                turnLength = 0
            newParms["statusMsg"] = "Standard bidir/maxAccel (TL " + str(turnLength) + ", F " + str(allParms["Minor"]["accelfactor"])
        else:
            print("Error - unknown bidirectional scan mode: " + bidirectionalMode)
            return False
    else:
        # unidirectional scanning
        turnLength = int(pixelsX * (100.0 / float(allParms["Minor"]["linearpercentage"]))) - pixelsX
        if turnLength < 0 or turnLength > pixelsX:
            print("Error - incorrect linearPercentage value: " + float(minorParms["linearpercentage"]))
            return False
        turnAround = np.linspace(centerX - halfVoltsX, centerX + halfVoltsX, turnLength)
        rowPair = np.concatenate((turnAround, linearPortion, turnAround, linearPortion))
        newParms["statusMsg"] = "Standard unidir (TL " + str(turnLength) + ", linear " + allParms["Minor"]["linearpercentage"] + ", "
    newParms["turnLength"] = str(turnLength) # extra pixels added to Xsize on each line
    newParms["rowPairPoints"] = str(len(rowPair)) # 2 x Xsize plus 2 x turnLength
    newParms["rowPairMs"] = str((pixelUs * len(rowPair)) / 1000.)
    newParms["saturatedRowPair"] = str(max(rowPair) > 9.996 or min(rowPair) < -9.996)
    if max(rowPair) > 9.996:
        rowPair[rowPair > 9.996] = 9.996
    if min(rowPair) < -9.996:
        rowPair[rowPair < -9.996] = -9.996
    newParms["rowPairVoltSpan"] = str(max(rowPair) - min(rowPair))
    if int(allParms["Minor"]["saverowpair"]) == 1:
        newParms["rowPairFileName"] = allParms["System"]["tempFolder"] + "/RowPair_float64.bin"
        rowPair.tofile(newParms["rowPairFileName"])
    numFramePixels = int(pixelsY * (pixelsX + turnLength))
    newParms["numFramePixels"] = str(numFramePixels)
    frameMs = numFramePixels * pixelUs / 1000.
    newParms["estimatedFrameMs"] = str(frameMs)
    newParms["estimatedTotalSeconds"] = str(numFrames * (float(newParms["estimatedFrameMs"]) / 1000.))
    newParms["statusMsg"] += ", Frame " + str(int(frameMs)) + " ms)"
    
    # generate first frame
    mXcenter = float(allParms["minor"]["centerXvolts"])
    scanPointsX = np.tile(rowPair, int(pixelsY/2))
    halfVoltsY = voltsY / 2.0
    mYcenter = float(allParms["minor"]["centerYvolts"])
    scanPointsY = np.repeat(np.linspace(mYcenter + halfVoltsY, mYcenter - halfVoltsY, pixelsY),
                         pixelsX + turnLength)

    # rotate frame if needed
    if int(allParms["Minor"]["rotation"]) != 0:
        rot = np.radians(float(allParms["Major"]["rotation"]))
        mSinRot = math.sin(rot)
        mCosRot = math.cos(rot)
        for ii in range(len(scanPointsX)):
            TX = scanPointsX[ii]
            TY = scanPointsY[ii]
            scanPointsX[ii] = (((TX - mXcenter) * mCosRot) - ((TY - mYcenter) * mSinRot)) + mXcenter
            scanPointsY[ii] = (((TX - mXcenter) * mSinRot) + ((TY - mYcenter) * mCosRot)) + mYcenter

    # Save scan waveforms as binary files and generate final parameter text file with all new and old values
    #  only save one frame even if multi-frame movie requested; assume hardware computer will duplicate frame
    satScan = 0
    if max(scanPointsX) > 9.996:
        satScan = 1
    if min(scanPointsX) < -9.996:
        satScan = -1
    newParms["saturatedFrameX"] = str(satScan)
    satScan = 0
    if max(scanPointsY) > 9.996:
        satScan = 1
    if min(scanPointsY) < -9.996:
        satScan = -1
    newParms["saturatedFrameY"] = str(satScan)
    newParms["scanPointsX"] ="ScanPointsX_float64.bin"
    scanPointsX.tofile(localInputFolder + "/" + newParms["scanPointsX"])
    newParms["scanPointsY"] = "ScanPointsY_float64.bin"
    scanPointsY.tofile(localInputFolder + "/" + newParms["scanPointsY"])
    return newParms
    

