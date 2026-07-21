import sqlite3
import os

os.makedirs('storage/file1', exist_ok=True)
with open('storage/file1/test.csv', 'w') as f:
    f.write('dummy')

con = sqlite3.connect('dev.db')
cur = con.cursor()
cur.execute("INSERT INTO sessions (id) VALUES ('sess1')")
cur.execute("INSERT INTO files (id, session_id, original_filename, file_type, size_bytes, storage_path) VALUES ('file1', 'sess1', 'test.csv', 'csv', 100, 'storage/file1')")
cur.execute("INSERT INTO prompts (id, file_id, raw_text) VALUES ('prompt1', 'file1', 'make a chart')")
cur.execute("INSERT INTO charts (id, prompt_id, chart_type, chart_spec) VALUES ('chart1', 'prompt1', 'bar', '{}')")
con.commit()
con.close()
print('Inserted dummy rows!')
