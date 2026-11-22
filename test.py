
import os
import getpass
import mysql.connector
from dotenv import load_dotenv

load_dotenv(".env", override=True)

print("Checking .env password...")
entered_password = getpass.getpass("Enter your MySQL Workbench password: ")

if entered_password != os.getenv("DB_PASSWORD"):
    print("Password in .env does not match!")
else:
    print("Password matches .env!")

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=entered_password,
            database=os.getenv("DB_NAME")
        )
        print("Database connected successfully!")
        conn.close()

    except mysql.connector.Error as e:
        print("Connection failed:", e)
