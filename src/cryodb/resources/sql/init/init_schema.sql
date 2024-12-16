BEGIN;

CREATE TABLE process_table (
    process_id          INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    type                TEXT, -- one-off or continuous
    level               INTEGER UNSIGNED,
    timestamp_begin     TEXT,
    timestamp_end       TEXT,
    notes               TEXT
);    

CREATE TABLE instrument_table (
    instrument_id       INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    type                TEXT NOT NULL,
    manufacture_date    TEXT,
    manufacture_batch   TEXT,
    commission_date     TEXT,
    notes               TEXT,
    pressure_keller_min REAL NOT NULL DEFAULT 0,
    pressure_keller_max REAL NOT NULL
);

CREATE TABLE receiver_table (
    receiver_id         INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    name       TEXT NOT NULL, 
    type       TEXT NOT NULL,
    imei_number         TEXT, -- associated with the Iridium receiver
    manufacture_date    TEXT,
    manufacture_batch   TEXT,
    commission_date     TEXT,
    notes               TEXT
);

CREATE TABLE campaign_table (
    campaign_id         INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    name                TEXT NOT NULL, -- i.e. SLIDE2024, Donkey!
    description         TEXT,
    -- location fields
    latitude            REAL, 
    longitude           REAL,
    elevation           REAL,
    -- dates
    start_timestamp     TEXT,
    end_timestamp       TEXT
);

CREATE TABLE instrument_deployment_table (
    deployment_id       INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    description         TEXT, -- i.e. location of the moulin the instrument was deployed in 
    campaign_id         INTEGER UNSIGNED,
    instrument_id       INTEGER UNSIGNED,
    start_timestamp     TEXT NOT NULL,
    end_timestamp       TEXT,
    -- Assign foreign keys
    FOREIGN KEY (campaign_id) REFERENCES campaign_table(campaign_id),
    FOREIGN KEY (instrument_id) REFERENCES instrument_table(instrument_id)
);

CREATE TABLE receiver_deployment_table (
    deployment_id       INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    description         TEXT, -- i.e. location of borehole the receiver is near
    campaign_id         INTEGER UNSIGNED,
    receiver_id         INTEGER UNSIGNED,
    firmware_version    TEXT,
    antenna_type        TEXT,
    start_timestamp     TEXT NOT NULL,
    end_timestamp       TEXT,
    service_timestamp   TEXT, -- date of last service
    -- location fields
    original_latitude   REAL,
    original_longitude  REAL,
    original_elevation  REAL,
    latest_latitude     REAL,
    latest_longitude    REAL,
    latest_elevation    REAL,
    -- Assign foreign keys
    FOREIGN KEY (campaign_id) REFERENCES campaign_table(campaign_id),
    FOREIGN KEY (receiver_id) REFERENCES receiver_table(receiver_id)
);

-- CREATE TABLES
CREATE TABLE ingest_event_table (
    ingest_event_id     INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    ingest_type         TEXT NOT NULL, -- enum of [test, lingomo, sdcard, local, manual]
    account_id          TEXT, -- accountId in 'identity' of LingoMO messages
    description         TEXT,
    timestamp           TEXT NOT NULL    -- time started?
);   

CREATE TABLE ingest_table (
    ingest_id           INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    ingest_event_id     INTEGER UNSIGNED NOT NULL,
    raw                 BLOB NOT NULL,
    -- Assign foreign keys
    FOREIGN KEY (ingest_event_id) REFERENCES ingest_event_table(ingest_event_id)
);

CREATE TABLE ingest_lingomo_table (
    ingest_id           INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    lingomo_id          TEXT, -- unique identifier of LingoMO obj from Cloudloop
    received_timestamp  TEXT,
    imei                TEXT,
    serial              TEXT, -- same as ThingID (i.e. RockBlock+216143)
    momsn               INTEGER UNSIGNED,
    latitude            REAL,
    longitude           REAL,
    accuracy            REAL,
    -- Assign foreign keys
    FOREIGN KEY (ingest_id) REFERENCES ingest_table(ingest_id)
);

-- no SD ingest needed

CREATE TABLE ingest_localpacket_table (
    ingest_id           INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    local_timestamp     TEXT,
    -- Assign foreign keys
    FOREIGN KEY (ingest_id) REFERENCES ingest_table(ingest_id)
);

