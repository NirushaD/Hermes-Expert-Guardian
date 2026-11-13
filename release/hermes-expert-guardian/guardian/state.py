"""SQLite transactions serialize Desktop and hook workers, including across processes."""
from contextlib import contextmanager, closing
import json
import sqlite3
import time


class Store:
    def __init__(self, path):
        self.path = str(path)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, touched REAL, data TEXT)")

    @contextmanager
    def session(self, identity):
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM sessions WHERE id=?", (identity,)).fetchone()
            if row is None and db.execute("SELECT count(*) FROM sessions").fetchone()[0] >= 512:
                raise RuntimeError("Guardian capacity reached; delete inactive history explicitly")
            data = json.loads(row[0]) if row else {"events": [], "incidents": [], "pending": {}, "objective": ""}
            yield data
            db.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (identity, time.time(), json.dumps(data)))
            for old_id, encoded in db.execute("SELECT id,data FROM sessions WHERE touched < ?", (time.time()-30*86400,)).fetchall():
                old = json.loads(encoded)
                if (not old["pending"] and all(i["state"] in {"RESOLVED", "REVIEWED"} for i in old["incidents"])
                        and all(r["state"] in {"FAILED", "ADVICE_READY", "CANCELLED"} for r in old.get("reviews", []))):
                    db.execute("DELETE FROM sessions WHERE id=?", (old_id,))

    def delete(self, identity):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM sessions WHERE id=?", (identity,))

    def incident_index(self):
        """Read existing incident summaries without creating chat history."""
        with closing(sqlite3.connect(self.path)) as db:
            result = []
            for identity, encoded in db.execute("SELECT id,data FROM sessions"):
                data = json.loads(encoded)
                result.append({"session": identity, "incidents": [
                    {key: item[key] for key in ("id", "reason", "state", "time", "attempts", "retry_ok", "outcome_unresolved") if key in item}
                    for item in data.get("incidents", [])]})
            return result
