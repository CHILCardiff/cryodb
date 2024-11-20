import cryodb

# Libraries for import required for testing
import datetime
import os
import pathlib
import pytest

# import common test parameters
from .config import *

def __test_campaign_workflow(db : cryodb.CryoDatabase):

    # Setup test by deleting any objects to be created
    cursor = db.cursor()

    # Create a new campaign
    campaign_id = db.add_campaign("test_campaign", "test campaign", 69.9, -30.3, start_timestamp = datetime.datetime.now(tz=datetime.timezone.utc))

    print(f"Added campaign with ID [{campaign_id}]")

    # Add an instrument
    instrument_one_id = db.add_instrument("ce990001", cryodb.InstrumentType.Cryoegg, 30.0)
    # Add a receiver
    receiver_one_id = db.add_receiver("99000001", cryodb.ReceiverType.PORTABLE, receiver_name="Cardiff Portable Receiver #1")
    
    # Add a deployment
    instr_deployment_id = db.add_instrument_deployment(
        campaign_id = campaign_id,
        instrument_id = instrument_one_id,
        start_timestamp = datetime.datetime(2024, 1, 15, tzinfo=datetime.timezone.utc),
        description = "example deployment of instrument on campaign"
    )

    rcvr_deployment_id = db.add_receiver_deployment(
        campaign_id = campaign_id,
        receiver_id = receiver_one_id,
        start_timestamp = datetime.datetime(2024, 1, 15, tzinfo=datetime.timezone.utc),
        antenna_type = "yagi",
        description = "receiver deployed on small hill above moulin",
    )

    # # Try adding the same instrument, without an end date
    # with pytest.raises(cryodb.AlreadyDeployedError):
    #     db.add_instrument_deployment(
    #         campaign_id = campaign_id,
    #         instrument_id = instrument_one_id,
    #         start_timestamp = datetime.datetime(2024, 1, 15, tzinfo=datetime.timezone.utc),
    #         description = "example deployment of instrument on campaign"
    #     )

    # Update deployment information
    db.update_instrument_deployment(
        deployment_id = instr_deployment_id,
        end_timestamp = datetime.datetime(2024, 1, 15, tzinfo=datetime.timezone.utc)
    )

    # Now add the same instrument but deployed at a later date
    db.add_instrument_deployment(
        campaign_id = campaign_id,
        instrument_id = instrument_one_id,
        start_timestamp = datetime.datetime(2024, 2, 1, tzinfo=datetime.timezone.utc),
        description = "a second deployment of instrument one"
    )

    # with pytest.raises(cryodb.AlreadyDeployedError):
    #     db.add_receiver_deployment(
    #         campaign_id = campaign_id,
    #         instrument_id = instrument_one_id,
    #         start_timestamp = datetime.datetime(2024, 1, 15, tzinfo=datetime.timezone.utc),
    #         description = "example deployment of instrument on campaign"
    #     )

    # Update deployment information
    db.update_receiver_deployment(
        deployment_id = rcvr_deployment_id,
        end_timestamp = datetime.datetime(2024, 1, 20, tzinfo=datetime.timezone.utc)
    )

    db.add_receiver_deployment(
        campaign_id = campaign_id,
        receiver_id = receiver_one_id,
        start_timestamp = datetime.datetime(2024, 2, 1, tzinfo=datetime.timezone.utc),
        description = "a second deployment of receiver on"
    )

    # Cleanup
    cursor.execute("DELETE FROM `receiver_deployment_table` WHERE `deployment_id` = ?;", (rcvr_deployment_id,))
    cursor.execute("DELETE FROM `instrument_deployment_table` WHERE `deployment_id` = ?;", (instr_deployment_id,))
    cursor.execute("DELETE FROM `receiver_table` WHERE `receiver_id` = ?;", (receiver_one_id,))
    cursor.execute("DELETE FROM `instrument_table` WHERE `instrument_id` = ?;", (instrument_one_id,))
    cursor.execute("DELETE FROM `campaign_table` WHERE `campaign_name` = 'test_campaign';")
    
def test_campaign_workflow(db_mariadb, db_sqlite):

    __test_campaign_workflow(db_mariadb)
    __test_campaign_workflow(db_sqlite)