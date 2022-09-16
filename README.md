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


## Forward Error Correction ##

The basic version of this code just sends the data in chunks over the wire. That can work OK, most networks are very reliable these days, however there are a few reasons why you might want something a bit more robust that is capable of coping with some data loss:
* Any particular integrity requirements, the kind of systems needing protection with diodes are usually important enough that you want accurate data.
* A large amount of data being transferred.
* The throughput has been tuned for speed (largely same as above).
* Happy to sacrifice some performance for additional reliability.

If you're just sending a small amount of data, like bytes/second, and you can cope with the occassional gap, then the simpler approach might be more appropriate. But given the potential for data loss, I'd tend to go with the FEC approach every time. 

In testing with transfers of large amounts of data, there were some losses even when using loopback interfaces with zero network loss. Because this flow is unidirectional then there's no way of signalling back to the transmitting end that packets have been missed, so your realistic options are:
* Store everything until someone manually confirms it's been transferred.
* Store everything for a set period, e.g. a week, and hope that someone validates the data each week.
* Send some kind of checksum/hash for each file and validate it (this is on the roadmap anyway!).
* Use forward error correction.

FEC is not an absolute fix, it works on a ratio of how much redundancy you want, more redundancy = more data needing to be transferred = lower throughput = less data you can actually send. Therefore it's a balancing act between the level of redundancy against the likely reliability of the systems involved, which will vary each time. There's a basic test script to help with this, which is likely to develop in future.
