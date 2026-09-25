"""One-time migration from the former MongoDB workspace to PostgreSQL.

Requires the optional legacy driver: pip install "pymongo>=4.11,<5".
The destination PostgreSQL schema must be empty.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.db import COLLECTIONS, connect, initialize


def main():
    parser = argparse.ArgumentParser(description="Copy SkillSprint MongoDB data into PostgreSQL")
    parser.add_argument(
        "--mongo-uri", default=os.getenv("MONGO_SOURCE_URI", "mongodb://localhost:27017")
    )
    parser.add_argument(
        "--mongo-database", default=os.getenv("MONGO_SOURCE_DATABASE", "skillsprint")
    )
    args = parser.parse_args()
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise SystemExit(
            'Install the legacy source driver first: pip install "pymongo>=4.11,<5"'
        ) from exc

    settings = Settings()
    source_client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=5000, tz_aware=True)
    source_client.admin.command("ping")
    source = source_client[args.mongo_database]
    target_client, target = connect(settings)
    initialize(target)
    try:
        nonempty = [name for name in COLLECTIONS if target[name].count_documents({})]
        if nonempty:
            raise SystemExit(
                "Destination schema is not empty (" + ", ".join(nonempty) + "). "
                "Choose a new POSTGRES_SCHEMA to avoid overwriting data."
            )
        totals = {}
        for name in COLLECTIONS:
            rows = list(source[name].find({}))
            for row in rows:
                row["_id"] = str(row["_id"])
                target[name].insert_one(row)
            totals[name] = len(rows)
            print(f"{name}: {len(rows)}")
        print(f"Migration complete: {sum(totals.values())} records copied to schema {target.name}.")
    finally:
        source_client.close()
        target_client.close()


if __name__ == "__main__":
    main()
