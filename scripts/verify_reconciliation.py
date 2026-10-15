
import json
import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "dev.duckdb"
AUDIT_PATH = PROJECT_ROOT / "metadata" / "approval_audit.jsonl"

con = duckdb.connect(str(DB_PATH), read_only=True)

try:
    print("=== INCIDENT COUNTS BY TYPE AND SEVERITY ===")
    print(con.execute("""
        SELECT incident_type, incident_severity, incident_status,
               COUNT(*) AS total
        FROM fct_reconciliation_incidents
        GROUP BY incident_type, incident_severity, incident_status
        ORDER BY incident_type, incident_severity, incident_status
    """).fetchdf().to_string(index=False))

    print("\n=== TWO PREVIOUSLY APPROVED INCIDENTS ===")
    print(con.execute("""
        SELECT payment_id, order_id, incident_type, incident_status,
               incident_severity, order_amount, payment_amount,
               refund_amount, settlement_amount
        FROM fct_reconciliation_incidents
        WHERE order_id IN ('ORD000824', 'ORD000907')
        ORDER BY order_id
    """).fetchdf().to_string(index=False))

finally:
    con.close()

print("\n=== APPROVAL AUDIT RECORDS ===")

if not AUDIT_PATH.exists():
    print("Approval audit file not found:", AUDIT_PATH)
else:
    with AUDIT_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)
            incident_id = record.get("incident_id", "")
            if "ORD000824" in incident_id or "ORD000907" in incident_id:
                print(json.dumps(record, indent=2))
