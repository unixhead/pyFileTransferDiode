# pyFileTransferDiode
File transfer over unidirectional link

THIS IS A POC - DO NOT USE IN PRODUCTION IN RAW STATE!

https://otnss.co.uk for paid support and development.
Feel free to post queries/issues here.

Requires Python 3.x

Run the txFileTransferDiode.py on the high security / North side.

Run the rxFileTransferDiode.py on the low security / South side.

May need static ARP entries if using a geniune data diode.
The South side should have filtering to avoid connectivity to the service other than by the North side, it has no inherent security features or protection.


Configurations in files for the IP addressing, folders, etc.


There are two versions:

**Basic** - this just sends each file over UDP


**FEC** - this breaks each file down to a number of smaller chunks including redundant blocks of information, so corruption of data in transfer does not result in loss of the file. Note that this can't handle dropped packets at the minute so is a bit limited, will fix that shortly! Uses [zfec](https://github.com/tahoe-lafs/zfec)


txTestGenerator.sh is used to create files and dump them into the input folder
