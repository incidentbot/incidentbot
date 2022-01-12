import logging
import psycopg2

from __main__ import config
from psycopg2 import sql

logger = logging.getLogger(__name__)

"""
Base tables describes the tables that should exist within the
database
"""
base_tables = {
    "incidents": """
    CREATE TABLE incidents (
        incident_id VARCHAR(50) NOT NULL PRIMARY KEY,
        channel_id VARCHAR(50) NOT NULL,
        channel_name VARCHAR(50) NOT NULL,
        status VARCHAR(50) NOT NULL,
        severity VARCHAR(50) NOT NULL,
        bp_message_ts VARCHAR(50) NOT NULL,
        dig_message_ts VARCHAR(50) NOT NULL,
        sp_message_ts VARCHAR(50),
        sp_incident_id VARCHAR(50)
    );
    """
}


def db_bootstrap():
    """
    Verify tables
    Create what doesn't exist
    """
    # Which tables to check for
    tables = [
        "incidents",
    ]

    # Check for base tables, create the ones that don't exist
    conn = db_connect()
    if conn != None:
        for t in tables:
            try:
                # Does the table exist?
                exists = table_exists(conn, t, "public")
                # If it does, say as much and move on
                if exists:
                    logger.info(f"Table {t} already exists, so it will not be created.")
                # If it doesn't, execute a statement to create it
                else:
                    logger.info(f"Table {t} does not exist, so it will be created")
                    cursor = conn.cursor()
                    cursor.execute(base_tables[t])
                    conn.commit()
                    # Since it should have been created, verify that it was
                    exists = table_exists(conn, t, "public")
                    if exists:
                        logger.info(f"Table {t} was created.")
                    else:
                        logger.error(f"Table {t} could not be created.")
                    cursor.close()
            except psycopg2.Error as error:
                logger.error(f"Table {t} could not be created: {error}")
        conn.close()
    else:
        logger.error(f"Unable to connect to the database - is it running?")


def db_connect():
    """
    Connect to the PostgreSQL database server
    """
    conn = None
    try:
        logger.info("Connecting to database...")
        # connect to the PostgreSQL server
        conn = psycopg2.connect(
            host=config.database_host,
            database=config.database_name,
            user=config.database_user,
            password=config.database_password,
            port=config.database_port,
        )
    except (Exception, psycopg2.DatabaseError) as e:
        logger.error(f"Error connecting to database: {e}")
        exit(1)
    return conn


def db_read_incident(incident_id: str):
    """
    Read from database
    """
    conn = db_connect()
    if conn != None:
        try:
            cursor = conn.cursor()
            # Return the entry for the given incident
            query = sql.SQL("select * from {table} where {pkey} = %s").format(
                table=sql.Identifier("incidents"),
                pkey=sql.Identifier("incident_id"),
            )
            cursor.execute(query, (incident_id,))
            logger.info(f"Incident lookup query matched {cursor.rowcount} entries.")
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as error:
            logger.error(f"Incident lookup query failed for {incident_id}: {error}")
    else:
        logger.error("Unable to connect to the database - is it running?")
    return row


def db_read_all_incidents():
    """
    Return all rows from incidents table
    """
    conn = db_connect()
    if conn != None:
        try:
            cursor = conn.cursor()
            # Return the entry for the given incident
            query = sql.SQL("select * from {table}").format(
                table=sql.Identifier("incidents"),
            )
            cursor.execute(query)
            logger.info(f"Found {cursor.rowcount} entries.")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as error:
            logger.error(
                f"Incident lookup query failed when returning all incidents: {error}"
            )
    else:
        logger.error("Unable to connect to the database - is it running?")
    return rows


def db_write_incident(
    incident_id,
    channel_id,
    channel_name,
    status,
    severity,
    bp_message_ts,
    dig_message_ts,
):
    """
    Write incident entry to database

    Args:
        incident_id - The formatted channel name (title) for the incident (primary key)
        channel_id - ID of the incident channel
        channel_name - Slack channel name
        status - Status of the incident
        severity - Severeity of the incident
        bp_message_id - Boilerplate message ID
        bp_message_ts - Boilerplate message creation timestamp
        dig_message_id - Digest channel message ID
        dig_message_ts - Digest channel message creation timestamp
    """
    conn = db_connect()
    if conn != None:
        try:
            cursor = conn.cursor()
            cursor.execute(
                sql.SQL("insert into {} values (%s, %s, %s, %s, %s, %s, %s)").format(
                    sql.Identifier("incidents")
                ),
                [
                    incident_id,
                    channel_id,
                    channel_name,
                    status,
                    severity,
                    bp_message_ts,
                    dig_message_ts,
                ],
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as error:
            logger.error(f"Incident row create failed for {incident_id}: {error}")
    else:
        logger.error("Unable to connect to the database - is it running?")


def db_update_incident_sp_id_col(incident_id: str, sp_incident_id: str):
    conn = db_connect()
    if conn != None:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE incidents SET sp_incident_id=(%s)" " WHERE incident_id = (%s)",
                (
                    sp_incident_id,
                    incident_id,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as error:
            logger.error(f"Incident update failed for {incident_id}: {error}")
    else:
        logger.error("Unable to connect to the database - is it running?")


def db_update_incident_sp_ts_col(incident_id: str, ts: str):
    conn = db_connect()
    if conn != None:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE incidents SET sp_message_ts=(%s)" " WHERE incident_id = (%s)",
                (
                    ts,
                    incident_id,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as error:
            logger.error(f"Incident update failed for {incident_id}: {error}")
    else:
        logger.error("Unable to connect to the database - is it running?")


def db_update_incident_severity_col(incident_id: str, severity: str):
    conn = db_connect()
    if conn != None:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE incidents SET severity=(%s)" " WHERE incident_id = (%s)",
                (
                    severity,
                    incident_id,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as error:
            logger.error(f"Incident update failed for {incident_id}: {error}")
    else:
        logger.error("Unable to connect to the database - is it running?")


def db_update_incident_status_col(incident_id: str, status: str):
    conn = db_connect()
    if conn != None:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE incidents SET status=(%s)" " WHERE incident_id = (%s)",
                (
                    status,
                    incident_id,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as error:
            logger.error(f"Incident update failed for {incident_id}: {error}")
    else:
        logger.error("Unable to connect to the database - is it running?")


def db_verify():
    """
    Verify database is reachable
    """
    try:
        conn = db_connect()
        conn.close()
        return True
    except:
        return False


def table_exists(conn, table: str, schema: str) -> bool:
    """Take a connection, table, and schema and
    return whether or not the table exists
    """
    exists = False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT EXISTS(SELECT * FROM information_schema.tables "
            + f"WHERE table_schema='{schema}' AND "
            + f"table_name='{table}');"
        )
        exists = cursor.fetchone()[0]
        cursor.close()
    except psycopg2.Error as error:
        logger.error(f"Error reading tables: {error}")
    return exists
