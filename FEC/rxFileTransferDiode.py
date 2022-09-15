

#
# THIS IS A POC ONLY AND SHOULD NOT BE USED IN PRODUCTION
#


#
# For paid support/development activities, please visit https://otnss.co.uk
#
# For open source support, please visit https://github.com/unixhead/pyFileTransferDiode
#

# rxFileTransferDiode
# Receives transfers via UDP from txFileTransferDiode.py and writes them to an output folder.
# Duplicate files get a timestamp appended to the file name
#
# Original source: https://github.com/unixhead/pyFileTransferDiode

# Beerware license


from socket import *
import os 
from os.path import exists
import random
import struct
import time
import zfec
from datetime import datetime

# IP address to listen on, this should be filtered by the OS or network architecture so only the transmit side can reach it. 
fileIP = "127.0.0.1"
filePort = 10337

#size of data to be transferred - TODO - make this an MTU setting
chunkSize=1400
fileNameSize=12 #size of filename field

headerStr="III"+str(fileNameSize)+"sI"
formatStr="III"+str(fileNameSize)+"sI"+str(chunkSize)+"s"
packetSize=struct.calcsize(formatStr)
headerSize = struct.calcsize(headerStr)

#name of folder to store files in 
#use the full path for this to avoid potential security issues, the filenames do get basic filtering but there's a degree of assumed trust
outputFolder = "out"

#TODO - check outfolder exists


#logigng configuration
logFile="test.log"
logFileHandle = open(logFile, "at")
writeLogLevel=7
printLogLevel=5

maxPacket = 1500

#outFile="out/out" + str(random.randrange(10000000,90000000))
#fOut = open(outFile, "wb")
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind((fileIP, filePort))

def getTimeMS():
    return int(time.time()*1000)


#
# debug logging
#
# levels are same as syslog but only use 3 of them:
# 0 = emerg (min)
# 5 = notice (all that might be useful)
# 7 = debug (everything)
def debugLog(data, level=0):
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    if  writeLogLevel >= level:
        timeStamp = int(time.time())
        logFileHandle.write(dt_string + " " +  data + "\n")
    if printLogLevel >= level:
        print(dt_string + " " + data) 




writing = False
currentFile = False


