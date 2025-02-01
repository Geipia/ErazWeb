from backend.data_structures import *
import os
import csv
import datetime
from app_web import app, set_error
from backend.client import client
from internal.log import log_error, log_warning

REMOTE_VALUE_FILE = "/eraz/eraz_values.csv"
LOCAL_TEMP_FILE = "temp_eraz_values.csv"

def ensure_eraz_directory():
    if not client.check("/eraz"):
        client.mkdir("/eraz")

def ensure_value_file():
    if not client.check(REMOTE_VALUE_FILE):
        with open(LOCAL_TEMP_FILE, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'value'])
            writer.writerow([datetime.datetime.now().isoformat(), initial_eraz_value])
        client.upload_sync(remote_path=REMOTE_VALUE_FILE, local_path=LOCAL_TEMP_FILE)
        os.remove(LOCAL_TEMP_FILE)

if not os.path.exists(VALUE_FILE):
    with open(VALUE_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['timestamp', 'value'])
        writer.writerow([datetime.datetime.now().isoformat(), initial_eraz_value])


def update_eraz_value(minedamount: float = 0):
    """Updates the Eraz value."""
    try:
        client.download_sync(remote_path=REMOTE_VALUE_FILE, local_path=LOCAL_TEMP_FILE)

        with open(LOCAL_TEMP_FILE, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            last_row = list(reader)[-1]  # Get last row
            last_value = float(last_row[1])

        new_value = last_value - minedamount / 10000 if minedamount / 10000 < last_value else 0

        if new_value <= 0:
            app.redirect('/error')
            set_error(True)
            log_error('FATAL ERROR: Eraz value can never be negative.')
            return

        with open(LOCAL_TEMP_FILE, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([datetime.datetime.now().isoformat(), new_value])

        client.upload_sync(remote_path=REMOTE_VALUE_FILE, local_path=LOCAL_TEMP_FILE)
        os.remove(LOCAL_TEMP_FILE)
    except Exception as e:
        log_error(f"Error updating Eraz value: {str(e)}")

def get_eraz_values():
    """Reads eraz_values from WebDAV."""
    eraz_values = []
    try:
        if client.check(REMOTE_VALUE_FILE):
            client.download_sync(remote_path=REMOTE_VALUE_FILE, local_path=LOCAL_TEMP_FILE)
            with open(LOCAL_TEMP_FILE, "r") as csv_file:
                reader = csv.reader(csv_file)
                next(reader)
                eraz_values = [(row[0], float(row[1])) for row in reader if len(row) == 2]
            os.remove(LOCAL_TEMP_FILE)
        else:
            log_warning(f"No eraz_values.csv found at {REMOTE_VALUE_FILE}. Creating a new one.")
            ensure_value_file()
    except Exception as e:
        log_error(f"Error reading eraz_values from WebDAV: {str(e)}")

    return eraz_values

# Initialize WebDAV storage
ensure_eraz_directory()
ensure_value_file()
