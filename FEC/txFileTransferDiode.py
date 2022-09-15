

#
# THIS IS A POC ONLY AND SHOULD NOT BE USED IN PRODUCTION
#


#
# For paid support/development activities, please visit https://otnss.co.uk
#
# For open source support, please visit https://github.com/unixhead/pyFileTransferDiode
#

# txFileTransferDiode.py
# Detects new files in a folder (inFolder) and transmits via UDP for sending over uni-directional links
#
# Original source: https://github.com/unixhead/pyFileTransferDiode

# Beerware license


import os 
from socket import *
import struct
import time
import zfec
import math

# how frequently to check folder for new files in seconds
pollTime=5

# Will transmit files received in the inFolder and move them to sentFolder
# To clear out sentFolder, another process is needed.
#
#use the full path for this to avoid potential security issues, the filenames do get basic filtering but there's a degree of assumed trust
inFolder="in"
sentFolder="sent"

tempFolder="temp"

#where to send files
sendToIP="127.0.0.1"
sendToPort=10337
fileNameSize=12 #size of filename field, you can increase this but it's put in every packet header so avoid going too large as it'll reduce throughput


#FEC ratio - must be between 0 and 1
#This is the redundancy requirement for the forward error correction, it sets how many blocks must successfully arrive to reassemble the file
# e.g. 0.5 = 50% of blocks must arrive
# 0.8 = 80% of blocks must arrive
defaultFecRatio = 0.8
if defaultFecRatio > 1 or defaultFecRatio < 0:
    print("defaultFecRatio must be between 0 and 1, recommend set to 0.8")
    exit

#size of data to be transferred - TODO - make this an MTU setting
chunkSize=1400 # size of data in each packet

# introduced a delay between packets to lower chances of drops
# if network is a bit slower then may need to increase this, but obviously decreases throughput
packetDelay = 0.001
#delay between sending files to give remote end a chance to unzfec and tidy up
fileDelay = 0.1

#Internal variable - packet format
formatStr="III"+str(fileNameSize)+"sI"+str(chunkSize)+"s"


def debugLog(data):
    print(data)

#return unix timestamp in milliseconds
def getTimeMS():
    return int(time.time()*1000)


# Error signalling - send a fault message and quit afterwards
def sendError(error):
    error = error + "The transmitting program will now exit and need manually restarting once the error is resolved."
    debugLog("Sending error packet: " + error)
    s = socket(type=SOCK_DGRAM)
    errMsg = bytes(error,"utf-8")
    errCode = bytes("ERROR", "utf-8")
    txData=struct.pack(formatStr, 99 , 1, 1,errCode, len(errMsg), errMsg)
    s.sendto(txData,(sendToIP,int(sendToPort)))
    s.close()
    exit(0)


#called with a filepath/name and transmits it to the remote site.
def sendFile(fileName, type = 0, overrideFileName = False):
    debugLog("sendFile " + str(fileName) + " type: " + str(type))
    s = socket(type=SOCK_DGRAM)
    fH = open(fileName, "rb")
    fileSize=os.stat(fileName).st_size
    debugLog("Sending file: " + str(fileName) + " - size: " + str(fileSize))
    num = math.ceil( fileSize / chunkSize)
    i=0

    # build packet and transmit
    while i < num:
        # Packet format is:
        # messageType (int) - 0 = data transfer, 1 = FEC transfer, 2 = last FEC packet, 69 = checksum, 99 = error
        # currentSerial (int)
        # totalPackets (int)
        # filename (char[fileNameSize])
        # dataSize (int) - size of data in this packet
        # bytes[chunkSize] - actual data 

        dataChunk = fH.read(chunkSize)
        
        dataSize=len(dataChunk)
        if type == 0:
            fileNameTrimmed = fileName.replace(inFolder + "/", '') # remove the path for filename value that goes into packet header
        elif type == 1 or type == 2:
            fileNameTrimmed = overrideFileName.replace(inFolder + "/", '') # for FECS then use the original file name rather than the fec itself

        #debugLog("trimmed name: " +fileNameTrimmed)
        fileNameEncoded=bytes(fileNameTrimmed,"utf-8") # will get truncated to fileNameSize when packed, or null padded if shorter
        
        txData=struct.pack(formatStr, type , i, num,fileNameEncoded, dataSize, dataChunk)
        s.sendto(txData,(sendToIP,int(sendToPort)))
        i+=1
        #delay 1ms to try and avoid dropped packets
        time.sleep(packetDelay)

    # Finished sending, close handles for file and socket
    fH.close()
    s.close()


# uses zfec to create a bunch of FEC files, sends those over network.
def processFile(fileName):
    debugLog("Processing file " + fileName)
    # work out K & M values
    # K = how many blocks needed to recreate file
    # M = how many blocks to break file into, max 256
    
    #set using blocksPerMeg so I can play around tuning it
    blocksPerMeg = 0.1
    minBlocks = 20
    
    fileSize=os.stat(fileName).st_size
    numBlocks = int((fileSize/1024/1024) * blocksPerMeg)
    if numBlocks < minBlocks:
        numBlocks = minBlocks
    if numBlocks > 256:
        numBlocks = 256

    minGoodBlocks = int(defaultFecRatio * numBlocks)

    debugLog("sending with numBlocks: " + str(numBlocks) + " and min: " + str(minGoodBlocks))

    fH = open(fileName, "rb")
    zfec.filefec.encode_to_files(fH, fileSize, tempFolder, "tmp",  minGoodBlocks, numBlocks, ".fec", True, True)
    fecList = os.listdir(tempFolder)
    n=1
    nFecs = len(fecList)
    for fec in fecList:
        # send the FEC, last one needs to be type 2
        if n==nFecs:
            packetType = 2
        else: 
            packetType = 1
        debugLog("Sending FEC # " + str(n))
        #send it
        sendFile(tempFolder + "/" + fec, packetType, fileName)

        # delete the file
        os.remove(tempFolder + "/" + fec)

        n+=1

        # wait between transmissions => attempt to reduce dropped packets
        time.sleep(fileDelay)


# Main loop, watches for files appearing in the "inFolder" and then sends them. 

while True:
    #debugLog("Main loop")

    #check folders exist
    if not os.path.exists(inFolder):
        sendError("The folder : " + str(inFolder) + " does not exist, please create it or update configuration to the correct path for new files.")

    if not os.path.exists(sentFolder):
        sendError("The folder : " + str(sentFolder) + " does not exist, please create it or update configuration to the correct path for new files.")

    if not os.path.exists(tempFolder):
        sendError("The folder : " + str(tempFolder) + " does not exist, please create it or update configuration to the correct path for new files.")


    # look for any new folders in the inFolder
    fileList = os.listdir(inFolder)
    for file in fileList:
        if os.path.isfile(inFolder + "/" + file): # only send files in the directory, not links, other directories, etc
            debugLog("Got new file: " + str(file))

            #process it
            processFile(inFolder + "/" + file)
            

            #TODO send checksum across


            #now move it to the archive folder
            outFile = sentFolder + "/" + file
            if os.path.exists(outFile): # if it does then name this file with a timestamp afterwards
                outFile = outFile + str(getTimeMS())

            try:
                os.rename(inFolder + "/" + file, outFile)
            except PermissionError: 
                sendError("Permission error writing to the output folder.")
            except OSError as error:          
                sendError("Failed to move file to output folder, error was: " + str(error) + ".")    



    #sleep for the configured interval time
    time.sleep(pollTime)
