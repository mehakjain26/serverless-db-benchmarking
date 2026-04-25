import psycopg2
import os

DB_CONFIG = {
    "host": "d5e65386-f8fc-4847-8272-f2bcabdf6bc3.0135ec03d5bf43b196433793c98e8bd5.databases.appdomain.cloud",
    "port": 31604,
    "dbname": "ibmclouddb",
    "user": "ibm_cloud_c56b4076_94db_4c14_bdea_e54446df05d2",
    "password": "mKfSwfgwlWEkwZQlvbHTCa2TNGqln2le",
    "sslmode": "verify-full",
    "sslrootcert": "ibm_postgres_ca.crt"
}

TABLES = [

"""
CREATE TABLE IF NOT EXISTS stops (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_stop_id TEXT,
    stop_name TEXT,
    stop_lat DOUBLE PRECISION,
    stop_lon DOUBLE PRECISION,
    location_type SMALLINT,
    parent_station TEXT
)
""",

"""
CREATE TABLE IF NOT EXISTS routes (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_route_id TEXT,
    route_short_name TEXT,
    route_long_name TEXT,
    route_type SMALLINT,
    route_color TEXT
)
""",

"""
CREATE TABLE IF NOT EXISTS calendar (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_service_id TEXT,
    monday BOOLEAN,
    tuesday BOOLEAN,
    wednesday BOOLEAN,
    thursday BOOLEAN,
    friday BOOLEAN,
    saturday BOOLEAN,
    sunday BOOLEAN,
    start_date TEXT,
    end_date TEXT
)
""",

"""
CREATE TABLE IF NOT EXISTS trips (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_trip_id TEXT,
    gtfs_route_id TEXT,
    gtfs_service_id TEXT,
    trip_headsign TEXT,
    direction_id SMALLINT
)
""",

"""
CREATE TABLE IF NOT EXISTS stop_times (
    id SERIAL PRIMARY KEY,
    transport_id INT,
    gtfs_trip_id TEXT,
    gtfs_stop_id TEXT,
    arrival_time INT,
    departure_time INT,
    stop_sequence INT,
    pickup_type SMALLINT,
    drop_off_type SMALLINT
)
"""

]

def main():
    # Ensure the script finds the .crt file in its own directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for sql in TABLES:
        print("Running:", sql.split("(")[0])
        cur.execute(sql)

    conn.commit()
    cur.close()
    conn.close()

    print("All tables created successfully!")

if __name__ == "__main__":
    main()