# -*- coding: utf-8 -*-
""" createPhotometryWaveforms.py

This routine calls specialized non-raster scans used in the photometry mode.
This non-raster scan generation module is required for Toronado (ie, do not delete this file)

last revised 19 Dec 2017 BWS

"""

import sys, os, math
import os.path as path
import numpy as np

def circle(allParms):
    localInputFolder = allParms["Interface"]["localInputFolder"]
    centerX = float(allParms["Minor"]["photometryCurXvolts"])
    centerY = float(allParms["Minor"]["photometryCurYvolts"])
    sweepDurMs = float(allParms["Minor"]["photometryDurMs"])
    diameterMicrons = float(allParms["Minor"]["photometryDiameter"])
    msPerRev = 1. / float(allParms["Minor"]["photometryRevPerMs"])
    pixelUs = 1. # photometry always goes at 1 MHz pixel clock
    pointsPerMs = int(1. / (pixelUs / 1000.))
    pointsPerRev = int(pointsPerMs * msPerRev)
    numRevRepeats = 1 + int(sweepDurMs / msPerRev) # add one extra rev

    micronsPerVolt10X = float(allParms["system"]["micronspervolt10x"])
    objectiveStr = allParms["minor"]["objective"].upper().strip()
    magnification = float(objectiveStr.split("X")[0])

    newParms = {}
    circleRadius = diameterMicrons / 2000. # passed in mV, convert to Volts and radius [xx change after is known]
    oneCircleTh = np.linspace(0, 2 * np.pi, pointsPerRev, endpoint = False)
    oneCircleX = centerX + (circleRadius * np.cos(oneCircleTh))
    oneCircleY = centerY + (circleRadius * np.sin(oneCircleTh))
    satScan = 0
    if max(oneCircleX) > 9.996:
        satScan = 1
    if min(oneCircleX) < -9.996:
        satScan = -1
    newParms["saturatedFrameX"] = str(satScan)
    satScan = 0
    if max(oneCircleY) > 9.996:
        satScan = 1
    if min(oneCircleY) < -9.996:
        satScan = -1
    newParms["saturatedFrameY"] = str(satScan)
    scanPointsX = np.tile(oneCircleX, numRevRepeats)
    scanPointsY = np.tile(oneCircleY, numRevRepeats)
    newParms["numRevs"] = str(numRevRepeats)
    newParms["msPerRev"] = str(msPerRev)
    newParms["pixelUs"] = str(pixelUs)
    newParms["scanPointsX"] ="ScanPointsX_float64.bin"
    newParms["scanPointsY"] ="ScanPointsY_float64.bin"
    scanPointsX.tofile(localInputFolder + "/" + newParms["scanPointsX"])
    scanPointsY.tofile(localInputFolder + "/" + newParms["scanPointsY"])
    #print("Photometry circle diam volts: " + str(2 * circleRadius))
    print("Photometry circle mode is armed (" + str(len(oneCircleX)) + " points per cycle).")
    return newParms

def lissajous(allParms):
    localInputFolder = allParms["Interface"]["localInputFolder"]
    centerX = float(allParms["Minor"]["photometryCurXvolts"])
    centerY = float(allParms["Minor"]["photometryCurYvolts"])
    sweepDurMs = float(allParms["Minor"]["photometryDurMs"])
    diameterMicrons = float(allParms["Minor"]["photometryDiameter"])
    msPerRev = 1. / float(allParms["Minor"]["photometryRevPerMs"])
    pixelUs = 1. # photometry always goes at 1 MHz pixel clock
    pointsPerMs = int(1. / (pixelUs / 1000.))
    pointsPerRev = int(pointsPerMs * msPerRev)
    numRevRepeats = 1 + int(sweepDurMs / msPerRev) # add one extra rev

    micronsPerVolt10X = float(allParms["system"]["micronspervolt10x"])
    objectiveStr = allParms["minor"]["objective"].upper().strip()
    magnification = float(objectiveStr.split("X")[0])

    newParms = {}
    circleRadius = diameterMicrons / 2000. # passed in mV, convert to Volts and radius [xx change after is known]
    theta = np.pi / 2.
    lissA = 3 # should be even
    lissB = 4 # odd and one away from lissA
    oneCircleTh = np.linspace(0, 2 * np.pi, pointsPerRev, endpoint = False)
    oneCircleX = centerX + (circleRadius * np.sin(theta + (lissA * oneCircleTh)))
    oneCircleY = centerY + (circleRadius * np.cos(lissB * oneCircleTh))
    satScan = 0
    if max(oneCircleX) > 9.996:
        satScan = 1
    if min(oneCircleX) < -9.996:
        satScan = -1
    newParms["saturatedFrameX"] = str(satScan)
    satScan = 0
    if max(oneCircleY) > 9.996:
        satScan = 1
    if min(oneCircleY) < -9.996:
        satScan = -1
    newParms["saturatedFrameY"] = str(satScan)
    scanPointsX = np.tile(oneCircleX, numRevRepeats)
    scanPointsY = np.tile(oneCircleY, numRevRepeats)
    newParms["numRevs"] = str(numRevRepeats)
    newParms["msPerRev"] = str(msPerRev)
    newParms["pixelUs"] = str(pixelUs)
    newParms["scanPointsX"] ="ScanPointsX_float64.bin"
    newParms["scanPointsY"] ="ScanPointsY_float64.bin"
    scanPointsX.tofile(localInputFolder + "/" + newParms["scanPointsX"])
    scanPointsY.tofile(localInputFolder + "/" + newParms["scanPointsY"])
    #print("Photometry circle diam volts: " + str(2 * circleRadius))
    print("Photometry circle mode is armed (" + str(len(oneCircleX)) + " points per cycle).")
    return newParms

