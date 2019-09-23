# -*- coding: utf-8 -*-
# processImageData.py - helper routines to decode raw binary ADC and write zip plus TIFF files

# revised 17 Dec 2017 BWS
# includes fix for lag drift during movies in decodeData (index += 1)
# changed loadRasterZipFile on 28 Mar 2017 to allow for .gsi files that are renamed Zip image files
# added reading photometry test data 7 Dec 2017

import numpy as np
from scipy.io import savemat
import os.path as path
import time
import os
import shutil
import configparser as ConfigParser
import zipfile
import glob, copy, pickle
import tifffile as TIFF

def readImageFile(fileName, readHeader=True):
    if path.splitext(fileName)[1].lower() in [".tif", ".tiff"]:
        retDict = _loadTIFF(fileName, readHeader=readHeader)
    elif path.splitext(fileName)[1].lower() == ".img":
        retDict = _loadIMG(fileName, readHeader=readHeader)
    elif path.splitext(fileName[1].lower() in [".zip", ".gsi"]): # gsi is a renamed zip file
        retDict = loadRasterZipFile(fileName)
    else:
        print("unknown file type: " + path.splitext(fileName[1]))
        return None
    if not retDict:
        return None
    else:
        if retDict["containsValidData"]:
            return retDict
        else:
            return None

def loadPhotometryZipFile(fileName):
    if not path.exists(fileName):
        print("Requested .zip or .gsi file not found: " + fileName)
        return None
    with zipfile.ZipFile(fileName, "r") as fZip:
        contents = fZip.namelist()
        retDict = {}
        retDict["data"] = {}
        retDict["loadedFileName"] = fileName
        chanFN = _ADCnameFromNum(0) # makes full name, eg 0 => ADC0_ImageRaw_int16.bin
        retDict["data"]["A"] = _arrayFromZip(chanFN, fZip)
        chanFN = _ADCnameFromNum(1) # makes full name, eg 0 => ADC0_ImageRaw_int16.bin
        retDict["data"]["B"] = _arrayFromZip(chanFN, fZip)
    retDict["containsValidData"] = True
    return retDict

