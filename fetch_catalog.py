import json
import os
from pathlib import Path

import psycopg2
import rich

import globals as G
from server import db_config as SG
from server.req_sql import sample_catalog

# Add any transport_ids you want included in the catalog.
TRANSPORT_IDS = [G.TRANSPORT_ID]

# SSL cert is relative to sql/ dir
os.chdir(Path(__file__).parent / "sql")

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
