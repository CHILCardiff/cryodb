-- populate a cryodb with a set of test instrument, receiver and campaign data

/*

Dataset outline:

Greenland [ID: 1] (2024-06-01 to 2024-07-12)

    2 x Receivers
        Receiver [ID: 10] deployed with Cryoeggs only
        Receiver [ID: 11] deployed with mix of Cryoeggs and Cryowurst

    5 x Instruments
        Cryoegg [ID: ce990001] deployed at Receiver 10 for 10 days then retrieved.
        Cryoegg [ID: ce990002] deployed at Receiver 10 until end of deployment.
        Cryoegg [ID: ce990003] deployed at Receiver 10, also received on Receiver 11 until end of deployment.
        Cryoegg [ID: ce990004] deployed at Receiver 11 deployed for 5 days.
        Cryowurst [ID: cf990010] deployed at Receiver 11 deployed.

    European [ID: 2] (2024-03-10 onwards)

    2 x Receivers
        Receiver [ID: 1] tripod receiver, originally deployed
        Receiver [ID: 20] portable receiver, deployed for a week during second summer

    4 x Instruments
        Cryoegg [ID: ce990001] deployed during drilling of initial borehole
        Cryowurst [ID: cf990001] Deployed in borehole near Receiver 20
        Cryowurst [ID: cf990002] Deployed in borehole near Receiver 20
        Cryowurst [ID: cf990003] Deployed in borehole near Receiver 20

*/

BEGIN;

INSERT INTO `campaign_table` 
    (`campaign_id`, `name`, `description`, `latitude`, `longitude`, `elevation`, `start_timestamp`, `end_timestamp`) 
    VALUES  
    -- Greenland Campaign
    (1, 'Greenland Campaign', 'A month-long test campaign in Greenland.', 70.0, -40.0, 2000, '2024-06-01 00:00:00', '2024-07-12 00:00:00'),
    -- European Campaign (ongoing)
    (2, 'European Campaign', 'An ongoing test campaign in the European Alps', 45.832728, 6.865599, 4809, '2022-03-10 00:00:00', NULL)
    -- end of campaigns
    ;

INSERT INTO `receiver_table` 
    (`receiver_id`, `name`, `type`, `manufacture_date`, `manufacture_batch`, `commission_date`)
    VALUES
    (10, 'Tripod Receiver 1', 'tripod', '2022-09-12 00:00:00', 'JJ_2022', '2022-09-12 00:00:00'),
    (11, 'Tripod Receiver 2', 'tripod', '2022-09-12 00:00:00', 'JJ_2022', '2022-09-12 00:00:00'),
    -- European campaign receiers
    (1, 'Portable Receiver 1', 'portable', '2019-06-10 00:00:00', 'Cardiff_19', '2019-06-10 00:00:00'),
    (20, 'Tripod Receiver 3', 'tripod', '2022-09-12 00:00:00', 'JJ_2022', '2022-09-12 00:00:00')
    ;

INSERT INTO `instrument_table`
    (`instrument_id`, `type`, `manufacture_date`, `manufacture_batch`, `commission_date`, `notes`, `pressure_keller_min`, `pressure_keller_max`)
    VALUES
    (3466133505, 'cryoegg', '2019-05-30 00:00:00', 'CE2019', '2019-05-30 00:00:00', 'Cryoegg with eyelet for testing', 0.0, 250.0),
    (3466133506, 'cryoegg', '2023-06-05 00:00:00', 'CE2023', '2023-06-05 00:00:00', 'Revised 23 Cryoegg for long term deployment', 0.0, 100.0),
    (3466133507, 'cryoegg', '2023-06-05 00:00:00', 'CE2023', '2023-06-05 00:00:00', 'Revised 23 Cryoegg for long term deployment', 0.0, 100.0),
    (3466133508, 'cryoegg', '2023-06-05 00:00:00', 'CE2023', '2023-06-05 00:00:00', 'Revised 23 Cryoegg for long term deployment', 0.0, 100.0),
    (3482910721, 'cryowurst', '2020-05-19 00:00:00', 'CW2020', '2020-05-19 00:00:00', 'Borehole cryowurst for European deployment with pressure sensor', 0.0, 250.0),
    (3482910722, 'cryowurst', '2020-05-19 00:00:00', 'CW2020', '2020-05-19 00:00:00', 'Borehole cryowurst for European deployment without pressure sensor', 0.0, 0.0),
    (3482910723, 'cryowurst', '2020-05-19 00:00:00', 'CW2020', '2020-05-19 00:00:00', 'Borehole cryowurst for European deployment without pressure sensor', 0.0, 0.0),
    (3482910736, 'cryowurst', '2023-02-03 00:00:00', 'CW2023', '2023-05-19 00:00:00', 'Borehole cryowurst for Greenland deployment with pressure sensor', 0.0, 100.0)
    ;

INSERT INTO `instrument_deployment_table` 
    (`description`, `campaign_id`, `instrument_id`, `start_timestamp`, `end_timestamp`)
    VALUES
    ('Test deployment of CE990001', 1, 3466133505, '2024-06-05 00:00:00', '2024-06-15 00:00:00'),
    ('Long term deployment of CE990002 at receiver 10', 1, 3466133506, '2024-06-07 13:33:00', NULL),
    ('Long term deployment of CE990003 at receiver 10', 1, 3466133507, '2024-06-07 12:47:00', NULL),
    ('Deployment of CE990004 at receiver 11', 1, 3466133508, '2024-06-07 15:21:00', '2024-06-11 10:54:00'),
    ('Deployment of CF990010 at receiver 11', 1, 3482910736, '2024-06-11 14:03:00', NULL),
    -- European deployments
    ('Test deployment of CE990001 during borehole drilling', 2, 3466133505, '2022-03-21 11:13:00', '2022-03-22 12:52:00'),
    ('50m borehole deployment of CF990001', 2, 3482910721, '2022-03-27 09:00:00', NULL),
    ('75m borehole deployment of CF990002', 2, 3482910722, '2022-03-27 09:00:00', NULL),
    ('100m borehole deployment of CF990003', 2, 3482910723, '2022-03-27 09:00:00', NULL)
    ;

INSERT INTO `receiver_deployment_table`
    (`description`, `campaign_id`, `receiver_id`, `firmware_version`, `antenna_type`, `start_timestamp`, `end_timestamp`, `original_latitude`, `original_longitude`, `original_elevation`)
    VALUES
    ('Receiver 10 deployed near moulin', 1, 10, '2.1cryoegg', 'Yagi', '2024-06-02 14:03:00', '2024-07-08 20:44:00', 69.99938, -39.99812, 2000),
    ('Receiver 11 deployed near borehole', 1, 11, '2.1cryowurst', 'Yagi', '2024-06-03 11:39:00', '2024-07-09 12:50:00', 70.00070, -40.00340, 2000),
    ('Receiver 1 deployed near borehole', 2, 1, '1.0cryowurst', 'Yagi', '2022-03-20 15:11:00', NULL, 45.833311, 6.866093, 2000),
    ('Portable receiver deployed during second summer', 2, 20, '1.0cryowurst', 'Yagi', '2023-07-01 00:00:00', '2023-07-14 00:00:00', 45.833311, 6.866093, 2000)
    ;

COMMIT;