import sqlite3

conn = sqlite3.connect('dev.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for table_name in tables:
    if table_name[0] != 'sqlite_sequence':
        cursor.execute(f"DELETE FROM {table_name[0]};")
        
conn.commit()
conn.close()
print("Database cleared successfully.")
