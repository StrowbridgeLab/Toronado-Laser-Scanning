#!/usr/bin/python
# -*- coding: utf-8 -*-

# This is rasterPlots.py
# revised 17 May 2016 BWS

import sys
import os
import configparser as CP
import os.path as path
import shutil as shutil
import subprocess
import datetime
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

def linePlotYYY(yData1, yData2, yData3, plotTitle=""):
    fig = plt.figure(frameon=False)
    fig.set_size_inches(4, 3)
    sns.set_style("darkgrid")
    fig = plt.figure()
    xData = np.arange(len(yData1))
    plt.plot(xData, yData1, "-k", xData, yData2, "-b", xData, yData3, "-r")
    plt.title(plotTitle)
    saveFileName = getTempFolder() + "/temp.pdf"
    plt.savefig(saveFileName)
    if os.name == "posix":
        subprocess.call(["open", saveFileName])
    else:
        os.startfile(saveFileName)
    return fig


def linePlotYY(yData1, yData2, plotTitle=""):
    fig = plt.figure(frameon=False)
    fig.set_size_inches(4, 3)
    sns.set_style("darkgrid")
    fig = plt.figure()
    xData = np.arange(len(yData1))
    plt.plot(xData, yData1, "-b", xData, yData2, "-r")
    plt.title(plotTitle)
    saveFileName = getTempFolder() + "/temp.pdf"
    plt.savefig(saveFileName)
    if os.name == "posix":
        subprocess.call(["open", saveFileName])
    else:
        os.startfile(saveFileName)
    return fig

def linePlotY(yData, plotTitle=""):
    fig = plt.figure(frameon=False)
    fig.set_size_inches(4, 3)
    sns.set_style("darkgrid")
    fig = plt.figure()
    plt.plot(yData)
    plt.title(plotTitle)
    saveFileName = getTempFolder() + "/temp.pdf"
    plt.savefig(saveFileName)
    if os.name == "posix":
        subprocess.call(["open", saveFileName])
    else:
        os.startfile(saveFileName)
    return fig

def linePlotXY(xData, yData, plotTitle=""):
    fig = plt.figure(frameon=False)
    fig.set_size_inches(4, 3)
    sns.set_style("darkgrid")
    fig = plt.figure()
    plt.plot(xData, yData)
    plt.title(plotTitle)
    saveFileName = getTempFolder() + "/temp.pdf"
    plt.savefig(saveFileName)
    if os.name == "posix":
        subprocess.call(["open", saveFileName])
    else:
        os.startfile(saveFileName)
    return fig

def plotXpos(cmdData, posData, rowPairMs, extraTitleStr=""):
    timeData = np.linspace(0, rowPairMs, len(cmdData))
    fig = plt.figure(frameon=False)
    fig.set_size_inches(4, 3)
    sns.set_style("darkgrid")
    fig = plt.figure()
    plt.plot(timeData, cmdData, color="b")
    plt.plot(timeData, posData, color="r")
    factorStr = "Ratio " + str(np.max(cmdData) / np.max(posData))
    plt.title("Cmd is blue; position output is red " + factorStr + " " + extraTitleStr)
    saveFileName = getTempFolder() + "/temp.pdf"
    plt.savefig(saveFileName)
    if os.name == "posix":
        subprocess.call(["open", saveFileName])
    else:
        os.startfile(saveFileName)
    return fig

def plotRowData(rowData, rowPairMs, turnLength, titleStr):
    timeData = np.linspace(0, rowPairMs, len(rowData))
    xsize = int((len(rowData) - (2 * turnLength)) / 2)
    fig = plt.figure(frameon=False)
    fig.set_size_inches(4, 3)
    sns.set_style("darkgrid")
    fig = plt.figure()
    # first turnAround
    startIndex = 0
    stopIndex = turnLength
    plt.plot(timeData[startIndex:stopIndex], rowData[startIndex:stopIndex], color="r")
    # first real data
    startIndex = stopIndex
    stopIndex = startIndex + xsize
    plt.plot(timeData[startIndex:stopIndex], rowData[startIndex:stopIndex], color="k")
    # second turnAround
    startIndex = stopIndex
    stopIndex = startIndex + turnLength
    plt.plot(timeData[startIndex:stopIndex], rowData[startIndex:stopIndex], color="r")
    # second real data
    startIndex = stopIndex
    stopIndex = startIndex + xsize
    plt.plot(timeData[startIndex:stopIndex], rowData[startIndex:stopIndex], color="k")
    plt.title(titleStr)
    plt.xlabel("Time (ms)")
    plt.ylabel("Fast axis command (V)")
    saveFileName = getTempFolder() + "/temp.pdf"
    plt.savefig(saveFileName)
    if os.name == "posix":
        subprocess.call(["open", saveFileName])
    else:
        os.startfile(saveFileName)
    return fig

def testLinePlotY():
    yData = np.cumsum(np.random.randn(1000,1))
    linePlotY(yData)


def getTempFolder():
    if os.name == "posix":
        tempName = "/Volumes/RamDrive"
        if path.exists(tempName):
            return tempName
        else:
            return path.expanduser("~")
    else:
        tempName = "R:/"
        if path.exists(tempName):
            return tempName
        else:
            return "D:/"

if __name__ == "__main__":
    testLinePlotY()