def loadRasterZipFile(fileName, specificADCchannels=None, lagPixelsAdjust=0, fastMode=False):
    """
    loadRasterZipFile -- last revised 31 Mat 2017 BWS

    Reads new style zip files with _ImageRaw in binary chan name and returns dict with retDict[data][A]
    representing an image stack [numFrames][image]; chan B data would be in retDict[data][B] etc
    file description text is saved as a string dict in retDict[parms]; Xsize would be retrieved using
    int(retDict[parms][xsize]). You can extract a specific set of channels by passing letters
    like "A" or ["A", "B"]. fastMode=True skips several steps like finding max pixel values in each stack.
    You can shift the reading frame during decoding by lagPixelsAdjust=xx to optimize odd/even row
    correlation in bidirectional image stacks. Max positive shift is 20 pixels; negative shifts are possible.
    """
    if not path.exists(fileName):
        print("Requested .zip or .gsi file not found: " + fileName)
        return None
    with zipfile.ZipFile(fileName, "r") as fZip:
        contents = fZip.namelist()
        retDict = {}
        retDict["data"] = {}
        retDict["loadedFileName"] = fileName
        retDict["channelNames"] = {} # for full name like Green or Red
        retDict["channelMaxValues"] = {}

        # file type specific stuff here
        if path.splitext(fileName)[1].lower() == ".zip":
            descFN = "ImageDescription.txt"
            if not descFN in contents:
                print("Zip file does not have an image description file: " + descFN)
                return None
            retDict["parms"] = _dictFromZip(descFN, fZip) # converts all new keys to lowercase
            retDict["parms"]["rastercmd"] = fZip.read("RasterCmd.txt").decode("utf-8")
        else:
            if not path.splitext(fileName)[1].lower() == ".gsi":
                print("ERROR - loadRasterZipFile routine can only process .zip or .gsi files.")
                return None
            tempCmd = _dictFromZip("Cmd.txt", fZip)
            retDict["parms"] = _dictFromZip(tempCmd["imagedesc"], fZip)
            if "hardwareSettings.txt" in contents:
                retDict["parms"]["hardware"] = _dictFromZip("hardwareSettings.txt", fZip)
            retDict["parms"]["numframes"] = int(tempCmd["numframes"])
            retDict["parms"]["positiondata"] = (1 == int(tempCmd["returnpositiondata"]))

        # common read stuff below here
        retDict["Xsize"] = int(retDict["parms"]["xsize"])
        retDict["Ysize"] = int(retDict["parms"]["ysize"])
        retDict["numFrames"] = int(retDict["parms"]["numframes"])
        includedADCchannels = []
        for oneChanNum in ["0", "1", "2", "3"]:
            if _ADCnameFromNum(oneChanNum) in contents:
                includedADCchannels.append(int(oneChanNum))
        if len(includedADCchannels) == 0:
            print("Requested .zip or .gsi file does not contain any Raster ADC output files")
            return None
        if specificADCchannels:
            chansToExtract = []
            for oneChan in specificADCchannels:
                chanNum = ord(oneChan.upper()) - 65 # to make A => 0, B => 1, etc
                if chanNum in includedADCchannels:
                    chansToExtract.append(chanNum)
                else:
                    print("Warning -- Requested channel not included in Zip file: " + oneChan)
        else:
            chansToExtract = includedADCchannels
        if len(chansToExtract) == 0:
            print("loadZipCore is ending because there are no Raster-generated ADC channels to extract.")
            return None
        retDict["channelLetters"] = [chr(65 + oneChanNum) for oneChanNum in chansToExtract]
        for oneChanNum in chansToExtract:
            chanLetter = chr(65 + oneChanNum) # 0 => A, 1 => B, etc
            chanFN = _ADCnameFromNum(oneChanNum) # makes full name, eg 0 => ADC0_ImageRaw_int16.bin
            retDict["data"][chanLetter] = _decodeRasterData(_arrayFromZip(chanFN, fZip), retDict["parms"],
                                                           lagPixelsAdjust=lagPixelsAdjust)
            retDict["channelNames"][chanLetter] = retDict["parms"][("chan" + chanLetter + "name").lower()]
            if fastMode:
                retDict["channelMaxValues"][chanLetter] = 2047
            else:
                retDict["channelMaxValues"][chanLetter] = 10 * int(np.percentile(retDict["data"][chanLetter], 99) / 10)
    # end of zip file processing so close it automatically
    retDict["maxPossibleValue"] = 2048
    retDict["containsValidData"] = True
    return retDict

def saveProcessedImageData(passDict, curFileName, newFormatStr, specificFrame=-1):
    # called by ImageDisplay window to re-format already saved data (eg, dump decoded image stack as a binary file)
    # generate output files for each ADC channel; specificFrame=-1 for entire movie
    # if lag pixels were adjusted post-acquisition in ImageWindow, images with this revised lag will be saved here
    if not curFileName:
        fileRoot = path.expanduser("~/RasterImages/toronadoOutput.zip")
    else:
        fileRoot = curFileName
    fileRoot = path.splitext(fileRoot)[0]
    finalName = "" # default for return value
    if newFormatStr in ["mat", "pk", "zip"]:
        # these extensions will save entire zip file content, not specific frames
        if newFormatStr == "mat": # xx fix to remove from channel loop and also fix 1-frame movies to have 2D stacks
            finalName = fileRoot + ".mat" # always saves entire zip file contents
            matCellName = (path.split(fileRoot)[1]).replace(" ", "_")
            tempDict = copy.deepcopy(passDict) # create a copy of main Dict since we have to modify data arrays
            for oneChanLetter in tempDict["parms"]["adcchanletters"]:
                if len(passDict["data"][oneChanLetter]) == 1:
                    tempDict["data"][oneChanLetter] = passDict["data"][oneChanLetter][0] # get rid of enclosing list
                else:
                    tempDict["data"][oneChanLetter] = np.array(passDict["data"][oneChanLetter]) # to 3-D np Array
            saveDict = {}
            saveDict[matCellName] = tempDict # nest passDict one level down so there is a single variable in Matlab
            savemat(finalName, saveDict)
            print("Saved " + finalName)
        if newFormatStr == "pk":
            finalName = path.splitext(fileRoot)[0] + ".pk"
            with open(finalName, "wb") as fP:
                pickle.dump(passDict, fP)
            print("Saved " + finalName)
        else:
            print("Unknown whole dict save method")
    else:
        # these extensions will trigger saving a specific frame rather than all the data
        for oneChanLetter in passDict["parms"]["adcchanletters"]:
            if oneChanLetter == "A":
                chanName = passDict["parms"]["chananame"]
            else:
                chanName = passDict["parms"]["chanBname"]
            oneFileRoot = fileRoot + "_ADC" + oneChanLetter + "_" + chanName
            if specificFrame == -1:
                saveData = np.array(passDict["data"][oneChanLetter]) # whole stack to numpy 3-D array
                sizeStr = "_" + str(passDict["numFrames"]) + "x" + str(passDict["Xsize"]) + "x" + str(passDict["Ysize"])
            else:
                saveData = passDict["data"][oneChanLetter][specificFrame] # one image is a 2-D numpy array
                sizeStr = "_" + str(passDict["Xsize"]) + "x" + str(passDict["Ysize"])
            finalName = None
            if newFormatStr == "tif":
                finalName = oneFileRoot + sizeStr + ".tif"
                TIFF.imsave(finalName, saveData)
            elif newFormatStr == "bin":
                finalName = oneFileRoot + sizeStr + "_int16.bin"
                saveData.tofile(finalName)
            else:
                print("Unknown file type for saving processed data: " + newFormatStr)
            if finalName:
                print("Saved " + finalName)
    return finalName

