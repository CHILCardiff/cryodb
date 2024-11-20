import argparse
import cryodb
import flask
from flask import current_app
from flask import g
import json

# Import cryodb logger
from ..__init__ import cryodb_logger

RESPONSES = {
    "invalid_api_key" : flask.Response(
        "Invalid API key.", status = 401
    )
}

def close_cryodb(e=None):

    db = g.pop("cryodb", None)

    if db is not None:
        db.disconnect()

def get_cryodb():

    if 'cryodb' not in g:

        # Select database based on config
        if current_app.config["DATABASE"] == "sqlite" : 
            
            cryodb_logger.debug(f"Flask connecting to sqlite database at {current_app.config["CRYODB_SQLITE_PATH"]}")
            g.cryodb = cryodb.database.connect(
                path = current_app.config["CRYODB_SQLITE_PATH"],
                sqlite_create_if_not_found = current_app.config["CRYODB_SQLITE_CREATE"]
            )

        else:

            cryodb_logger.debug(f"Flask connecting to MariaDB database '{current_app.config["CRYODB_DATABASE"]}' {current_app.config["CRYODB_USER"]}@{current_app.config["CRYODB_HOST"]}:{current_app.config["CRYODB_PORT"]}")
            g.cryodb = cryodb.database.connect(
                host = current_app.config["CRYODB_HOST"],
                user = current_app.config["CRYODB_USER"],
                password = current_app.config["CRYODB_PASSWORD"],
                port = current_app.config["CRYODB_PORT"],
                database = current_app.config["CRYODB_DATABASE"]
            )
    
    # Return database connection
    return g.cryodb

def create_app(test_config = None):

    # Create cryodb_app
    cryodb_app = flask.Flask("cryodb")
    cryodb_app.config.from_object('cryodb.server.default_settings')

    # Load testing config if available
    if test_config is not None:
        cryodb_logger.debug("Loading cryodb_app in testing mode")
        cryodb_app.config.update(test_config)
        cryodb_app.config["TESTING"] = True
    # otherwise load configuration from envvar if available    
    else:
        cryodb_app.config.from_envvar('CRYODB_FLASK_CONFIG', silent=True)

    if cryodb_app.config["DEBUG"]:
        cryodb_logger.debug("Creating cryodb_app in debug mode")

    # Add DB clearup
    cryodb_app.teardown_appcontext(close_cryodb)

    # Define API routes
    @cryodb_app.route("/instrument/<type>/list", methods=["POST",])
    def list_instruments(type):

        # Validate API key 
        api_key = flask.request.args.get("key")
        if api_key is None:
            return RESPONSES["invalid_api_key"]
        
        # Get database 
        db = get_cryodb()
        
        # and permissions for key
        api_type, permissions = db.get_api_permissions(api_key)
        if api_type == None:
            return RESPONSES["invalid_api_key"]

        try:
            type = cryodb.InstrumentType(type)
        except ValueError as e:
            return flask.Response(f"Bad request - type {api_type} invalid", status=400)
        
        instruments = []
        # if the permissions are ADMIN then return all instruments
        if api_type == cryodb.APIKeyType.ADMIN:
            instruments = db.get_instruments(type=type)
        # otherwise return only those with permission to view (select)
        else: 
            instruments = db.get_instruments(id=permissions["instruments"]["select"], type=type)

        cryodb_logger.debug(f"Retrieved {len(instruments)} {type} instruments")

        response = flask.Response(json.dumps([i.to_dict() for i in instruments]), status=200, mimetype="application/json")
        return response

    @cryodb_app.route("/receiver/list", methods=["POST",])
    def list_receivers():
        # Get database
        db = get_cryodb()

        # and permissions
        api_type, permissions = db.get_api_permissions(flask.request.args.get("key"))
        if api_type is None:
            return RESPONSES["invalid_api_key"]
        
        receivers = []
        if api_type == cryodb.APIKeyType.ADMIN:
            receivers = db.get_receivers()
        else:
            receivers = db.get_receivers(id=permissions["receivers"]["select"])

        cryodb_logger.debug(f"Retrieved {len(receivers)} receivers")

        response = flask.Response(json.dumps([r.to_dict() for r in receivers]), status=200, mimetype="application/json")
        return response
        
        

    return cryodb_app


def run_cli_server():

    parser = argparse.ArgumentParser(
        prog = "cryodb-server"
    )

    cryodb_app = create_app() 
    cryodb_app.run("localhost", 3291)


if __name__ == "__main__":
    create_app()