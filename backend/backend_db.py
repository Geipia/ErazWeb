from backend.data_structures import *
import os
import csv
import datetime
from app_web import app, set_error

if not os.path.exists(VALUE_FILE):
    with open(VALUE_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['timestamp', 'value'])
        writer.writerow([datetime.datetime.now().isoformat(), initial_eraz_value])


def update_eraz_value(minedamount: float = 0):
    """Met à jour la valeur de l'Eraz pour tout le monde."""
    with open(VALUE_FILE, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        last_row = list(reader)[-1]  # Get last row
        last_value = float(last_row[1])

    # Simule une légère augmentation ou diminution de la valeur
    new_value = last_value - minedamount / 10000 if minedamount / 10000 < last_value else 0
    if new_value <= 0:
        app.redirect('/error')
        set_error(True)
        print('FATAL ERROR: Eraz value can never be negative.')
        #RuntimeError("Eraz value can never be negative")

    with open(VALUE_FILE, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([datetime.datetime.now().isoformat(), new_value])


def get_eraz_values():
    """Récupère les valeurs de l'Eraz depuis le fichier CSV."""
    with open(VALUE_FILE, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        return [(datetime.datetime.fromisoformat(row[0]), float(row[1])) for row in reader]
