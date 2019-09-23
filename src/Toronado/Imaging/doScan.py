# -*- coding: utf-8 -*-
""" doScan.py

The core interface that takes minimal text description of scan and does IPC with hardware system

This is the common entry into the hardware interface and uses a minimal text desc file containing three
blocks: [Major], [Minor], [Interface]. This routine can be called independently of the RasterGUI program
enabling you to operate the scanning system remotely or via a text editor. The RasterGUI front end just
generates the minimal text desc file for you instead of you having to edit the parameters manually. It also
enables timing functions that allow scanning to be synchronized with ePhys data acquisition.

last revised 19 Dec 2017 BWS

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
from .Helper.EasyDict import EasyDict
import Imaging.Helper.processImageData as PI

def doCommonEntry(rasterDescFileIn):
    # Main function that recieves an INI-style text file with a command and parameters
    #   One entry in the [Interface] section must be "doScanFunction = xx" that reflects
    #   the command (xx = runScanner, genericCommand, armPhotometry, or testPhotometry)
    localInputFolder, allParmsStr = _prepareToMakeZipFile(rasterDescFileIn) # reads INI file
    errorRetDict = {}
    errorRetDict["retOkay"] = False
    if not allParmsStr:
        print("Error: problem with absence of parm Dict inside doScan.py")
        return errorRetDict
    requestedFunction = allParmsStr["Interface"]["doScanFunction"].lower().strip()
    if requestedFunction in ["runscanner"]:
        retDict = _doRunScanner(localInputFolder, allParmsStr)
    elif requestedFunction in ["genericcommand"]:
        retDict = _doGenericCommand(localInputFolder, allParmsStr)
    elif requestedFunction in ["armphotometry"]:
        retDict = _doArmPhotometry(localInputFolder, allParmsStr)
    elif requestedFunction in ["testphotometry"]:
        retDict = _doTestPhotometry(localInputFolder, allParmsStr)
    else:
        print("Error: requested function not available in DoScan.py: " + requestedFunction)
        return errorRetDict
    return retDict

def _doGenericCommand(localInputFolder, allParmsStr):
    falseStrings = ["false", "no", "0", "off"]
    retDict = {}
    diagMode = allParmsStr["Interface"]["diagmode"].lower() not in falseStrings
    allParmsStr["Interface"]["currentcommand"] = allParmsStr["Interface"]["specificCommand"]
    hardwareAddress = (allParmsStr["System"]["hardwareADCip"], int(allParmsStr["System"]["hardwareADCport"]))
    retOkay = _sendZipFile(localInputFolder, allParmsStr["Interface"], allParmsStr["System"]["tempFolder"],
                           hardwareAddress, diagMode)
    if not retOkay:
        print("Problem on return code from sendZipFile inside doScan.py (doGenericCommand)")
        retDict["retOkay"] = False
        return retDict
    if diagMode:
        print("Finished sending generic command file and other files to hardware computer")
    retDict["retOkay"] = True
    return retDict

def _doTestPhotometry(localInputFolder, allParmsStr):
    falseStrings = ["false", "no", "0", "off"]
    retDict = {}
    diagMode = allParmsStr["Interface"]["diagmode"].lower() not in falseStrings
    allParmsStr["Interface"]["currentcommand"] = "DoTestPhotometry"
    allParmsStr["Interface"]["destFileName"] = allParmsStr["System"]["tempfolder"] + "/testPhotometry.gsi"
    imageDescFN = "PhotometryDescription.txt"
    allParmsStr["Interface"]["ImageDesc"] = imageDescFN

    # make new scan waveforms
    allParmsStr["minor"]["photometrydurms"] = "7" # use 7 ms
    retOkay = _createPhotometryScan(allParmsStr, imageDescFN)
    if not retOkay:
        print("Problem creating photometry scan files.")
        retDict["retOkay"] = False
        return retDict
    if diagMode:
        print("Created new photometry scan waveforms as part of test.")

    # send photometry scan waveforms to hardware computer
    hardwareAddress = (allParmsStr["System"]["hardwareADCip"], int(allParmsStr["System"]["hardwareADCport"]))
    retOkay = _sendZipFile(localInputFolder, allParmsStr["Interface"], allParmsStr["System"]["tempFolder"],
                           hardwareAddress, diagMode)
    if not retOkay:
        print("Problem on return code from sendZipFile inside doScan.py (doTestPhotometry)")
        retDict["retOkay"] = False
        return retDict
    if diagMode:
        print("Finished sending photometry scan waveforms and other files to hardware computer")

    # wait for data to be returned; listen on different port to keep things simple for hardwarePC
    if diagMode:
        print("Request sent now waiting for hardware computer to finish ...")

    servAddr = (allParmsStr["System"]["returnIP"], int(allParmsStr["System"]["returnPort"]))
    newFileName = allParmsStr["Interface"]["destFileName"].strip()

    timeOutSec = 2
    retOkay = _waitForSocketResponse(servAddr, newFileName, timeOutSec, diagMode)
    if not retOkay:
        print("Problem with return code on waitForSocketResponse in DoScan.py (doTestPhotometry).")
        retDict["retOkay"] = False
        return retDict

    print("Finished getting test photometry data " + newFileName + " status: " + str(retOkay))
    retDict = PI.loadPhotometryZipFile(newFileName)
    if len(retDict["data"]["A"]) >= 6000:
        meanA = np.mean(retDict["data"]["A"][1000:6000]) # wait 1 ms for shutter to open then average for 5 ms
        meanB = np.mean(retDict["data"]["B"][1000:6000]) # wait 1 ms for shutter to open then average for 5 ms
        #print("Mean photoresponse: " + str(meanA) + " " + str(meanB))
        retDict["meanChanA"] = meanA
        retDict["meanChanB"] = meanB
        retDict["retOkay"] = True
        return retDict
    else:
        print("Not enough photometry data returned")
        retDict["retOkay"] = False
        return retDict

def _doArmPhotometry(localInputFolder, allParmsStr):
    falseStrings = ["false", "no", "0", "off"]
    retDict = {}
    diagMode = allParmsStr["Interface"]["diagmode"].lower() not in falseStrings
    allParmsStr["Interface"]["currentcommand"] = "DoLoadPhotometry"
    imageDescFN = "PhotometryDescription.txt"
    allParmsStr["Interface"]["ImageDesc"] = imageDescFN
    allParmsStr["Interface"]["PositionData"] = str(allParmsStr["Minor"]["positionEpisode"])
    # make new scan waveforms
    retOkay = _createPhotometryScan(allParmsStr, imageDescFN)
    if not retOkay:
        print("Problem creating photometry scan files.")
        retDict["retOkay"] = False
        return retDict
    if diagMode:
        print("Created new photometry scan waveforms.")

    # send photometry scan waveforms to hardware computer
    hardwareAddress = (allParmsStr["System"]["hardwareADCip"], int(allParmsStr["System"]["hardwareADCport"]))
    retOkay = _sendZipFile(localInputFolder, allParmsStr["Interface"], allParmsStr["System"]["tempFolder"],
                           hardwareAddress, diagMode)
    if not retOkay:
        print("Problem on return code from sendZipFile inside doScan.py (doArmPhotometry)")
        retDict["retOkay"] = False
        return retDict
    if diagMode:
        print("Finished sending photometry scan waveforms and other files to hardware computer")
    retDict["retOkay"] = True
    return retDict

def _doRunScanner(localInputFolder, allParmsStr):
    startTime = datetime.datetime.now()
    falseStrings = ["false", "no", "0", "off"]
    retDict = {}
    diagMode = allParmsStr["Interface"]["diagmode"].lower() not in falseStrings
    allParmsStr["Interface"]["currentcommand"] = "DoScan"

    # make new scan waveforms and ImageDesc text file if requested
    imageDescFN = "ImageDescription.txt"
    allParmsStr["Interface"]["ImageDesc"] = imageDescFN
    allParmsStr["Interface"]["ReturnPositionData"] = str(int(allParmsStr["Interface"]["positionData"]))
    if allParmsStr["Interface"]["updateScanWaveforms"].lower() not in falseStrings:
        retOkay = _createScan(allParmsStr, imageDescFN)
        if retOkay:
            retImageDescFN = imageDescFN # to let calling program know about updated parms
        else:
            print("Problem creating scan files.")
            retDict["retOkay"] = False
            return retDict
        if diagMode:
            print("Created new scan waveforms.")
    else:
        # hardwarePC is going to recycle cached ImageDescription.txt file since no changed parameters
        retImageDescFN = "" # this routine did not create a new ImageDesc file, so nothing to return

    hardwareAddress = (allParmsStr["System"]["hardwareADCip"], int(allParmsStr["System"]["hardwareADCport"]))
    retOkay = _sendZipFile(localInputFolder, allParmsStr["Interface"], allParmsStr["System"]["tempFolder"],
                           hardwareAddress, diagMode)
    if not retOkay:
        print("Problem on return code from sendZipFile inside doScan.py (doGenericCommand)")
        retDict["retOkay"] = False
        return retDict
    if diagMode:
        print("Finished sending doRunScanner command file and other files to hardware computer")

    # wait for data to be returned; listen on different port to keep things simple for hardwarePC
    if diagMode:
        print("Request sent now waiting for hardware computer to finish ...")

    servAddr = (allParmsStr["System"]["returnIP"], int(allParmsStr["System"]["returnPort"]))
    newFileName = allParmsStr["Interface"]["destFileName"].strip()
    if "estSecPerFrame" in allParmsStr["Interface"]:
        timeOutSec = 2 + (int(allParmsStr["Interface"]["numframes"])) * float(allParmsStr["interface"]["estSecPerFrame"])
    else:
        timeOutSec = 2 * int(allParmsStr["Interface"]["numframes"]) # estimate of 2 sec per frame max
    retOkay = _waitForSocketResponse(servAddr, newFileName, timeOutSec, diagMode)
    if not retOkay:
        print("Problem with return code on waitForSocketResponse in DoScan.py (runScanner).")
        retDict["retOkay"] = False
        return retDict
    if diagMode:
        print("  new file is: " + newFileName)
        diffTime = datetime.datetime.now() - startTime
        elaspedMs = (diffTime.seconds * 1000) + (diffTime.microseconds / 1000)
        print("Total milliseconds required: " + str(int(10. * elaspedMs) / 10.))
    retDict["newFileName"] = newFileName
    retDict["imageDescFN"] = retImageDescFN
    retDict["retOkay"] = True
    return retDict


# Private functions below here

def _prepareToMakeZipFile(rasterDescFileIn):
    rasterDescFile = path.expanduser(rasterDescFileIn)
    if not path.exists(rasterDescFile):
        print("Cannot find requested DoScan command file: " + str(rasterDescFile))
        return "", ""
    allParmsStr = _preProcessParms(rasterDescFile) # actual reading of INI file

    # copy key parameters to [Interface] section since the RasterNoGUI only gets this section
    allParmsStr["Interface"]["localInputFolder"] = allParmsStr["System"]["tempFolder"] + "/Input"
    allParmsStr["Interface"]["commandTimeStamp"] = str(datetime.datetime.now())
    allParmsStr["Interface"]["returnIPaddress"] = allParmsStr["System"]["returnIP"]
    allParmsStr["Interface"]["returnport"] = allParmsStr["System"]["returnPort"]

    # create empty folder to put final parms and waveform files
    localInputFolder = allParmsStr["Interface"]["localInputFolder"]
    if not path.exists(localInputFolder):
        os.makedirs(localInputFolder)
    else:
        # input folder exists so clear any existing files or subfolders in it
        for oneFile in os.listdir(localInputFolder):
            filePlusPath = path.join(localInputFolder, oneFile)
            if path.isfile(filePlusPath):
                os.unlink(filePlusPath)
            elif path.isdir(filePlusPath):
                shutil.rmtree(filePlusPath)
    return localInputFolder, allParmsStr

def _sendZipFile(localInputFolder, parmDict, tempFolder, hardwareAddress, diagMode):
    # Makes Cmd.txt file, collapses everything in localInputFolder into a zip file and sends it to IP+port specified
    #   typically parmDict is only the [Interface] section of the main parameter dict. However
    #   the hardware RasterNoGUI will make a copy of the input ImageParameters INI file and include it in
    #   the output Zip file since some of those parameters (e.g., systemLag) are needed to decode raw data
    finalCmdFile = localInputFolder + "/Cmd.txt"
    with open(finalCmdFile, "w") as fOut: # write interface parameters to Cmd.txt file
        print("[Commands]\r", file=fOut) # the extra return char is required for Windows PCs
        for key in sorted(parmDict):
            print(str(key).lower() + " = " + parmDict[key] + "\r", file=fOut)

    # write final Zip file containing cmd, imageDesc, and scan waveforms (if requested)
    os.chdir(localInputFolder) # temp folder (typically on a RamDrive)
    zipFileName = tempFolder + "/rasterInput.zip"
    with zipfile.ZipFile(zipFileName, "w") as fZip:
        for root, dirs, files in os.walk(localInputFolder):
            for file in files:
                fZip.write(file)

    # send Zip file to hardwareAddress
    zipBytes = open(zipFileName, "rb").read()
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(1) # allow 1 sec before triggering a time-out exception
    try:
        client.connect(hardwareAddress)
        if diagMode:
            print("hardware client connected ...")
    except:
        print("** ERROR: Could not connect to hardware computer at " + str(hardwareAddress))
        client.close()
        return False
    client.settimeout(None) # best to turn off to send Zip file properly
    client.sendall(zipBytes) # should try sendall() instead of send()
    client.close()
    return True

def _waitForSocketResponse(servAddr, returnDataFileName, timeOutSec, diagMode):
    bufSize = 4096 * 2
    serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv.bind(servAddr)
    serv.listen(5)
    if diagMode:
        print("listening for return of acquired data from hardware computer...")
    serv.settimeout(timeOutSec)
    while True:
        try:
            listenConn, listenAddr = serv.accept()
        except socket.timeout:
            print("ERROR - hardware computer did not respond with acquired data within max time allowed.")
            return None
        if diagMode:
            print('hardware computer connected ... ', listenAddr)
        serv.settimeout(None)
        myHandle = open(returnDataFileName, "wb")
        while True:
            data = listenConn.recv(bufSize)
            if not data: break
            myHandle.write(data)
        myHandle.close()
        listenConn.close()
        if diagMode:
            print("Closed socket connection with hardware computer.")
        break
    return True

def _preProcessParms(parmFileName):
    # returns a Dict of input parmeters with subDicts for Major, Minor etc
    # returns strings of all parameters
    if path.exists(parmFileName):
        systemINI = None
        config = ConfigParser.ConfigParser()
        config.read(parmFileName)
        coreDict = EasyDict()
        for oneSection in config.sections():
            if config[oneSection]:
                coreDict[oneSection] = EasyDict()
                for key in config[oneSection]:
                    coreDict[oneSection][key] = config[oneSection][key].split(";")[0].strip()
                    if key == "systemini":
                        systemINI = path.expanduser(config[oneSection][key].split(";")[0].strip())
                        if not path.exists(systemINI):
                            print("Bad system INI file found in doScan.py")
                            systemINI = None
        if systemINI:
            config = ConfigParser.ConfigParser()
            config.read(systemINI)
            coreDict["System"] = EasyDict()
            for oneSection in config.sections():
                if config[oneSection]:
                    for key in config[oneSection]:
                        coreDict["System"][key] = config[oneSection][key].split(";")[0].strip()
            return coreDict
        else:
            print("no systemINI file processed")
            return None
    else:
        return None

def _createPhotometryScan(allParms, passedImageDescFN):
    scanModuleStr = "Imaging.Helper.Scans.createPhotometryScans"
    try:
        scanModule = importlib.import_module(scanModuleStr)
    except:
        print("ERROR - problem importing module: " + scanModuleStr)
        return False
    scanFunctionStr = allParms["Minor"]["photometryShape"].lower().strip()
    try:
        updatedNewParms = getattr(scanModule, scanFunctionStr)(allParms)
    except:
        print("ERROR - could not match requested photometryMode with a generation subroutine: " + scanFunctionStr)
        return False
    localInputFolder = allParms["Interface"]["localInputFolder"]
    updatedNewParms["scanWaveformsTimeStamp"] = str(datetime.datetime.now())
    with open(localInputFolder + "/" + passedImageDescFN, "w") as fOut:
        print("[Derived]\r", file=fOut)
        for key, value in sorted(updatedNewParms.items()):
            print(str(key).lower() + " = " + str(value) + "\r", file=fOut) # str to fix any number entries
        print(" ", file=fOut)
        print("[System]\r", file=fOut)
        for key, value in sorted(allParms["System"].items()):
            print(str(key).lower() + " = " + value + "\r", file=fOut)
    return True

def _createScan(allParms, passedImageDescFN):
    # called once major and minor parameters are set to create derived Dict
    # this routine creates the ImageDescription.txt file that contains all parameters - both
    # those specified by the user and the derived settings like turnLength
    # it also writes the scan waveforms binary files to the tempFolder

    # create common initial variables needed for most scan generation subroutines
    newParms = {} # will become [Derived] section in final ImageDescription.txt file
    newParms["doScanVersion"] = str(1.2)
    newParms["zoomAsVolts"] = str(_zoomToVoltage(float(allParms["Major"]["zoom"])))
    lagUs = float(allParms["System"]["systemlagus"]) + float(allParms["Minor"]["lagtweakus"])
    newParms["lagUs"] = str(lagUs)
    newParms["lagPixels"] = str(int(lagUs / float(allParms["Major"]["pixelUs"])))
    numADCs = 0
    chanList = ""
    if float(allParms["Major"]["chanAfullScale"]) > 0:
        numADCs += 1
        chanList += "A"
    if float(allParms["Major"]["chanBfullScale"]) > 0:
        numADCs += 1
        chanList += "B"
    if float(allParms["Major"]["chanCfullScale"]) > 0:
        numADCs += 1
        chanList += "C"
    if float(allParms["Major"]["chanDfullScale"]) > 0:
        numADCs += 1
        chanList += "D"
    if numADCs == 0:
        print("Warning: No ADC channels are enabled.")
    newParms["numADCs"] = str(numADCs)
    newParms["ADCchanLetters"] = chanList

    # now load module and run function selected by Minor parameters to create scan
    #   allows program to be extended with new types of scans without changing core code
    updatedNewParms = None # an empty variable in case scan generation does not work
    scanModuleStr = "Imaging.Helper.Scans.createStandardScans"
    try:
        scanModule = importlib.import_module(scanModuleStr)
    except:
        print("ERROR - problem importing module: " + scanModuleStr)
    scanFunctionStr = allParms["Minor"]["scanfunction"].lower().strip()
    try:
        updatedNewParms = getattr(scanModule, scanFunctionStr)(allParms, newParms)
    except:
        print("ERROR - could not match requested scanType with a generation subroutine: " + scanFunctionStr)

    # write final ImageDescription file to temp folder
    if updatedNewParms:
        localInputFolder = allParms["Interface"]["localInputFolder"]
        updatedNewParms["scanWaveformsTimeStamp"] = str(datetime.datetime.now())
        with open(localInputFolder + "/" + passedImageDescFN, "w") as fOut:
            print("[Major]\r", file=fOut)
            for key, value in sorted(allParms["Major"].items()):
                print(str(key).lower() + " = " + value + "\r", file=fOut)
            print(" ", file=fOut)
            print("[Minor]\r", file=fOut)
            for key, value in sorted(allParms["Minor"].items()):
                print(str(key).lower() + " = " + value + "\r", file=fOut)
            print(" ", file=fOut)
            print("[Derived]\r", file=fOut)
            for key, value in sorted(updatedNewParms.items()):
                print(str(key).lower() + " = " + str(value) + "\r", file=fOut) # str to fix any number entries
            print(" ", file=fOut)
            print("[System]\r", file=fOut)
            for key, value in sorted(allParms["System"].items()):
                print(str(key).lower() + " = " + value + "\r", file=fOut)
        return True
    else:
        return False

def _zoomToVoltage(zoomLevel):
    # converts zoom level to voltage span; zoom=1 gives ~ 20V span (-10 to 10 FS)
    if zoomLevel < 1:
        print("Warning: minimum zoom is 1.")
        zoomLevel = 1.
    elif zoomLevel > 9:
        print("Warning: maximum zoom is 9.")
        zoomLevel = 9.
    voltSpan = 39.9998 * math.exp((-1. * zoomLevel) / 1.4427)
    return voltSpan


if __name__ == "__main__":
    if len(sys.argv) == 2:
        tempFN = path.expanduser(sys.argv[1])
        if path.exists(tempFN):
            doRunScanner(tempFN)
        else:
            print("Bad scan parameter file: " + tempFN)
    else:
        print("You need to provide a scan parameter text file name with doScan.py")

