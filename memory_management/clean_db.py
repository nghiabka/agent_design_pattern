import sqlite3
import os

DB_PATH = "/data/db/long_term_memory.db"

# Các từ khóa "rác" cần xóa bỏ
JUNK_PATTERNS = [
    "%key: value%", 
    "%key=value%", 
    "%hoặc none%", 
    "%(info)%", 
    "%...%", 
    "%tên=%", 
    "%sở thích=%", 
    "%ví dụ%", 
    "%nếu không có%",
    "%one short sentence%",
    "%mô tả ngắn gọn%",
    "%short problem%",
    "%short issue%"
]

def clean_database():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    deleted_total = 0

    tables = ["profile", "preferences", "key_facts", "past_issues"]
    columns = {
        "profile": "value",
        "preferences": "value",
        "key_facts": "fact",
        "past_issues": "issue"
    }

    print("--- STARTING DATABASE CLEANUP ---")

    for table in tables:
        col = columns[table]
        for pattern in JUNK_PATTERNS:
            cursor.execute(f"DELETE FROM {table} WHERE {col} LIKE ?", (pattern,))
            deleted_total += cursor.rowcount

    # Xóa các dòng chỉ có chữ "none" (không phân biệt hoa thường)
    for table in tables:
        col = columns[table]
        cursor.execute(f"DELETE FROM {table} WHERE LOWER({col}) = 'none'")
        deleted_total += cursor.rowcount

    conn.commit()
    conn.close()

    print(f"--- CLEANUP COMPLETE ---")
    print(f"Total junk rows removed: {deleted_total}")

if __name__ == "__main__":
    clean_database()