def halfspiral(allParms):
    localInputFolder = allParms["Interface"]["localInputFolder"]
    centerX = float(allParms["Minor"]["photometryCurXvolts"])
    centerY = float(allParms["Minor"]["photometryCurYvolts"])
    sweepDurMs = float(allParms["Minor"]["photometryDurMs"])
    diameterMicrons = float(allParms["Minor"]["photometryDiameter"])
    msPerRev = 1. / float(allParms["Minor"]["photometryRevPerMs"])
    pixelUs = 1. # photometry always goes at 1 MHz pixel clock
    pointsPerMs = int(1. / (pixelUs / 1000.))
    pointsPerRev = int(pointsPerMs * msPerRev) # calc as per circle

    micronsPerVolt10X = float(allParms["system"]["micronspervolt10x"])
    objectiveStr = allParms["minor"]["objective"].upper().strip()
    magnification = float(objectiveStr.split("X")[0])

    newParms = {}
    outerCircleRadius = diameterMicrons / 2000. # passed in mV, convert to Volts and radius [xx change after is known]
    outerCircum = 2 * outerCircleRadius * np.pi
    # numSpiralSteps = int(allParms["Minor"]["photometrySpiralSteps"])
    numSpiralSteps = 3
     # actually almost twice this because it goes in and out that number of steps
    oneSpiralX = np.zeros(0) # empty float array
    oneSpiralY = np.zeros(0)

    radiusSteps = np.linspace(outerCircleRadius, 0.5 * outerCircleRadius, numSpiralSteps) # go to 50% of initial diam
    for radius in radiusSteps: # going smaller part of spiral
        thisCircleCircum = 2 * radius * np.pi
        pointsThisCircle = int(pointsPerRev * (thisCircleCircum / outerCircum))
        oneCircleTh = np.linspace(0, 2 * np.pi, pointsThisCircle, endpoint = False)
        oneSpiralX = np.concatenate((oneSpiralX, centerX + (radius * np.cos(oneCircleTh))))
        oneSpiralY = np.concatenate((oneSpiralY, centerY + (radius * np.sin(oneCircleTh))))

    radiusSteps = np.sort(radiusSteps[:-1]) # don't repeat inner-most circle then go back out to largest circle
    for radius in radiusSteps: # going bigger part of spiral
        thisCircleCircum = 2 * radius * np.pi
        pointsThisCircle = int(pointsPerRev * (thisCircleCircum / outerCircum))
        oneCircleTh = np.linspace(0, 2 * np.pi, pointsThisCircle, endpoint = False)
        oneSpiralX = np.concatenate((oneSpiralX, centerX + (radius * np.cos(oneCircleTh))))
        oneSpiralY = np.concatenate((oneSpiralY, centerY + (radius * np.sin(oneCircleTh))))

    spiralMs = np.size(oneSpiralY) * (1. / pointsPerMs)
    satScan = 0
    if max(oneSpiralX) > 9.996:
        satScan = 1
    if min(oneSpiralX) < -9.996:
        satScan = -1
    newParms["saturatedFrameX"] = str(satScan)
    satScan = 0
    if max(oneSpiralY) > 9.996:
        satScan = 1
    if min(oneSpiralY) < -9.996:
        satScan = -1
    newParms["saturatedFrameY"] = str(satScan)

    numRevRepeats = 1 + int(sweepDurMs / spiralMs) # add one extra spiral
    scanPointsX = np.tile(oneSpiralX, numRevRepeats)
    scanPointsY = np.tile(oneSpiralY, numRevRepeats)
    newParms["numRevs"] = str(numRevRepeats)
    newParms["msPerRev"] = str(msPerRev)
    newParms["pixelUs"] = str(pixelUs)
    newParms["scanPointsX"] ="ScanPointsX_float64.bin"
    newParms["scanPointsY"] ="ScanPointsY_float64.bin"
    scanPointsX.tofile(localInputFolder + "/" + newParms["scanPointsX"])
    scanPointsY.tofile(localInputFolder + "/" + newParms["scanPointsY"])
    #print("Photometry circle diam volts: " + str(2 * circleRadius))
    print("Photometry halfspiral mode is armed (" + str(len(oneSpiralX)) + " points per cycle).")
    return newParms

