# -*- coding: utf-8 -*- import os import time

#
# Python 2 Program to use temperature sensors DS18B20 on Raspberry to measure,
# temperature values.  The program automatically discovers all sensors on W1.  It
# measures data every 5 s second, displays the data and also attemptsa to send to
# a web service (seperate project)
# Author:  Andreas Bauer
# e-mail:  fastberrypi@gmail.com
# Last update: 4/21/2017

#import os and time modules
import os
import time
import datetime
import logging


#
# some global variables
#

# path for devices on W1 on the system bus
devicePath = '/sys/bus/w1/devices/'

# start id value.  The ID count is incremented for each data record sent to the web service
idCount = 100

#
# the class TempSensor is used to keep static information about each temperature sensor
# and offers a method to access the current value
#
class TempSensor:
    'Temperator sensor class with information about sensor and capability to read current value'

    # the class data
    name = ''
    fullPath = ''
    niceName = ''
    value = 0.0
    lastRead = ''

    # constructor; it initializes all data members per passed parameters
    def __init__ (self, name, fullPath, niceName):
        self.name = name
        self.fullPath = fullPath
        self.niceName = niceName
        self.value = 0.0
        self.lastRead = ''

    # print instance data.  Used for debugging and diagnosis purposes
    def dump(self):
        print("Name: %s Full Path: %s Nice Name: %s Value: %3.2f Last Read: %s" \
        % (self.name, self.fullPath, self.niceName, self.value, self.lastRead))

    # read temperature from file in raw format
    def tempFileRead(self):
        f = open(self.fullPath, 'r')
        lines = f.readlines()
        f.close()
        return lines

    # read the sensor
    def read(self):

        try:
            # read the sensor file
            lines = []
            attempts = 0
            while (len(lines) == 0) and attempts < 32:
                lines = self.tempFileRead()
                attempts = attempts + 1

            if len(lines) > 0:
                # wait until new data is available
                while lines[0].strip()[-3:] != 'YES':
                    time.sleep(0.2)
                    lines = self.tempFileRead()

                # get the relevant portion of the file content
                temp_output = lines[1].find('t=')

                if temp_output != -1:
                    temp_string = lines[1].strip()[temp_output+2:]
                    temp_c = float(temp_string) / 1000.0
                    temp_f = temp_c * 9.0 / 5.0 + 32.0
                    self.value = temp_f
                    dateValue = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.lastRead = dateValue
                    return temp_f

        except Exception as e:
            logging.exception("Exception occurred while reading temperature")
            logging.error(e)

        return 0

#
# class to implement service that manages all sensors
#

class TemperatureService:
    'Service to manage and read temperature sensors'

    # the class data
    # list of all temperature sensors
    sensors = []

    # constructor; it initializes all data members per passed parameters
    def __init__(self):
        self.discoverSensors()

    # print instance data.  Used for debugging and diagnosis purposes
    def dump(self):
        for sensor in self.sensors:
            sensor.dump()

    # get the number of sensors
    def numberOfSensors(self):
        return len(sensors)

    # initialize to access the sensors and discover them al
    def discoverSensors(self):

        count = 0
        try:
        
            # load kernel modules
            os.system('modprobe w1-gpio')
            os.system('modprobe w1-therm')

            # get the contents of the bus directory.  listdir will give us a list of all sensor file names.
            sensorFileNames = os.listdir(devicePath);

            for sensorFileName in sensorFileNames:

                # our sensor has the prefix "28-"
                if '28-' in sensorFileName:
                    count += 1

                    fullPath = devicePath + sensorFileName + '/w1_slave'
                    newNiceName = 'Sensor ' + str(count)

                    newSensor = TempSensor(sensorFileName, fullPath, newNiceName)
                    self.sensors.append(newSensor)

                    logging.info("Discovered temperature sensor %s", fullPath)

        except Exception as e:
            logging.exception("Exception occurred while initializing sensor")
            logging.error(e)

        logging.info("Detected %d DS18B20 temperature sensors", count)
            
    # read the sensors
    def readSensors(self):
        for sensor in self.sensors:
            sensor.read()

    # get the measured values
    def getValues(self):
        values = [];
        for sensor in self.sensors:
            values.append(sensor.value)

        return values