def _decodeRasterData(rawData, parmDict, lagPixelsAdjust=0):
    # This routine decode the binary int16 data from a single ADC channel
    # returns a list of numpy(x,y) frames; lag correction can be adjusted from saved value in off-line decode
    # last revised 29 May 2016 BWS
    pixelsX = int(parmDict["xsize"])
    pixelsY = int(parmDict["ysize"])
    bidirectional = (1 == int(parmDict["bidirectional"]))
    if lagPixelsAdjust > 20:
        print("Warning -- max allowable positive lag pixel adjustment is 20. Resetting to this max value.")
        lagPixelsAdjust = 20
    lagPixels = int(parmDict["lagpixels"]) + lagPixelsAdjust
    turnLength = int(parmDict["turnlength"])
    numFrames = int(parmDict["numframes"]) # xx changed
    zStack = [] # empty list to contain all decoded frames
    index = lagPixels # start transferring data after jumping over lagPixels num of points
    for _ in range(numFrames):
        oneFrame = np.zeros((pixelsX, pixelsY), dtype="int16") # empty starting array must be created for each frame
        if bidirectional:
            # for bidirectional data we have to reverse odd rows
            for y in range(0, pixelsY, 2):
                index += turnLength
                oneFrame[:,y] = rawData[index:index+pixelsX] # forward
                index += pixelsX + turnLength
                oneFrame[:,y+1] = rawData[index:index+pixelsX][::-1] # reverse
                index += pixelsX
        else:
            # unidirectional data
            for y in range(0, pixelsY):
                index += turnLength
                oneFrame[:,y] = rawData[index:index+pixelsX] # forward
                index += pixelsX
        index += 1 # added as temp fix for lag drift during movies 10 Jun 2016 xx
        zStack.append(oneFrame)
    return zStack

def _ADCnameFromNum(chanNum):
    # converts an int like 0 or 1 into a complete file name that matches the format used in the zip archive
    return "ADC" + str(chanNum) + "_ImageRaw_int16.bin"

def _arrayFromZip(fName, zipHandle):
    # reads data file from Zip archive assuming last _ thing in name is dtype string
    fRoot = path.splitext(fName)[0]
    myDtype = fRoot.split("_")[-1].lower() # should be int16, float64 etc
    return np.frombuffer(zipHandle.read(fName), dtype=myDtype)

