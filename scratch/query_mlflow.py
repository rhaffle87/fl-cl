import sqlite3
conn = sqlite3.connect('/root/mlflow.db')
cur = conn.cursor()
cur.execute("SELECT key, COUNT(*), MIN(value), MAX(value) FROM metrics WHERE run_uuid = 'd024628e3e6e46d0881aef78265f2c7e' GROUP BY key")
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
