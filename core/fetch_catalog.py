import json
import os
from pathlib import Path

import psycopg2
import rich

from core import globals as G
from database_clients import db_config as SG
from database_clients.req_sql import sample_catalog

# Add any transport_ids you want included in the catalog.
TRANSPORT_IDS = [G.TRANSPORT_ID]

# SSL cert is relative to adapters/sql/ dir
os.chdir(Path(__file__).parent.parent / "adapters" / "sql")

conn = psycopg2.connect(**SG.POSTGRES)
cur = conn.cursor()

catalog = []
for tid in TRANSPORT_IDS:
    catalog.extend(sample_catalog(cur, tid, n=200))

cur.close()
conn.close()

with open(Path(__file__).parent / "catalog_cache.json", "w") as f:
    json.dump(catalog, f)

rich.print(f"Saved {len(catalog)} entries across {len(TRANSPORT_IDS)} city/cities to catalog_cache.json")