def _dictFromZip(fName, zipHandle):
    # removes section headings and just makes a one-level Dict; always converts keys to lowercase
    config = ConfigParser.ConfigParser()
    config.read_string(zipHandle.read(fName).decode("ASCII"))
    tempDict = {}
    for sectionName in config.sections():
        for key, value in config.items(sectionName):
            tempDict[key.lower()] = value
    return tempDict

# private functions below here

def _loadIMG(fileName, readHeader=True):
    retDict = {}
    retDict["loadedFileName"] = fileName
    retDict["fileRoot"] = path.splitext(path.split(fileName)[1])[0]
    retDict["containsValidData"] = False # default until re-written at end of a successful read
    if path.isfile(fileName):
        with open(fileName, "r") as f:
            programNum = np.fromfile(f, dtype=np.int32, count=1)
            programMode = np.fromfile(f, dtype=np.int32, count=1)
            if (programNum == 3) and (programMode == 0):
                dataOffset = np.fromfile(f, dtype=np.int32, count=1)
                retDict["Xsize"] = np.asscalar(np.fromfile(f, dtype=np.int32, count=1))
                retDict["Ysize"] = np.asscalar(np.fromfile(f, dtype=np.int32, count=1))
                retDict["numFrames"] = np.asscalar(np.fromfile(f, dtype=np.int32, count=1))
                retDict["numChannels"] = np.asscalar(np.fromfile(f, dtype=np.int32, count=1))
                retDict["containsValidData"] = True
                retDict["headerInfoAvailable"]= False
                if readHeader:
                    x = retDict["Xsize"]
                    y = retDict["Ysize"]
                    f.seek(dataOffset-1)
                    tempF0 = np.fromfile(f, dtype=np.int16, count=(x*y))
                    tempF = np.reshape(np.ravel(tempF0), (y, x)).T
                    #plt.plot(np.arange(x), tempF[:,3])
                    #plt.show()
                    retDict["data"] = [[tempF]]
                channelMaxValues = []
                for kk in range(retDict["numChannels"]):
                    channelMaxValues.append(0) # to be updated if not in fast-read mode
                retDict["channelMaxValues"] = channelMaxValues
                retDict["channelMaxValues"] = _findChannelMaxValues(retDict)
                retDict["channelNames"] = ["oneChan"]
            else:
                print("Error reading IMG file: " + fileName)
    else:
        print("Problem opening IMG file: " + fileName)
    return retDict

