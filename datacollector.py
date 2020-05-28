#!/usr/bin/python3

# Python3 code to read data from Analog Digital Converter 1115 and temperature sensos 1802 and store values in class structure
#

# logging facility: https://realpython.com/python-logging/
import logging

# sqlite3 access API
import sqlite3
from sqlite3 import Error
import os
import time
import socket
from requests import get
import datetime
from thermosensor import TemperatureService
from adc import ADCService
from lcd1602 import LCD
import relaiscontrol
import piplates.TINKERplate as tink

# dbfilename = "/tmp/data.db"
dbfilename = "/home/pi/pimon/data.db"
lastRowId = 1
timeBetweenSensorReads = 12
lcd = LCD()


# create connection to our db
def createConnection(dbFileName):
    """ create a database connection to a SQLite database """
    try:
        db = sqlite3.connect(dbFileName)
        logging.info("Connected to database %s which is version %s",
                     dbFileName, sqlite3.version)
        return db
    except Error as e:
        logging.error("Unable to create database %s", dbFileName)
        db.close()

    return None


# create database table
def createTable(mydb, createTableSql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param createTableSql: a CREATE TABLE statement
    :return:
    """
    try:
        cursor = mydb.cursor()
        cursor.execute(createTableSql)
        logging.info("Created table %s", createTableSql)
    except Error as e:
        logging.exception("Exception occurred")
        logging.error("Unable to create table %s", createTableSql)


# insert a record
def insertRow(mydb, row):
    """
    Create a new project into the projects table
    :param mydb:
    :param row:
    :return: newid
    """
    sql = ''' INSERT INTO datapoints(id, sensorid, date, time, isodatetime, value)
              VALUES(?,?,?,?,?,?) '''

    try:
        cursor = mydb.cursor()
        cursor.execute(sql, row)
        logging.debug("Insert %s", row)
        return cursor.lastrowid

    except Error as e:
        logging.exception("Exception occurred")
        logging.error("Unable to insert row %s %s", sql, row)


# get number of rows in table
def countRows(mydb):
    sql = '''select count(*) from datapoints'''
    try:
        cursor = mydb.cursor()
        result = cursor.execute(sql).fetchone()
        return result[0]

    except Error as e:
        logging.exception("Exception occurred")
        logging.error("Unable to get row count of table datapoints")

        return 0


# set up the logger
logging.basicConfig(filename="/tmp/datacollector.log", format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.INFO)


def main():
    # log start up message
    logging.info("***************************************************************")
    logging.info("Data Collector has started")
    logging.info("Running %s", __file__)
    logging.info("Working directory is %s", os.getcwd())
    logging.info("SQLITE Database file is %s", dbfilename);
    lcd.text("Data Collector", LCD.LCD_LINE_1)

    localipaddress = "IP: Unknown"
    try:
        hostname = socket.gethostname()
        externalip = get('https://api.ipify.org').text
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
        localipaddress = s.getsockname()[0]
        logging.info("Hostname is %s", hostname)
        logging.info("Local IP is %s and external IP is %s", localipaddress, externalip)
        lcd.text(localipaddress, LCD.LCD_LINE_2)

    except Exception as e:
        logging.exception("Exception occurred")
        logging.error("Unable to get network information")

    # close any open db connections

    # create connection to our database
    mydb = createConnection(dbfilename)

    if mydb is not None:
        # create table
        createTableSQL = """CREATE TABLE IF NOT EXISTS datapoints (
                                                    id integer PRIMARY KEY,
                                                    sensorid integer,
                                                    date text,
                                                    time text,
                                                    isodatetime text,
                                                    value real
                                                ); """
        createTable(mydb, createTableSQL)
        mydb.commit()

        # insert some values
        lastRowId = countRows(mydb)
        logging.info("Data points in table: %d", lastRowId)
        rowcount = lastRowId

        # create a temperature service instance
        temperatureService = None

        try:
            temperatureService = TemperatureService()
            lcd.text("Temp Service Created", LCD.LCD_LINE_2)
            time.sleep(3)

        except Error as e:
            logging.exception("Exception occurred")
            logging.error("Unable to create temperature service")
            lcd.text("Temp Service Failed", LCD.LCD_LINE_2)
            time.sleep(3)

        # create a voltage service instance
        voltageService = None

        try:
            voltageService = ADCService()
            lcd.text("ADC Service Created", LCD.LCD_LINE_1)

        except Exception as e:
            logging.exception("Exception occurred")
            logging.error("Unable to create ADC service")
            lcd.text("ADC Service Failed", LCD.LCD_LINE_1)

            # try to access TinkerPlate
        tinkerplate = None

        try:
            tinkerplate = tink
            tinkerplate.setDEFAULTS(0)
            logging.info("TinkerPlate found")
            lcd.text("TinkerPlate Created", LCD.LCD_LINE_1)

        except Exception as e:
            logging.exception("Exception occurred")
            logging.error("Unable to get Tinker Plate")
            lcd.text("TinkerPlate Failed", LCD.LCD_LINE_1)
            tinkerplate = None

            # keep running until ctrl+C
        while True:

            # toggle LED to indicate action
            if tinkerplate != None:
                try:
                    tink.setLED(0, 0)
                except Exception as e:
                    pass

            # read temperature values
            if (temperatureService != None):
                temperatureService.readSensors()
                now = datetime.datetime.now()
                nowDateTime = str(now)
                nowDate = now.strftime("%Y-%m-%d")
                nowTime = now.strftime("%H:%M:%S")

                try:

                    values = temperatureService.getValues()
                    sensorId = 1
                    for value in values:
                        row = (lastRowId + 1, sensorId, nowDate, nowTime, nowDateTime,
                               value)
                        lastRowId = insertRow(mydb, row)
                        sensorId = sensorId + 1
                        rowcount = rowcount + 1

                except Exception as e:
                    logging.exception("Exception occurred")
                    logging.error("Unable to read temperature")

            # toggle LED to indicate action
            if tinkerplate != None:
                try:
                    tink.clrLED(0, 0)
                except Exception as e:
                    pass

            # write to LCD
            lcd.text("At: " + nowTime, LCD.LCD_LINE_1)
            lcdstr1 = "T: "
            for value in values:
                lcdstr1 = lcdstr1 + "{:.2f}".format(value) + " "

            # readvoltage values
            now = datetime.datetime.now()
            nowDateTime = str(now)
            nowDate = now.strftime("%Y-%m-%d")
            nowTime = now.strftime("%H:%M:%S")

            values = []
            try:
                if (voltageService != None):
                    values = voltageService.getValues()
                    for value in values:
                        row = (lastRowId + 1, sensorId, nowDate, nowTime, nowDateTime,
                               value)
                        lastRowId = insertRow(mydb, row)
                        sensorId = sensorId + 1
                        rowcount = rowcount + 1

            except Exception as e:
                logging.exception("Exception occurred")
                logging.error("Unable to read voltage")

            # read voltage values from TinkerPlate
            try:
                if (tinkerplate != None):
                    channelid = 1
                    voltagefactors = [1220 / 220, 1220 / 220, 1333, 1]
                    values = tinkerplate.getADCall(0)
                    for value in values:
                        row = (lastRowId + 1, sensorId, nowDate, nowTime, nowDateTime,
                               value * voltagefactors[channelid - 1])
                        lastRowId = insertRow(mydb, row)
                        sensorId = sensorId + 1
                        rowcount = rowcount + 1
                        channelid = channelid + 1

            except Exception as e:
                logging.exception("Exception occurred")
                logging.error("Unable to read from TinkerPlate")

            try:
                # commit the DB write
                mydb.commit()

            except Exception as e:
                logging.exception("Exception occurred while trying to commit to DB")

            # build LCD display strings
            lcdstr2 = localipaddress
            lcdstr3 = lcdstr1
            try:
                if (len(values) > 1):
                    lcdstr2 = "{:.2f}V".format(values[0]) + " {:.2f}V".format(values[1])

                if (len(values) > 3):
                    lcdstr3 = "{:.2f}A".format(values[2]) + " {:.2f}A".format(values[3])

            except Exception as e:
                logging.exception("Exception while building LCD display strings")

            lcd.text(lcdstr1, LCD.LCD_LINE_2)
            time.sleep(timeBetweenSensorReads / 4)
            lcd.text(lcdstr1, LCD.LCD_LINE_1)
            lcd.text(lcdstr2, LCD.LCD_LINE_2)
            time.sleep(timeBetweenSensorReads / 4)
            lcd.text(lcdstr2, LCD.LCD_LINE_1)
            lcd.text(lcdstr3, LCD.LCD_LINE_2)
            time.sleep(timeBetweenSensorReads / 4)
            lcd.text(localipaddress, LCD.LCD_LINE_1)
            lcd.text("Rows:" + str(rowcount), LCD.LCD_LINE_2)

        mydb.close()

        time.sleep(3)


if __name__ == '__main__':

    try:

        main()

    except Exception as e:
        logging.exception("Exception occurred in main")

    lcd.text("Data Coll Exit", LCD.LCD_LINE_1)
    logging.info("Data Collector has terminated")

