# Philip Thompson 22024226

import os
import csv
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "predictions.csv")


def ensure_log_file():
    # Create logs directory and CSV file if they don't exist.

    os.makedirs(LOG_DIR, exist_ok=True)

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "image_path",
                "predicted_label",
                "fresh_probability",
                "rotten_probability",
                "grade",
                "action"
            ])


def log_prediction(result: dict):
    # Append a prediction result to the CSV log file.
    
    ensure_log_file()

    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            result.get("image_path"),
            result.get("predicted_label"),
            result.get("fresh_probability"),
            result.get("rotten_probability"),
            result.get("grade"),
            result.get("action"),
        ])