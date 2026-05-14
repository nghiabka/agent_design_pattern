import sqlite3
import os

DB_PATH = "/data/db/long_term_memory.db"
USER_ID = "demo_user"

def query_memory():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"--- LONG TERM MEMORY FOR USER: {USER_ID} ---\n")

    # 1. Profile
    print("👤 PROFILE:")
    try:
        cursor.execute("SELECT key, value FROM profile WHERE user_id = ?", (USER_ID,))
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                print(f"  - {r['key']}: {r['value']}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"  Error: {e}")

    # 2. Preferences
    print("\n⭐ PREFERENCES:")
    try:
        cursor.execute("SELECT key, value FROM preferences WHERE user_id = ?", (USER_ID,))
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                print(f"  - {r['key']}: {r['value']}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"  Error: {e}")

    # 3. Facts
    print("\n📌 KEY FACTS:")
    try:
        cursor.execute("SELECT fact FROM key_facts WHERE user_id = ?", (USER_ID,))
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                print(f"  - {r['fact']}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"  Error: {e}")

    # 4. Issues
    print("\n⚠️ PAST ISSUES:")
    try:
        cursor.execute("SELECT issue FROM past_issues WHERE user_id = ?", (USER_ID,))
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                print(f"  - {r['issue']}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"  Error: {e}")

    # 5. Stats
    print("\n📊 USER STATS:")
    try:
        cursor.execute("SELECT interaction_count, first_seen, last_seen FROM users WHERE user_id = ?", (USER_ID,))
        r = cursor.fetchone()
        if r:
            print(f"  - Interactions: {r['interaction_count']}")
            print(f"  - First seen: {r['first_seen']}")
            print(f"  - Last seen: {r['last_seen']}")
    except Exception as e:
        print(f"  Error: {e}")

    conn.close()

if __name__ == "__main__":
    query_memory()
