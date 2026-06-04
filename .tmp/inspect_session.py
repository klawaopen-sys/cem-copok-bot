import sqlite3

def main():
    db_path = "f:/Antigravity/Cem_copok/klava.session"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables:", tables)
    for table_tuple in tables:
        table_name = table_tuple[0]
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"Table {table_name} columns:", [c[1] for c in columns])
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"Table {table_name} row count:", count)
        except Exception as e:
            print(f"Error reading {table_name}: {e}")
    conn.close()

if __name__ == "__main__":
    main()
