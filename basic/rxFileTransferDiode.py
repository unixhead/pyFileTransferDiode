

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

# IP address to listen on, this should be filtered by the OS or network architecture so only the transmit side can reach it. 
fileIP = "127.0.0.1"
filePort = 10337

#size of data to be transferred - TODO - make this an MTU setting
chunkSize=1300
fileNameSize=12 #size of filename field

headerStr="III"+str(fileNameSize)+"sI"
formatStr="III"+str(fileNameSize)+"sI"+str(chunkSize)+"s"
packetSize=struct.calcsize(formatStr)
headerSize = struct.calcsize(headerStr)

#name of folder to store files in 
#use the full path for this to avoid potential security issues, the filenames do get basic filtering but there's a degree of assumed trust
outputFolder = "out"

#TODO - check outfolder exists

maxPacket = 1500

#outFile="out/out" + str(random.randrange(10000000,90000000))
#fOut = open(outFile, "wb")
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind((fileIP, filePort))

def getTimeMS():
    return int(time.time()*1000)

def debugLog(data):
    print(data)



writing = False
currentFile = False


#
# Main loop
#
while True:
    message, address = serverSocket.recvfrom(packetSize)

    #currentSerial,totalPackets,fileName,dataSize = struct.unpack(headerStr, message)
    debugLog("message received " + str(len(message)) + " bytes")

    # Packet format is:
    # messageType (int) - 0 = data transfer, 1 = error
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
    # type 1 = error code
    if packetType != 0:        
        dataStr = "<" + str(dataSize) + "s"
        data = struct.unpack_from(dataStr, message, headerSize)[0]
        debugLog("ERROR: " + str(data.decode("utf-8")))
        continue # stop processing

    fileName = str(fileName.decode("utf-8")).replace('\0','') # strip out null characters from filename (padded to 12 bytes)
    debugLog("pre-filtered + " + fileName)
    fileName = fileName.replace('..','') #strip out potential parent directory command
    fileName = fileName.replace('/','') # remove path
    debugLog("receiving + " + fileName)
    debugLog(str(currentSerial) + " / " + str(totalPackets) + " - file: " + fileName + " size: " + str(dataSize))

    
    # check if creating file
    if writing == False:
        outFile = outputFolder + "/" + fileName
        debugLog("receiving " + outFile)
        # see if file already exists
        if os.path.exists(outFile): # if it does then name this file with a timestamp afterwards
            outFile = outFile + str(getTimeMS())

        fOut = open(outFile, "wb")
        writing = True
        currentFile = fileName

    dataStr = "<" + str(dataSize) + "s"
    pktSize=struct.calcsize(dataStr)
    #print("buffer size is: " + str(pktSize))


    data = struct.unpack_from(dataStr, message, headerSize)[0]
    #print("data: " + str(data))
    debugLog("writing " + str(len(data)) + " bytes")


    # check the packet is part of the current file we're writing and not an overlapping transfer
    if currentFile != fileName:
        debugLog("packet received for incorrect file")
        continue
    else:
        fOut.write(data)

    if (dataSize < chunkSize):
        debugLog("Final packet")
        fOut.close()
        writing = False
        currentFile = False

print("done")

