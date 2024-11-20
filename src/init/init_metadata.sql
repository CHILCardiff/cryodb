BEGIN;

CREATE TABLE units_metadata_table (
    table_name                  TEXT,
    field_name                  TEXT,
    name                        TEXT,
    unit                        TEXT,
    unit_si                     TEXT,
    unit_to_unit_si_conversion  REAL
);

-- Populate metadata table with units

-- cryoegg_data_table
INSERT INTO `units_metadata_table` VALUES
    ('cryoegg_data_table', 'conductivity', 'Conductivity', 'Siemens', 'S', 1);
INSERT INTO `units_metadata_table` VALUES
    ('cryoegg_data_table', 'temperature_pt1000', 'Temperature (PT1000)', 'Celsius', 'K', NULL);
INSERT INTO `units_metadata_table` VALUES
    ('cryoegg_data_table', 'pressure', 'Pressure', 'Bar', 'kg/m/s^2', 100000);
INSERT INTO `units_metadata_table` VALUES
    ('cryoegg_data_table', 'temperature', 'Temperature', 'Celsius', 'K', NULL);

-- cryowurst_data_table
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'temperature_tmp117', 'TMP117 Temperature', 'Celsius', 'K', NULL);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'mag_x', 'Magnetic Field Strength X', 'micro-Tesla', 'kg/s^2/A^1', 1e-6);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'mag_y', 'Magnetic Field Strength Y', 'micro-Tesla', 'kg/s^2/A^1', 1e-6);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'mag_z', 'Magnetic Field Strength Z', 'micro-Tesla', 'kg/s^2/A^1', 1e-6);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'accel_imu_x', 'IMU Acceleration X', 'Standard gravity', 'm/s^2', 0.101971621);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'accel_imu_y', 'IMU Acceleration Y', 'Standard gravity', 'm/s^2', 0.101971621);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'accel_imu_z', 'IMU Acceleration Z', 'Standard gravity', 'm/s^2', 0.101971621);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'accel_tilt_x', 'Tilt Acceleration X', 'Standard gravity', 'm/s^2', 0.101971621);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'accel_tilt_y', 'Tilt Acceleration Y', 'Standard gravity', 'm/s^2', 0.101971621);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'accel_tilt_z', 'Tilt Acceleration Z', 'Standard gravity', 'm/s^2', 0.101971621);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'pitch', 'Pitch', 'degrees', 'radian', 0.01745329251994329576923690768489);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'roll', 'Roll', 'degrees', 'radian', 0.01745329251994329576923690768489);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'conductivity', 'Conductivity', 'Siemens', 'S', 1);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'pressure', 'Pressure', 'Bar', 'kg/m/s^2', 100000);
INSERT INTO `units_metadata_table` VALUES
    ('cryowurst_data_table', 'temperature_keller', 'Temperature', 'Celsius', 'K', NULL);

-- hydrobean_data_table
INSERT INTO `units_metadata_table` VALUES
    ('hydrobean_data_table', 'conductivity', 'Conductivity', 'Siemens', 'S', 1);
INSERT INTO `units_metadata_table` VALUES
    ('hydrobean_data_table', 'pressure', 'Pressure', 'Bar', 'kg/m/s^2', 100000);
INSERT INTO `units_metadata_table` VALUES
    ('hydrobean_data_table', 'temperature', 'Temperature', 'Celsius', 'K', NULL);

COMMIT;