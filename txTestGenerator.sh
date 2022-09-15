#!/bin/bash
#create a file full of random data between 1-501 megabytes and copy it to the input folder

INFOLDER=../in

TIME=`date +%H%M%S`
RANDNUM=$(( $RANDOM % 500 + 1 ))
echo "size: ${RANDNUM}"
dd if=/dev/urandom of=${TIME}.bin bs=1M count=$RANDNUM
mv send-${TIME}.bin ${INFOLDER}
SLEEPTIME=$(( $RANDNUM * 1.2 )) #wait before sending next file
echo "sleeping"
sleep $SLEEPTIME
./txTest.sh
