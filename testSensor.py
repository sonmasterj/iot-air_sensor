from lib.MultiGas import DFRobot_MultiGasSensor_I2C
from lib.asyncSleep import delay
import sys
import os
import time
import smbus
I2C_1       = 0x01               
SO2_ADDRESS = 0x74
NO2_ADDRESS = 0x75
CO_ADDRESS = 0x76     
# bus= smbus.SMBus(1)      
SO2 = DFRobot_MultiGasSensor_I2C(SO2_ADDRESS)
NO2 = DFRobot_MultiGasSensor_I2C(NO2_ADDRESS)
CO = DFRobot_MultiGasSensor_I2C(CO_ADDRESS)
so2_ppm=0
no2_ppm=0
co_ppm=0

def setup():
  #Mode of obtaining data: the main controller needs to request the sensor for data
    while (False == SO2.change_acquire_mode(SO2.PASSIVITY)):
      print("wait So2 acquire mode success!")
      delay(0.5)
    print("change SO2 mode success!")
    delay(0.5)
    while (False == NO2.change_acquire_mode(NO2.PASSIVITY)):
      print("wait No2 acquire mode success!")
      delay(1)
    print("change NO2 mode success!")
    delay(0.5)
    while (False == CO.change_acquire_mode(CO.PASSIVITY)):
      print("wait Co2 acquire mode success!")
      delay(1)
    print("change CO mode success!")
    SO2.set_temp_compensation(SO2.ON)
    NO2.set_temp_compensation(NO2.ON)
    CO.set_temp_compensation(CO.ON)
    delay(1)

def readSensor(sensor):
  i=0
  res=-1
  while i<=4:
    res= sensor.read_gas_concentration()
    delay(0.2)
    if res==-1:
      i=i+1
    else:
      break
  return res
def loop():

  so2_ppm= readSensor(SO2)
  delay(0.5)
  no2_ppm= readSensor(NO2)
  delay(0.5)
  co_ppm= readSensor(CO)
  # so2_ppm=0
  # co_ppm=0
  print("SO2={:.2f}ppm, NO2={:.2f}ppm, CO={:.2f}ppm".format(so2_ppm,no2_ppm,co_ppm))
  delay(1)  

if __name__ == "__main__":
  setup()
  while True:
    loop()