#
# Main loop
#
while True:
    message, address = serverSocket.recvfrom(packetSize)

    #currentSerial,totalPackets,fileName,dataSize = struct.unpack(headerStr, message)
    debugLog("packet received " + str(len(message)) + " bytes", 7)

    # Packet format is:
    # messageType (int) - 0 = data transfer, 1 = FEC transfer,  2 = last FEC packet, 69 = checksum, 99 = error
    # currentSerial (int)
    # totalPackets (int)
    # filename (char[fileNameSize])
    # dataSize (int) - size of data in this packet
    # bytes[chunkSize] - actual data

    packetType, currentSerial,totalPackets,fileName, dataSize = struct.unpack_from(headerStr, message, 0)

    if dataSize > maxPacket or dataSize < 0:
        debugLog("error in datasize")
        continue

    # packetType 0 = data transfer
    # type 99 = error code
    if packetType == 99:        
        dataStr = "<" + str(dataSize) + "s"
        data = struct.unpack_from(dataStr, message, headerSize)[0]
        debugLog("ERROR: " + str(data.decode("utf-8")), 0)
        continue # stop processing



    fileName = str(fileName.decode("utf-8")).replace('\0','') # strip out null characters from filename (padded to 12 bytes)
    #debugLog("pre-filtered + " + fileName)
    fileName = fileName.replace('..','') #strip out potential parent directory command
    fileName = fileName.replace('/','') # remove path
    debugLog("receiving + " + fileName, 7)
    debugLog(str(currentSerial) + " / " + str(totalPackets) + " - file: " + fileName + " size: " + str(dataSize), 7)

    
    # check if creating a new file
    if writing == False:
        if packetType == 1 or packetType == 2:
            debugLog("receiving FEC", 5)
            # if it's a fec then write it to outputFolder + "/temp" + filename -fec/
            tmpFecPath = outputFolder + "/" + fileName + "-fec"
            if not os.path.isdir(tmpFecPath):
                os.mkdir(tmpFecPath)

            fecList = os.listdir(tmpFecPath)
            if len(fecList) == 0:
                startTime = int(time.time())
                debugLog("starting at " + str(startTime), 7)
            outFile = tmpFecPath + "/fec" + str(len(fecList) + 1)
            debugLog("writing: " + outFile, 5)
        elif packetType == 0: 
            # if it's a regular file then write straight to the out folder
            outFile = outputFolder + "/" + fileName
            debugLog("receiving " + outFile, 5)
            # see if file already exists
            if os.path.exists(outFile): # if it does then name this file with a timestamp afterwards
                outFile = outFile + str(getTimeMS())

        fOut = open(outFile, "wb")
        writing = True
        currentFile = fileName

    # read the data bytes from the packet
    dataStr = "<" + str(dataSize) + "s"
    pktSize=struct.calcsize(dataStr)
    data = struct.unpack_from(dataStr, message, headerSize)[0]
    debugLog("writing " + str(len(data)) + " bytes to " + outFile, 7)
    

    # check the packet is part of the current file we're writing and not an overlapping transfer
    # assuming all good then write the data
    if currentFile != fileName:

        #TODO - set a timer on this as it may mean the old transfer dropped packets, so need to force close it and start on the new one
        
        debugLog("packet received for incorrect file", 0)
        continue
    else:
        fOut.write(data)
    
    # If this is the final packet then close file handles
    if (currentSerial == (totalPackets-1)):
        #debugLog("Final packet")
        fOut.close()
        writing = False
        currentFile = False

        # if it's a FEC and we've received the final FEC chunk, then need to run zunfec
        #TODO - turn this into a function so can call it from above too if we dropped packets
        if packetType == 2:
            # type 2 is the last FEC in a series
            tmpFecPath = outputFolder + "/" + fileName + "-fec"
            debugLog("reassembling " + fileName + " from fecs in " + tmpFecPath, 5)
            

            #check all files are the same size, if not then unfec will fail so delete any incorrect ones
            fecs = os.listdir(tmpFecPath)
            fecSize = 0
            for fec in fecs:
                #find biggest file, this should be same size as all of them
                curSize=os.stat(tmpFecPath + "/" + fec).st_size
                if curSize > fecSize: #last fec was too small
                    fecSize = curSize
            
            debugLog("fec size is " + str(fecSize), 7)
            
            #now delete any that are smaller than fecSize
            for fec in fecs:
                curSize=os.stat(tmpFecPath + "/" + fec).st_size
                if curSize < fecSize:
                    debugLog("fec too small, deleting :" + tmpFecPath + "/" + fec, 7)
                    os.remove(tmpFecPath + "/" + fec)

            # now try to unfec the remaining ones
            # regenerate the list increase we deleted some
            fecs = False
            fecs = os.listdir(tmpFecPath)
            
            # get file to write
            outFile = outputFolder + "/" + fileName
            if os.path.exists(outFile): # if it does then name this file with a timestamp afterwards
                outFile = outFile + str(getTimeMS())    
            fOut = open(outFile, "wb")

            # get list of handles to the FECs

            fecHandles = []
            for fec in fecs:
                fecName = tmpFecPath + "/" + fec    
                fecHandles.append(open(fecName, 'rb'))

            zfecWorked = True
            try:                
                zfec.filefec.decode_from_files(fOut, fecHandles, verbose=False)
            except:
                zfecWorked = False

            # close all the file handles
            debugLog("closing file handles to FECs", 7)
            for fecHandle in fecHandles:
                fecHandle.close()

            #check worked
            if zfecWorked:
                debugLog("Successfully wrote " + outFile, 5)
                endTime = int(time.time())
                elapsedTime=(endTime - startTime) # time in seconds
                outputSize=os.stat(outFile).st_size/1024 #size in kb
                debugLog("Transferred " + str(outputSize) + " KB in " + str(elapsedTime) + " seconds - RATE: " + str( outputSize / elapsedTime ) + " KB/s", 5)


                #delete fecs
                for fec in fecs:
                    os.remove(tmpFecPath + "/" + fec)
                
                #delete tmpfecpath
                os.rmdir(tmpFecPath)
            else:
                debugLog("unfec failed, leaving raw files in output directory " + str(tmpFecPath), 0)


print("done")