CREATE TABLE ingest_manual_table(
    ingest_id           INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    metadata            TEXT,    
    -- Assign foreign keys
    FOREIGN KEY (ingest_id) REFERENCES ingest_table(ingest_id)
); -- this should be able to record unique metadata/notes for each ingest

CREATE TABLE receiver_data_table (
    receiver_data_id    INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    receiver_id         INTEGER UNSIGNED NOT NULL,
    ingest_id           INTEGER UNSIGNED NOT NULL,
    timestamp           TEXT NOT NULL,
    channel             INTEGER UNSIGNED,
    temperature_logger  REAL,
    pressure_logger     REAL,
    voltage_logger      REAL,
    -- Assign foreign keys
    FOREIGN KEY (receiver_id) REFERENCES receiver_table(receiver_id),
    FOREIGN KEY (ingest_id) REFERENCES ingest_table(ingest_id)
);

CREATE TABLE cryoegg_raw_table (
    cryoegg_raw_id          INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    receiver_data_id        INTEGER UNSIGNED,
    ingest_id               INTEGER UNSIGNED,
    instrument_id           INTEGER UNSIGNED,
    conductivity_raw        INTEGER,
    temperature_pt1000_raw  INTEGER,
    pressure_raw            INTEGER,
    temperature_raw         INTEGER,
    battery_voltage         INTEGER,
    sequence_number         INTEGER,
    rssi                    REAL,
    packet_version          TEXT, -- C0 or C1 current valid values
    -- Assign foreign keys
    FOREIGN KEY (ingest_id)         REFERENCES ingest_table(ingest_id),
    FOREIGN KEY (receiver_data_id)  REFERENCES receiver_data_table(receiver_data_id),
    FOREIGN KEY (instrument_id)     REFERENCES instrument_table(instrument_id)
);

CREATE TABLE cryowurst_raw_table (
    cryowurst_raw_id        INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    receiver_data_id        INTEGER UNSIGNED,
    ingest_id               INTEGER UNSIGNED,
    instrument_id           INTEGER UNSIGNED,
    temperature_tmp117_raw  INTEGER,
    mag_x_raw               INTEGER,
    mag_y_raw               INTEGER,
    mag_z_raw               INTEGER,
    accel_imu_x_raw         INTEGER,
    accel_imu_y_raw         INTEGER,
    accel_imu_z_raw         INTEGER,
    accel_tilt_x_raw        INTEGER,
    accel_tilt_y_raw        INTEGER,
    accel_tilt_z_raw        INTEGER,
    pitch_raw               INTEGER,
    roll_raw                INTEGER,
    conductivity_raw        INTEGER,
    pressure_raw            INTEGER,
    temperature_keller_raw  INTEGER,
    battery_voltage         INTEGER,
    sequence_number         INTEGER,
    rssi                    REAL,
    packet_version          TEXT, -- W1 or W2 current valid values
    -- Assign foreign keys
    FOREIGN KEY (ingest_id)         REFERENCES ingest_table(ingest_id),
    FOREIGN KEY (receiver_data_id)  REFERENCES receiver_data_table(receiver_data_id),
    FOREIGN KEY (instrument_id)     REFERENCES instrument_table(instrument_id)
);

CREATE TABLE hydrobean_raw_table (
    hydrobean_raw_id    INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    receiver_data_id    INTEGER UNSIGNED,
    ingest_id           INTEGER UNSIGNED,
    instrument_id       INTEGER UNSIGNED,
    conductivity_raw    INTEGER,
    pressure_raw        INTEGER,
    temperature_raw     INTEGER,
    battery_voltage     INTEGER,
    sequence_number     INTEGER,
    rssi                REAL,
    packet_version      TEXT, -- ?? current valid values
    -- Assign foreign keys
    FOREIGN KEY (ingest_id)         REFERENCES ingest_table(ingest_id),
    FOREIGN KEY (receiver_data_id)  REFERENCES receiver_data_table(receiver_data_id),
    FOREIGN KEY (instrument_id)     REFERENCES instrument_table(instrument_id)
);

CREATE TABLE cryoegg_data_table (
    cryoegg_data_id     INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    cryoegg_raw_id      INTEGER UNSIGNED,
    process_id          INTEGER UNSIGNED,
    conductivity        REAL,
    temperature_pt1000  INT,
    pressure            REAL,
    temperature         REAL,
    -- Assign foreign keys
    FOREIGN KEY (cryoegg_raw_id)    REFERENCES cryoegg_raw_table(cryoegg_raw_id),
    FOREIGN KEY (process_id)        REFERENCES process_table(process_id)
);

