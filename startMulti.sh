#!/bin/bash
network_name=$(sudo qmicli -d /dev/cdc-wdm0 --nas-get-home-network)
vietel="VIETTEL"
vina="VINAPHONE"
mobi="MOBIFONE"
vietnam="VIETNAMOBILE"
echo ${network_name^^}
sudo qmicli -d /dev/cdc-wdm0 --dms-set-operating-mode='online'
sudo ifconfig wwan0 down
echo 'Y' | sudo tee /sys/class/net/wwan0/qmi/raw_ip
case ${network_name^^} in 
    *"$vietel"*)
        printf  "use viettel network!\n"
        sudo qmicli -p -d /dev/cdc-wdm0 --device-open-net='net-raw-ip|net-no-qos-header' --wds-start-network="apn='v-internet',ip-type=4" --client-no-release-cid
    ;;
    *"$vina"*)
        printf  "use vinaphone network!\n"
        sudo qmicli -p -d /dev/cdc-wdm0 --device-open-net='net-raw-ip|net-no-qos-header' --wds-start-network="apn='m3-word',username='mms',password='mms',ip-type=4" --client-no-release-cid
    ;;
    *"$mobi"*)
        printf  "use mobifone network!\n"
        sudo qmicli -p -d /dev/cdc-wdm0 --device-open-net='net-raw-ip|net-no-qos-header' --wds-start-network="apn='m-wap',username='mms',password='mms',ip-type=4" --client-no-release-cid
    ;;
    *"$vietnam"*)
        printf  "use vietnamobile network!\n"
        sudo qmicli -p -d /dev/cdc-wdm0 --device-open-net='net-raw-ip|net-no-qos-header' --wds-start-network="apn='v-internet',ip-type=4" --client-no-release-cid
    ;;
esac
sudo udhcpc -i wwan0 -n
