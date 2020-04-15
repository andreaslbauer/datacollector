# -*- coding: utf-8 -*- import os import time

#
# Python 3 Program to use temperature sensors DS18B20 on Raspberry to measure,
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
import Adafruit_ADS1x15


#
# some global variables
#

# initialize the ADS and get the access object
adc = Adafruit_ADS1x15.ADS1115()

# present the gain for each channel and compute the factor needed to compute
# the voltage value
GAINFACTOR = [4.096, 2.048, 1.024, 0.521, 0.256]
GAIN = [1, 4, 1, 1]
VOLTAGEFACTOR = [4.096 / (2.0**15)]*4
for i in range(4):
    # note: we need to offset by -1 when we look up the GAIN index
    VOLTAGEFACTOR[i] = GAINFACTOR[GAIN[i] - 1] / (2.0**15)
CALIBRATIONFACTOR = [14.3 / 1.04, -200, 14.3 / 1.04, 1]

#
# the class ADCChannel is used to keep static information about each adc channel
#
class ADCChannel:
    'Temperator sensor class with information about sensor and capability to read current value'

    # the class data
    name = ""
    channelId = 0
    gain = 1
    gainfactor = 1
    value = 0.0
    lastRead = ''

    # constructor; it initializes all data members per passed parameters
    def __init__ (self, name, channelId, gain, calibrationfactor):
        self.name = name
        self.channelId = channelId
        self.gain = 1
        self.gainfactor = (GAINFACTOR[gain - 1] / (2.0**15)) * calibrationfactor
        self.calibrationfactor = calibrationfactor
        self.value = 0.0
        self.lastRead = ''
        logging.info("Set up ADC1115 channel %s with gainfactor %s",
                     self.name, self.gainfactor)

    # print instance data.  Used for debugging and diagnosis purposes
    def dump(self):
        print("Name: %s Channel Id: %s Value: %3.2f Last Read: %s" \
        % (self.name, self.channelId, self.value, self.lastRead))

    # read the sensor
    def read(self):
        rawvalue = adc.read_adc(self.channelId, self.gain)
        value = rawvalue * self.gainfactor
        self.value = value
        dateValue = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.lastRead = dateValue
        logging.info("Read ADC Sensor %i - Raw Value: %i  Calibrated Value: %s", self.channelId, rawvalue, value)
        return value

#
# class to implement service that manages all sensors
#

class ADCService:
    'Service to manage and read temperature sensors'

    # the class data
    # list of all ADC channels
    channels = [0, 0, 0, 0]

    # constructor; it initializes all data members per passed parameters
    def __init__(self):
        self.discoverChannels()

    # print instance data.  Used for debugging and diagnosis purposes
    def dump(self):
        for channel in channels:
            channel.dump()

    # initialize to access the sensors and discover them al
    def discoverChannels(self):

        # create an ADC Channel object for the 4 channels
        for i in range(4):
            self.channels[i] = ADCChannel("Channel " + str(i), i, GAIN[i], CALIBRATIONFACTOR[i])
        
    # read the sensors

    def readChannels(self):
        for channel in self.channels:
            channel.read()

    # get the measured values
    def getValues(self):
        values = [];
        for channel in self.channels:
            values.append(channel.value)

        return values





