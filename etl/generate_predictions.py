import os
import random
from datetime import datetime, timedelta

import psycopg
import numpy as np
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

TOTAL_RECORDS = 100_000
BATCH_SIZE = 5_000

MODEL_VERSIONS = [3, 5, 7, 8]

START_DATE = datetime(2026, 7, 1)
DAYS = 30


def generate_prediction(version_id, timestamp):
    degradation = (
        version_id == 3
        and timestamp.date() >= datetime(2026, 7, 21).date()
    )

    if degradation:
        accuracy = 0.86
        latency_mean = 280
    else:
        accuracy = {
            3: 0.94,
            5: 0.92,
            7: 0.90,
            8: 0.93,
        }[version_id]

        latency_mean = {
            3: 130,
            5: 145,
            7: 160,
            8: 150,
        }[version_id]

    actual = random.randint(0, 1)

    if random.random() < accuracy:
        predicted = actual
    else:
        predicted = 1 - actual

    confidence = np.clip(
        np.random.normal(0.90 if predicted == actual else 0.55, 0.08),
        0.50,
        0.99
    )

    latency = max(
        20,
        int(np.random.normal(latency_mean, 30))
    )

    return (
        version_id,
        timestamp,
        actual,
        predicted,
        round(float(confidence), 4),
        latency
    )


def generate_data():
    records = []

    for _ in range(TOTAL_RECORDS):
        version_id = random.choice(MODEL_VERSIONS)

        day_offset = random.randint(0, DAYS - 1)
        seconds_offset = random.randint(0, 86399)

        timestamp = (
            START_DATE
            + timedelta(days=day_offset, seconds=seconds_offset)
        )

        records.append(
            generate_prediction(version_id, timestamp)
        )

    return records


def insert_data(records):
    query = """
        INSERT INTO predictions
        (
            version_id,
            prediction_timestamp,
            actual_value,
            predicted_value,
            confidence,
            latency_ms
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    with psycopg.connect(**DB_CONFIG) as connection:
        with connection.cursor() as cursor:
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i:i + BATCH_SIZE]

                cursor.executemany(query, batch)

                print(
                    f"Inserted {min(i + BATCH_SIZE, len(records)):,}"
                    f"/{len(records):,} records"
                )

        connection.commit()


def main():
    print("Generating prediction data...")

    records = generate_data()

    print(f"Generated {len(records):,} records")

    print("Loading data into PostgreSQL...")

    insert_data(records)

    print("Data generation complete.")


if __name__ == "__main__":
    main()