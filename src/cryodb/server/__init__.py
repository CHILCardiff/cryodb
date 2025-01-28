import argparse
import cryodb
import datetime
import flask
from flask import current_app
from flask import g
from flask import request
import importlib.resources
import ipaddress
import json
import tomllib
# Import for ProxyFix if using a reverse proxy
from werkzeug.middleware.proxy_fix import ProxyFix

# Import cryodb logger
from ..__init__ import cryodb_logger

class CryodbResponse(flask.Response):
    default_mimetype = "application/json"

class CryodbErrorResponse(CryodbResponse):

    def __init__(self, exception, status=500, message="", **kwargs):

        if not isinstance(exception, Exception):
            self.exception_name = "Error"
        else:
            self.exception_name = exception.__class__.__name__
            self.exception_message = str(exception) if message == "" else message

        # Create response from exception information
        data = {
            "error" : {
                "name"      : self.exception_name,
                "message"   : self.exception_message,
                "timestamp" : str(datetime.datetime.now())
            }
        }

        super().__init__(response=data, status=status, mimetype="application/json", **kwargs)

def close_cryodb(e=None):

    db = g.pop("cryodb", None)

    if db is not None:
        db.disconnect()

def get_cryodb():

    if 'cryodb' not in g:

        # Select database based on config
        if current_app.config["DATABASE"] == "sqlite" : 
            
            cryodb_logger.debug(f"Flask connecting to sqlite database at {current_app.config['CRYODB_SQLITE_PATH']}")
            g.cryodb = cryodb.database.connect(
                path = current_app.config["CRYODB_SQLITE_PATH"],
                sqlite_create_if_not_found = current_app.config["CRYODB_SQLITE_CREATE"]
            )

        else:

            cryodb_logger.debug(f"Flask connecting to MariaDB database '{current_app.config['CRYODB_DATABASE']}' {current_app.config['CRYODB_USER']}@{current_app.config['CRYODB_HOST']}:{current_app.config['CRYODB_PORT']}")
            g.cryodb = cryodb.database.connect(
                host = current_app.config["CRYODB_HOST"],
                user = current_app.config["CRYODB_USER"],
                password = current_app.config["CRYODB_PASSWORD"],
                port = current_app.config["CRYODB_PORT"],
                database = current_app.config["CRYODB_DATABASE"]
            )
    
    # Return database connection
    return g.cryodb

###############################################################################
# Authentication logic to handle IP authentication types
###############################################################################
def validate_api_key():
    """
    :raise ValueError: if the IP address is invalid, then a ValueError is raised.  Should result in a 400 status code.
    :raise InvalidAPIKeyError: if the API key is invalid.


    """
    # Check if we're in a request
    if not flask.has_request_context():
        raise Exception("Validating API key outside of request.")

    # Get db object
    db = get_cryodb()

    # Get API key from HTTP headers
    api_key = flask.request.args.get("key")
    # if the header is empty, lookup if we have an IP key
    if api_key == None:
        # Check whether we have an API key available
        # ! Raises ValueError if IP address is invalid !
        ip = ipaddress.ip_address(request.remote_addr)
        api_type, permissions = db.get_api_permissions(ip=str(ip))
    # else if the key is provided in the header, validate that
    else:
        # Check if we're using an IP authentication type
        api_type, permissions = db.get_api_permissions(key=api_key)

    # No such key exists if API key is returned
    if api_type == None:
        raise cryodb.InvalidAPIKeyError()
    else:
        return api_type, permissions

