import board
import busio
import logging


import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


#
# class to implement service that manages all sensors
#

class ADCService:
    'Service to manage and read temperature sensors'

    # the class data
    # list of all ADC channels
    ads1 = None
    ads2 = None
    idc = None

    channels = []

    adjustmentfactors = [1.59 / 0.144, 1.59 / 0.144, -1, 1]

    # constructor; it initializes all data members per passed parameters
    def __init__(self):
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            ads1 = ADS.ADS1115(i2c, address=0x48)
            ads2 = ADS.ADS1115(i2c, address=0x49)

            channels = [AnalogIn(ads1, ADS.P0, ADS.P1),
                        AnalogIn(ads1, ADS.P2, ADS.P3),
                        AnalogIn(ads2, ADS.P0, ADS.P1),
                        AnalogIn(ads2, ADS.P2, ADS.P3)]

        except Exception as e:
            logging.exception("Exception occurred")
            logging.error("Unable to get ADC")

    # get the measured values
    def getValues(self):
        values = [];
        channelid = 0
        for channel in self.channels:
            values.append(channel.voltage * self.adjustmentfactors[channelid])
            channelid = channelid + 1

        return values

