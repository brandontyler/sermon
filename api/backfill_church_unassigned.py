"""One-time backfill: set churchId='church-unassigned' on sermons missing it,
and ensure the 'Church Unassigned' record exists in the churches container.

Usage: python backfill_church_unassigned.py
Requires COSMOS_CONNECTION_STRING env var.
"""
import os
from azure.cosmos import CosmosClient

UNASSIGNED = "church-unassigned"

conn = os.environ["COSMOS_CONNECTION_STRING"]
cosmos = CosmosClient.from_connection_string(conn)
db = cosmos.get_database_client("psr")

# Ensure churches container + unassigned record
try:
    cc = db.create_container_if_not_exists(id="churches", partition_key={"paths": ["/id"], "kind": "Hash"})
except Exception:
    cc = db.get_container_client("churches")

try:
    cc.read_item(UNASSIGNED, partition_key=UNASSIGNED)
    print("Church Unassigned record already exists")
except Exception:
    cc.create_item({"id": UNASSIGNED, "name": "Church Unassigned", "city": "", "state": "", "url": "", "pastors": [], "autoCreated": True})
    print("Created Church Unassigned record")

# Backfill sermons
sc = db.get_container_client("sermons")
sermons = list(sc.query_items(
    "SELECT c.id, c.churchId, c.pastor FROM c WHERE NOT IS_DEFINED(c.churchId) OR c.churchId = null",
    enable_cross_partition_query=True,
))
print(f"Found {len(sermons)} sermons without churchId")

# Build pastor→churchId lookup from existing churches
churches = list(cc.query_items("SELECT c.id, c.pastors FROM c", enable_cross_partition_query=True))
pastor_church = {}
for ch in churches:
    for p in ch.get("pastors", []):
        pastor_church[p["name"]] = ch["id"]

updated = 0
for s in sermons:
    church_id = pastor_church.get(s.get("pastor"), UNASSIGNED)
    doc = sc.read_item(s["id"], partition_key=s["id"])
    doc["churchId"] = church_id
    sc.upsert_item(doc)
    updated += 1
    tag = church_id if church_id != UNASSIGNED else "unassigned"
    print(f"  {s['id']} → {tag}")

print(f"Done. Updated {updated} sermons.")