###############################################################################
# Define app initialisation and HTTP routes
###############################################################################
def create_app(test_config = None):

    # Create cryodb_app
    cryodb_app = flask.Flask("cryodb")
    cryodb_app.config.from_file(importlib.resources.files("cryodb") / "default_settings.toml", load=tomllib.load, text=False)

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

    # Add proxy if configured
    if cryodb_app.config["REVERSE_PROXY"]:
        # Configure app behind proxy
        #
        # ProxyFix documentation from Werkzeug
        #   https://werkzeug.palletsprojects.com/en/stable/middleware/proxy_fix/
        #
        #   x_for (int) - Number of values to trust for X-Forwarded-For.
        #   x_proto (int) - Number of values to trust for X-Forwarded-Proto.
        #   x_host (int) - Number of values to trust for X-Forwarded-Host.
        #   x_port (int) - Number of values to trust for X-Forwarded-Port.
        #   x_prefix (int) - Number of values to trust for X-Forwarded-Prefix.
        cryodb_app.wsgi_app = ProxyFix(
            cryodb_app.wsgi_app,
            # Get settings from configuration --------------------- 
            x_for    = cryodb_app.config["REVERSE_PROXY_X_FOR"], 
            x_proto  = cryodb_app.config["REVERSE_PROXY_X_PROTO"], 
            x_host   = cryodb_app.config["REVERSE_PROXY_X_HOST"],
            x_port   = cryodb_app.config["REVERSE_PROXY_X_PORT"], 
            x_prefix = cryodb_app.config["REVERSE_PROXY_X_PREFIX"]
        )

    ###########################################################################
    # Define API routes
    ###########################################################################
    @cryodb_app.route("/alive", methods=["GET",])
    def alive():
        return CryodbResponse({"message" : "Hello, world!"})


    @cryodb_app.route("/instrument/<type>/list", methods=["GET",])
    def list_instruments(type):

        # Validate API
        try:
            api_type, permissions = validate_api_key()
        except cryodb.InvalidAPIKeyError as e:
            return CryodbErrorResponse(e, 401, "Invalid API key.")
        
        # Get DB object
        db = get_cryodb()

        try:
            type = cryodb.InstrumentType(type)
        except ValueError as e:
            return CryodbErrorResponse(e, status=400)
        
        instruments = []
        # if the permissions are ADMIN then return all instruments
        if api_type == cryodb.APIKeyType.ADMIN:
            instruments = db.get_instruments(type=type)
        # otherwise return only those with permission to view (select)
        else: 
            instruments = db.get_instruments(id=permissions["instruments"]["select"], type=type)

        cryodb_logger.debug(f"Retrieved {len(instruments)} {type} instruments")

        return CryodbResponse(json.dumps([i.to_dict() for i in instruments]), status=200)

    ###########################################################################
    @cryodb_app.route("/receiver/list", methods=["GET",])
    def list_receivers():

        # Validate API
        try:
            api_type, permissions = validate_api_key()
        except cryodb.InvalidAPIKeyError as e:
            return CryodbErrorResponse(e, 401, "Invalid API key")
        
        # Get DB object
        db = get_cryodb()
        
        receivers = []
        if api_type == cryodb.APIKeyType.ADMIN:
            receivers = db.get_receivers()
        else:
            receivers = db.get_receivers(id=permissions["receivers"]["select"])

        cryodb_logger.debug(f"Retrieved {len(receivers)} receivers")

        return CryodbResponse(json.dumps([r.to_dict() for r in receivers]), status=200)
    
    ###########################################################################
    @cryodb_app.route("/ingest/lingomo", methods=["POST",])
    def ingest_lingomo():

        # Validate API
        try:
            api_type, permissions = validate_api_key()
        except cryodb.InvalidAPIKeyError as e:
            return CryodbErrorResponse(e, 401, message="Invalid API key.")
        
        event_id = cryodb_app.config["LINGOMO_EVENT_ID"]
        if event_id < 0: # default value is -1
            return CryodbErrorResponse(ValueError(), 500, message="config['LINGOMO_EVENT_ID'] not set.")

        # Try inserting LingoMO into database
        db = get_cryodb()
        try: 
            ingest_id = db.ingest_lingomo(request.data.decode("utf-8"), event_id)
            
        except json.decoder.JSONDecodeError as e:
            return CryodbErrorResponse(e, 400, message="Invalid JSON data.") # Bad request
        except cryodb.InvalidLingoMOPacketError as e:
            return CryodbErrorResponse(e, 400, message="Invalid LingoMO packet.") # Bad request
        except cryodb.NoRecordInsertedError as e:
            return CryodbErrorResponse(e, 501, "Failed to insert record.") # Internal server error
        except ValueError as e:
            return CryodbErrorResponse(e, 500)
        except Exception as e:
            return CryodbErrorResponse(e, 500, message="Could not ingest message.")
        
        return CryodbResponse({"ingest_id" : ingest_id}, 200)

        
    ###########################################################################
    return cryodb_app


def run_cli_server():

    parser = argparse.ArgumentParser(
        prog = "cryodb-server"
    )

    cryodb_app = create_app() 
    cryodb_app.run("localhost", 3291)


if __name__ == "__main__":
    create_app()