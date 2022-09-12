

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


# how frequently to check folder for new files in seconds
pollTime=5

# Will transmit files received in the inFolder and move them to sentFolder
# To clear out sentFolder, another process is needed.
#
#use the full path for this to avoid potential security issues, the filenames do get basic filtering but there's a degree of assumed trust
inFolder="in"
sentFolder="sent"


#where to send files
sendToIP="127.0.0.1"
sendToPort=10337
fileNameSize=12 #size of filename field, you can increase this but it's put in every packet header so avoid going too large as it'll reduce throughput


#size of data to be transferred - TODO - make this an MTU setting
chunkSize=1300 # size of data in each packet


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
    txData=struct.pack(formatStr, 1 , 1, 1,errCode, len(errMsg), errMsg)
    s.sendto(txData,(sendToIP,int(sendToPort)))
    s.close()
    exit(0)


#called with a filepath/name and transmits it to the remote site.
def sendFile(fileName):
    if fileName.find(".."):
        sendError("WARNING: filename passed that contained directory traversal: " + str(fileName) + ".")

    s = socket(type=SOCK_DGRAM)
    fH = open(fileName, "rb")
    fileSize=os.stat(fileName).st_size
    debugLog("Sending file: " + str(fileName) + " - size: " + str(fileSize))
    num = int( fileSize / chunkSize) + 1
    i=0

    # build packet and transmit
    while i < num:
        # Packet format is:
        # messageType (int) - 0 = data transfer, 1 = error
        # currentSerial (int)
        # totalPackets (int)
        # filename (char[fileNameSize])
        # dataSize (int) - size of data in this packet
        # bytes[chunkSize] - actual data

        dataChunk = fH.read(chunkSize)
        
        dataSize=len(dataChunk)
        fileNameTrimmed = fileName.replace(inFolder + "/", '') # remove the path for filename value that goes into packet header
        fileNameEncoded=bytes(fileNameTrimmed,"utf-8") # will get truncated to fileNameSize when packed, or null padded if shorter
        
        txData=struct.pack(formatStr, 0 , i, num,fileNameEncoded, dataSize, dataChunk)
        s.sendto(txData,(sendToIP,int(sendToPort)))
        i+=1

    # Finished sending, close handles for file and socket
    fH.close()
    s.close()


# Main loop, watches for files appearing in the "inFolder" and then sends them. 

while True:
    #debugLog("Main loop")

    #check folders exist
    if not os.path.exists(inFolder):
        sendError("The folder : " + str(inFolder) + " does not exist, please create it or update configuration to the correct path for new files.")

    if not os.path.exists(sentFolder):
        sendError("The folder : " + str(sentFolder) + " does not exist, please create it or update configuration to the correct path for new files.")

    # look for any new folders in the inFolder
    fileList = os.listdir(inFolder)
    for file in fileList:
        if os.path.isfile(inFolder + "/" + file): # only send files in the directory, not links, other directories, etc
            debugLog("Got new file: " + str(file))
            #process it
            sendFile(inFolder + "/" + file)
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