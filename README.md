# pyFileTransferDiode
File transfer over unidirectional link

THIS IS A POC - DO NOT USE IN PRODUCTION IN RAW STATE!

https://otnss.co.uk for paid support and development.
Feel free to post queries/issues here.

Run the txFileTransferDiode.py on the high security / North side.
Run the rxFileTransferDiode.py on the low security / South side.

May need static ARP entries if using a geniune data diode.
The South side should have filtering to avoid connectivity to the service other than by the North side, it has no inherent security features or protection.


Configurations in files for the IP addressing, folders, etc.
