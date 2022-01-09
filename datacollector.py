#!/usr/bin/python3

# Python3 code to read data from Analog Digital Converter 1115 and temperature sensos 1802 and store values in class structure
#

# logging facility: https://realpython.com/python-logging/
import logging

# set up the logger
logging.basicConfig(filename="/tmp/datacollector.log", format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.INFO)

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

try:
    import relaiscontrol
except BaseException as e:
    logging.error("Unable to import relais control - not running on Raspberry PI?")

try:
    from einkdisplay import eink

except Exception as e:
    logging.error("Unable to import Waveshare eink modules")

try:
    import piplates.TINKERplate as tink

except Exception as e:
    logging.error("Unable to import piplates modules")

# dbfilename = "/tmp/data.db"
dbfilename = "/home/pi/pimon/data.db"
lastRowId = 1
timeBetweenSensorReads = 5
numberOfSensors = 0

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


def main():
    # log start up message
    logging.info("***************************************************************")
    logging.info("Data Collector has started")
    logging.info("Running %s", __file__)
    logging.info("Working directory is %s", os.getcwd())
    logging.info("SQLITE Database file is %s", dbfilename);

    localipaddress = "IP: Unknown"
    try:
        hostname = socket.gethostname()
        externalip = get('https://api.ipify.org').text
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
        localipaddress = s.getsockname()[0]
        logging.info("Hostname is %s", hostname)
        logging.info("Local IP is %s and external IP is %s", localipaddress, externalip)

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

        except Error as e:
            logging.error("Unable to create temperature service")

        # create a voltage service instance
        voltageService = None

        try:
            voltageService = ADCService()

        except Exception as e:
            logging.error("Unable to create ADC service")

        # try to access TinkerPlate
        tinkerplate = None

        try:
            tinkerplate = tink
            tinkerplate.setDEFAULTS(0)
            logging.info("TinkerPlate found")

        except Exception as e:
            logging.error("Unable to get Tinker Plate")
            tinkerplate = None

        # counter for measurement iterations
        iteration = 1

        # initialize eink display, if present
        einkDisplay = None
        try:
            einkDisplay = eink()
            einkDisplay.initDisplay()

        except Exception as e:
            logging.error("Unable to get eink display")

        data = []
        if temperatureService != None:
            for sensor in temperatureService.sensors:
                data.append([])

        # keep running until ctrl+C
        while True:
            # increase iteration count
            iteration = iteration + 1

            # toggle LED to indicate action
            if tinkerplate != None:
                try:
                    tink.setLED(0, 0)

                except Exception as e:
                    pass

            # read temperature values
            dataSetIndex = 0
            if (temperatureService != None):
                tempsString = ""
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
                        rowcount = rowcount + 1
                        tempsString = tempsString + str(value) + " "
                        data[sensorId - 1].append(value)

                        # keep length of items to show in chart to less than 120
                        while (len(data[sensorId - 1]) > 120):
                            data[sensorId - 1].pop(0)

                        sensorId = sensorId + 1

                except Exception as e:
                    logging.error("Unable to read temperature")

                #logging.info("Iteration: %d Temperature data: %s", iteration, tempsString)
                if einkDisplay != None:
                    einkDisplay.displayTemps(values, data)

            # toggle LED to indicate action
            if tinkerplate != None:
                try:
                    tink.clrLED(0, 0)
                except Exception as e:
                    pass

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
                logging.error("Unable to read voltage")

            # read voltage values from TinkerPlate
            try:
                if (tinkerplate != None):
                    channelid = 1
                    #voltagefactors = [1220 / 220, 1220 / 220, 1333, 1]
                    voltagefactors = [1220 / 220, 1220 / 220, 1, 1]
                    values = tinkerplate.getADCall(0)
                    for value in values:
                        row = (lastRowId + 1, sensorId, nowDate, nowTime, nowDateTime,
                               value * voltagefactors[channelid - 1])
                        lastRowId = insertRow(mydb, row)
                        sensorId = sensorId + 1
                        rowcount = rowcount + 1
                        channelid = channelid + 1

            except Exception as e:
                logging.error("Unable to read from TinkerPlate")

            try:
                # commit the DB write
                mydb.commit()

            except Exception as e:
                logging.exception("Exception occurred while trying to commit to DB")

            time.sleep(7)

        mydb.close()

        if einkDisplay != None:
            einkDisplay.turnOff()

        logging.info("Data Collector main loop has terminated, database is closed")

# main program
if __name__ == '__main__':

    try:

        main()

    except Exception as e:
        logging.exception("Exception occurred in main")

    logging.info("Data Collector has terminated")

