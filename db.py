import os
import mysql.connector
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

CA_PATH = os.path.join(BASE_DIR, "certs", "tidb-ca.pem")


def get_db_connection():

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "4000")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),

        ssl_ca=CA_PATH,
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )

    return connection