def _loadTIFF(fileName, readHeader=True):
    # returns nested Lists of 2D numpy arrays: NumFrames, NumChannels, OneFrame
    # so retDict["data"][3][1] gets the fourth frame, second channel
    # and retDict["data"][0][0] gets the first frame, first channel (saved this way even if only one frame)
    # channelMaxValues is a List of 99%ile for each channel, calculated across the movie (rounded to nearest 10)
    retDict = {}
    retDict["loadedFileName"] = fileName
    retDict["fileRoot"] = path.splitext(path.split(fileName)[1])[0]
    retDict["containsValidData"] = False # default until re-written at end of a successful read
    if path.isfile(fileName):
        try:
            im = TIFF.TiffFile(fileName)
            retDict["containsValidData"] = True
            retDict["headerInfoAvailable"] = readHeader
            if readHeader:
                mainList = (str(im[0].tags["image_description"])).split("\\n")
                retDict["frameNumbers"] = mainList[0].split("=")[1].strip()
                for ii in range(1, len(mainList) - 2):
                    parts = mainList[ii].split("=")
                    if "user" not in parts[0] and "usr" not in parts[0]:
                        if "." in parts[0]:
                            newKey = parts[0].split(".")[-1].strip()
                        else:
                            newKey = parts[0].strip()
                        retDict[newKey] = parts[1].strip()
                #for oneKey in retDict:
                    #print(oneKey + " = " + str(retDict[oneKey]))
                if ";" in retDict["channelsActive"]:
                    # Matlab array for channel indexes; need to convert to 0-based indexes for python
                    retDict["channelsList"] = [ii - 1 for ii in eval(retDict["channelsActive"].replace(";", ","))]
                    retDict["numChannels"] = len(retDict["channelsList"])
                else:
                    # just one channel
                    retDict["numChannels"] = 1
                    retDict["channelsList"] = [eval(retDict["channelsActive"]) - 1]

                tempStr = retDict["channelMergeColor"].replace("{","").replace("}","").replace("'","")
                if ";" in tempStr:
                    parts = tempStr.split(";")
                else:
                    parts = tempStr.split(" ")
                tempList = []
                for kk in range(retDict["numChannels"]):
                    tempList.append(parts[kk])
                retDict["channelNames"] = tempList

                retDict["numFrames"] = int(retDict["framesPerSlice"])
                retDict["Xsize"] = int(retDict["pixelsPerLine"])
                retDict["Ysize"] = int(retDict["linesPerFrame"])
                tempData = im.asarray() # will be 2d for one image or 3d if >1 frames or >1 channel

                junk = np.reshape(np.ravel(tempData), (retDict["Ysize"], retDict["Xsize"])).T
                #plt.plot(np.arange(1024), junk[:,0])
                #plt.show()
                #tempShape = np.shape(tempData)
                #print("Dict: " + str(retDict["Xsize"]) + " by " + str(retDict["Ysize"]))
                #print("Shape: " + str(tempShape))
                if retDict["numFrames"] == 1 and retDict["numChannels"] == 1:
                    #chanData = [[np.reshape(tempData.T, (retDict["Ysize"], retDict["Xsize"]))]]
                    #chanData = [[np.fliplr(tempData.T)]] # works for Chris' image
                    #chanData = [[np.reshape(np.flipud(tempData), (retDict["Xsize"], retDict["Ysize"]))]]
                    chanData = [[junk]]
                    print("Load: " + str(np.shape(chanData)))
                else:
                    # store in retDict as [channel][frame][one x by y image]
                    chanData = []
                    for channel in range(retDict["numChannels"]):
                        framesInOneChannel = []
                        for frame in range(retDict["numFrames"]):
                            tempStart = tempData[channel + (retDict["numChannels"] * frame)]
                            #tempLinear = np.ravel(np.transpose(tempStart))
                            #framesInOneChannel.append(np.reshape(tempLinear, (retDict["Xsize"], retDict["Ysize"])))
                            framesInOneChannel.append(tempStart.T)
                            #framesInOneChannel.append(tempData[channel + (retDict["numChannels"] * frame)])
                        chanData.append(framesInOneChannel)
                retDict["data"] = chanData
            else: # readHeader
                # processs as simple movie if faster read required without getting header info
                tempData = im.asarray()
                tempShape = np.shape(tempData)
                if len(tempShape) == 3:
                    retDict["numChannels"] = tempShape[0]
                    retDict["Xsize"] = tempShape[1]
                    retDict["Ysize"] = tempShape[2]
                    retDict["numFrames"] = 1
                else:
                    retDict["numFrames"] = 1
                    retDict["numChannels"] = 1
                    retDict["Xsize"] = tempShape[0]
                    retDict["Ysize"] = tempShape[1]
                chanData = []
                for kk in range(retDict["numChannels"]):
                    chanData.append([tempData[kk]]) # append list with one image since numFrames=1
                    channelMaxValues.append(0) # to be updated if not in fast-read mode
                retDict["data"] = chanData # assume only one frame containing one or more channels
            channelMaxValues = []
            for kk in range(retDict["numChannels"]):
                channelMaxValues.append(0) # to be updated if not in fast-read mode
            retDict["channelMaxValues"] = channelMaxValues
        except Exception as e:
            print(e)
            print("Problem reading TIFF file: " + fileName)
    else:
        print("Could not find requested TIFF file: " + fileName)
    return retDict

def _findChannelMaxValues(retDict):
    # replace dummy list of values for each channel with correct max values (99%ile)
    tempList = retDict["channelMaxValues"]
    for ff in range(retDict["numFrames"]):
        for cc in range(retDict["numChannels"]):
            # get the 99th percentile value of the pixels in each frame
            tempValue = 10 * int(np.percentile(retDict["data"][cc][ff], 99) / 10)
            #print("Max: " + str(tempValue) + "  and min " + str(np.percentile(retDict["data"][cc][ff], 1)))
            if tempValue > tempList[cc]:
                tempList[cc] = tempValue
    return tempList
