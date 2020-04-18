#!/usr/bin/python3

# for database debugging:
# sqlite3 /tmp/data.db
# sqlite> select * from datapoints;
# sqlite> drop table datapoints;


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
from adcsensor import ADCService


#dbfilename = "/tmp/data.db"
dbfilename = "/opt/pimon/data.db"
lastRowId = 1
timeBetweenSensorReads = 180

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
        logging.info("Insert %s", row)
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
logging.basicConfig(filename="/tmp/datacollector.log", format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)


def main() :

    # log start up message
    logging.info("***************************************************************")
    logging.info("Data Collector has started")
    logging.info("Running %s", __file__)
    logging.info("Working directory is %s", os.getcwd())
    logging.info("SQLITE Database file is %s", dbfilename);

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

        # create a temperature service instance
        temperatureService = TemperatureService()

        # create a voltage service instance
        voltageService = ADCService()

        # keep running until ctrl+C
        while True:
            
            # read temperature values
            temperatureService.readSensors()
            now = datetime.datetime.now()
            nowDateTime = str(now)
            nowDate = now.strftime("%Y-%m-%d")
            nowTime = now.strftime("%H:%M:%S")

            values = temperatureService.getValues()
            sensorId = 1
            for value in values:
                row = (lastRowId + 1, sensorId, nowDate, nowTime, nowDateTime,
                       value)
                lastRowId = insertRow(mydb, row)
                sensorId = sensorId + 1


            # readvoltage values
            voltageService.readChannels()
            now = datetime.datetime.now()
            nowDateTime = str(now)
            nowDate = now.strftime("%Y-%m-%d")
            nowTime = now.strftime("%H:%M:%S")

            values = voltageService.getValues()
            for value in values:
                row = (lastRowId + 1, sensorId, nowDate, nowTime, nowDateTime,
                       value)
                lastRowId = insertRow(mydb, row)
                sensorId = sensorId + 1            
            
            # commit the DB write          

            mydb.commit()
            time.sleep(timeBetweenSensorReads)

        mydb.close()


if __name__ == '__main__':


    try:
        main()

    except Exception as e:
        logging.exception("Exception occurred in main")

    logging.info("Data Collector has terminated")




    
