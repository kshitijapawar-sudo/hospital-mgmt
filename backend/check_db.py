import sqlite3
import traceback

try:
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()
    # Check if column exists
    cols = [col[1] for col in c.execute('PRAGMA table_info(inpatients)').fetchall()]
    print("Columns:", cols)
    if 'photo_description' not in cols:
        print("Adding column photo_description...")
        c.execute("ALTER TABLE inpatients ADD COLUMN photo_description TEXT DEFAULT ''")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column already exists.")
except Exception as e:
    print("Error:", e)
    traceback.print_exc()
