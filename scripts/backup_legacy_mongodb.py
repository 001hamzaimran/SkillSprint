"""Create a checksummed, restorable Extended JSON backup of legacy MongoDB data."""
import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from bson import json_util
from pymongo import MongoClient


ROOT = Path(__file__).resolve().parents[1]


def main():
    uri = os.getenv("MONGO_SOURCE_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGO_SOURCE_DATABASE", "skillsprint")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "archive" / f"mongodb-backup-{stamp}"
    output.mkdir(parents=True, exist_ok=False)
    client = MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True)
    client.admin.command("ping")
    database = client[database_name]
    manifest = {"database": database_name, "created_at": stamp, "collections": {}}
    try:
        for name in sorted(database.list_collection_names()):
            rows = list(database[name].find({}))
            path = output / f"{name}.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                json.dump(rows, stream, default=json_util.default, ensure_ascii=False)
            manifest["collections"][name] = {
                "records": len(rows),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "file": path.name,
            }
        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(output)
        print(f"Backed up {sum(item['records'] for item in manifest['collections'].values())} records.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
