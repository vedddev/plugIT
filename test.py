import sqlite3

c = sqlite3.connect("smartllm.db")

tables = c.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("TABLES:")
for table in tables:
    print(table[0])

c.close()