import mysql.connector

# Connect to database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="cryoparty"
)

# Run scripts
cursor = db.cursor()

for script in ["init_user.sql", "init_database.sql", "init_metadata.sql"]:

    with open(f"src/init/{script}", "r") as fh:

        cursor.executemany(fh.read())