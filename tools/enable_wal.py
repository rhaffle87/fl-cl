import sqlite3
import sys

def main():
    try:
        conn = sqlite3.connect("mlflow.db")
        # Enable WAL mode
        res = conn.execute("PRAGMA journal_mode=WAL;").fetchone()
        conn.close()
        print(f"WAL Mode Status: {res}")
    except Exception as e:
        print(f"Error enabling WAL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