CREATE TABLE cryowurst_data_table (
    cryowurst_data_id   INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    cryowurst_raw_id    INTEGER UNSIGNED,
    process_id          INTEGER UNSIGNED,
    temperature_tmp117  REAL,
    mag_x               REAL,   
    mag_y               REAL,
    mag_z               REAL,
    accel_imu_x         REAL,
    accel_imu_y         REAL,
    accel_imu_z         REAL,
    accel_tilt_x        REAL,
    accel_tilt_y        REAL,
    accel_tilt_z        REAL,
    pitch               REAL,
    roll                REAL,
    conductivity        REAL,
    pressure            REAL,
    temperature_keller  REAL,
    -- Assign foreign keys
    FOREIGN KEY (cryowurst_raw_id)  REFERENCES cryowurst_raw_table(cryowurst_raw_id),
    FOREIGN KEY (process_id)        REFERENCES process_table(process_id)
);

CREATE TABLE hydrobean_data_table (
    hydrobean_data_id   INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    hydrobean_raw_id    INTEGER UNSIGNED,
    process_id          INTEGER UNSIGNED,
    conductivity        REAL,
    pressure            REAL,
    temperature         REAL,
        -- Assign foreign keys
    FOREIGN KEY (hydrobean_raw_id)  REFERENCES hydrobean_raw_table(hydrobean_raw_id),
    FOREIGN KEY (process_id)        REFERENCES process_table(process_id)
);

CREATE TABLE calibration_table (
    calibration_id              INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    instrument_id               INTEGER UNSIGNED,
    timestamp                   REAL,
    temperature_scale           REAL,
    temperature_offset          REAL,
    tmp117_scale                REAL,
    Tmp117_offset               REAL,
    pressure_min                REAL,
    pressure_max                REAL,
    mag_cal_scale_xx            REAL,
    mag_cal_scale_xy            REAL,
    mag_cal_scale_xz            REAL,
    mag_cal_scale_yx            REAL,
    mag_cal_scale_yy            REAL,
    mag_cal_scale_yz            REAL,
    mag_cal_scale_zx            REAL,
    mag_cal_scale_zy            REAL,
    mag_cal_scale_zz            REAL,
    mag_cal_offset_x            REAL,
    mag_cal_offset_y            REAL,
    mag_cal_offset_z            REAL,
    accel_imu_cal_scale_xx      REAL,
    accel_imu_cal_scale_xy      REAL,
    accel_imu_cal_scale_xz      REAL,
    accel_imu_cal_scale_yx      REAL,
    accel_imu_cal_scale_yy      REAL,
    accel_imu_cal_scale_yz      REAL,
    accel_imu_cal_scale_zx      REAL,
    accel_imu_cal_scale_zy      REAL,
    accel_imu_cal_scale_zz      REAL,
    accel_imu_cal_offset_x      REAL,
    accel_imu_cal_offset_y      REAL,
    accel_imu_cal_offset_z      REAL,
    accel_tilt_cal_scale_xx     REAL,
    accel_tilt_cal_scale_xy     REAL,
    accel_tilt_cal_scale_xz     REAL,
    accel_tilt_cal_scale_yx     REAL,
    accel_tilt_cal_scale_yy     REAL,
    accel_tilt_cal_scale_yz     REAL,
    accel_tilt_cal_scale_zx     REAL,
    accel_tilt_cal_scale_zy     REAL,
    accel_tilt_cal_scale_zz     REAL,
    accel_tilt_cal_offset_x     REAL,
    accel_tilt_cal_offset_y     REAL,
    accel_tilt_cal_offset_z     REAL,
    pitch_scale                 REAL,
    pitch_offset                REAL,
    roll_scale                  REAL,
    roll_offset                 REAL,
    FOREIGN KEY (instrument_id)     REFERENCES instrument_table(instrument_id)
);

CREATE TABLE conductivity_calibration_table (
    calibration_id  INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL,
    voltage         INTEGER UNSIGNED,
    conductivity    REAL,
    temperature     REAL,
    FOREIGN KEY (calibration_id) REFERENCES calibration_table(calibration_id)
);   
COMMIT;