def spiral(allParms):
    localInputFolder = allParms["Interface"]["localInputFolder"]
    centerX = float(allParms["Minor"]["photometryCurXvolts"])
    centerY = float(allParms["Minor"]["photometryCurYvolts"])
    sweepDurMs = float(allParms["Minor"]["photometryDurMs"])
    diameterMicrons = float(allParms["Minor"]["photometryDiameter"])
    msPerRev = 1. / float(allParms["Minor"]["photometryRevPerMs"])
    pixelUs = 1. # photometry always goes at 1 MHz pixel clock
    pointsPerMs = int(1. / (pixelUs / 1000.))
    pointsPerRev = int(pointsPerMs * msPerRev) # calc as per circle

    micronsPerVolt10X = float(allParms["system"]["micronspervolt10x"])
    objectiveStr = allParms["minor"]["objective"].upper().strip()
    magnification = float(objectiveStr.split("X")[0])

    newParms = {}
    outerCircleRadius = diameterMicrons / 2000. # passed in mV, convert to Volts and radius [xx change after is known]
    outerCircum = 2 * outerCircleRadius * np.pi
    # numSpiralSteps = int(allParms["Minor"]["photometrySpiralSteps"])
    numSpiralSteps = 5
     # actually almost twice this because it goes in and out that number of steps
    oneSpiralX = np.zeros(0) # empty float array
    oneSpiralY = np.zeros(0)

    radiusSteps = np.linspace(outerCircleRadius, 0.1 * outerCircleRadius, numSpiralSteps) # go to 10% of initial diam
    for radius in radiusSteps: # going smaller part of spiral
        thisCircleCircum = 2 * radius * np.pi
        pointsThisCircle = int(pointsPerRev * (thisCircleCircum / outerCircum))
        oneCircleTh = np.linspace(0, 2 * np.pi, pointsThisCircle, endpoint = False)
        oneSpiralX = np.concatenate((oneSpiralX, centerX + (radius * np.cos(oneCircleTh))))
        oneSpiralY = np.concatenate((oneSpiralY, centerY + (radius * np.sin(oneCircleTh))))

    radiusSteps = np.sort(radiusSteps[:-1]) # don't repeat inner-most circle then go back out to largest circle
    for radius in radiusSteps: # going bigger part of spiral
        thisCircleCircum = 2 * radius * np.pi
        pointsThisCircle = int(pointsPerRev * (thisCircleCircum / outerCircum))
        oneCircleTh = np.linspace(0, 2 * np.pi, pointsThisCircle, endpoint = False)
        oneSpiralX = np.concatenate((oneSpiralX, centerX + (radius * np.cos(oneCircleTh))))
        oneSpiralY = np.concatenate((oneSpiralY, centerY + (radius * np.sin(oneCircleTh))))

    spiralMs = np.size(oneSpiralY) * (1. / pointsPerMs)
    satScan = 0
    if max(oneSpiralX) > 9.996:
        satScan = 1
    if min(oneSpiralX) < -9.996:
        satScan = -1
    newParms["saturatedFrameX"] = str(satScan)
    satScan = 0
    if max(oneSpiralY) > 9.996:
        satScan = 1
    if min(oneSpiralY) < -9.996:
        satScan = -1
    newParms["saturatedFrameY"] = str(satScan)

    numRevRepeats = 1 + int(sweepDurMs / spiralMs) # add one extra spiral
    scanPointsX = np.tile(oneSpiralX, numRevRepeats)
    scanPointsY = np.tile(oneSpiralY, numRevRepeats)
    newParms["numRevs"] = str(numRevRepeats)
    newParms["msPerRev"] = str(msPerRev)
    newParms["pixelUs"] = str(pixelUs)
    newParms["scanPointsX"] ="ScanPointsX_float64.bin"
    newParms["scanPointsY"] ="ScanPointsY_float64.bin"
    scanPointsX.tofile(localInputFolder + "/" + newParms["scanPointsX"])
    scanPointsY.tofile(localInputFolder + "/" + newParms["scanPointsY"])
    #print("Photometry circle diam volts: " + str(2 * circleRadius))
    print("Photometry halfspiral mode is armed (" + str(len(oneSpiralX)) + " points per cycle).")
    return newParms


