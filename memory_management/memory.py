"""
═══════════════════════════════════════════════════════════════════════
MEMORY — Short-term & Long-term Memory System
═══════════════════════════════════════════════════════════════════════

Hai loại bộ nhớ:

SHORT-TERM MEMORY (Bộ nhớ ngắn hạn):
  • Lưu trong RAM — lịch sử hội thoại phiên hiện tại
  • Mất khi kết thúc session
  • Sliding window: giữ N lượt gần nhất (tránh token overflow)

LONG-TERM MEMORY (Bộ nhớ dài hạn):
  • Lưu trên SQLite database — persistent qua nhiều session
  • Database path configurable qua SQLITE_DB_PATH env var
  • Gồm: user profile, preferences, past issues, key facts
  • LLM trích xuất thông tin quan trọng → lưu vào long-term memory
  • 5 tables: users, profile, preferences, key_facts,
    past_issues, conversation_summaries
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from rich.console import Console
from rich.table import Table

from config import SQLITE_DB_PATH

console = Console()


# ═══════════════════════════════════════════════════════════════
# SHORT-TERM MEMORY — Conversation buffer (không đổi, vẫn RAM)
# ═══════════════════════════════════════════════════════════════

class ShortTermMemory:
    """Bộ nhớ ngắn hạn — lịch sử hội thoại trong phiên.

    Sử dụng sliding window để giữ N lượt gần nhất,
    tránh context quá dài gây token overflow.
    """

    def __init__(self, max_turns: int = 10):
        self.messages: list[BaseMessage] = []
        self.max_turns = max_turns
        self.total_turns = 0

    def add_user_message(self, content: str):
        self.messages.append(HumanMessage(content=content))
        self._trim()

    def add_ai_message(self, content: str):
        self.messages.append(AIMessage(content=content))
        self.total_turns += 1
        self._trim()

    def _trim(self):
        max_messages = self.max_turns * 2
        if len(self.messages) > max_messages:
            removed = len(self.messages) - max_messages
            self.messages = self.messages[removed:]
            console.print(
                f"  [dim]📎 Short-term: trimmed {removed} messages"
                f" (giữ {self.max_turns} turns)[/dim]"
            )

    def get_messages(self) -> list[BaseMessage]:
        return list(self.messages)

    def get_summary(self) -> str:
        return (
            f"{len(self.messages)} messages"
            f" ({self.total_turns} turns, max {self.max_turns})"
        )

    def clear(self):
        self.messages.clear()
        self.total_turns = 0


# ═══════════════════════════════════════════════════════════════
# LONG-TERM MEMORY — SQLite Database
# ═══════════════════════════════════════════════════════════════

class LongTermMemory:
    """Bộ nhớ dài hạn — persistent qua nhiều session bằng SQLite.

    Database path lấy từ SQLITE_DB_PATH env var:
      • Docker: /data/db/long_term_memory.db (mounted volume)
      • Local:  ./memory_store/long_term_memory.db

    Database schema:
      • users           — user_id, interaction_count, first_seen, last_seen
      • profile         — user_id, key, value  (tên, tuổi, nghề...)
      • preferences     — user_id, key, value  (sở thích)
      • key_facts       — user_id, fact, created_at
      • past_issues     — user_id, issue, created_at
      • conversation_summaries — user_id, summary, created_at
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db_path = SQLITE_DB_PATH
        self._init_db()
        self._ensure_user()

    def _get_conn(self) -> sqlite3.Connection:
        """Tạo connection mới (thread-safe)."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Tạo tables nếu chưa tồn tại."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                interaction_count INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT
            );
            CREATE TABLE IF NOT EXISTS profile (
                user_id TEXT, key TEXT, value TEXT, updated_at TEXT,
                PRIMARY KEY (user_id, key),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS preferences (
                user_id TEXT, key TEXT, value TEXT, updated_at TEXT,
                PRIMARY KEY (user_id, key),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS key_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, fact TEXT, created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS past_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, issue TEXT, created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, summary TEXT, created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)
        conn.commit()
        conn.close()

    def _ensure_user(self):
        """Tạo user record nếu chưa tồn tại."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (self.user_id,)
        ).fetchone()
        if row:
            console.print(f"  [green]🗄️  Long-term memory loaded: {self.user_id}[/green]")
        else:
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO users (user_id, interaction_count, first_seen) VALUES (?, 0, ?)",
                (self.user_id, now),
            )
            conn.commit()
            console.print(f"  [yellow]🗄️  New user — tạo long-term memory mới[/yellow]")
        conn.close()

    # ── CRUD operations ──────────────────────────────────────

    def update_profile(self, key: str, value: str):
        """Cập nhật / thêm thông tin profile (UPSERT)."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO profile (user_id, key, value, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, key) DO UPDATE SET value=?, updated_at=?""",
            (self.user_id, key, value, now, value, now),
        )
        conn.commit()
        conn.close()

    def add_preference(self, key: str, value: str):
        """Thêm / cập nhật sở thích (UPSERT)."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO preferences (user_id, key, value, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, key) DO UPDATE SET value=?, updated_at=?""",
            (self.user_id, key, value, now, value, now),
        )
        conn.commit()
        conn.close()

    def add_key_fact(self, fact: str):
        """Thêm thông tin quan trọng (tránh duplicate, giữ max 30)."""
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM key_facts WHERE user_id = ? AND fact = ?",
            (self.user_id, fact),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO key_facts (user_id, fact, created_at) VALUES (?, ?, ?)",
                (self.user_id, fact, datetime.now().isoformat()),
            )
            conn.execute("""
                DELETE FROM key_facts WHERE id IN (
                    SELECT id FROM key_facts WHERE user_id = ?
                    ORDER BY created_at ASC
                    LIMIT MAX(0, (SELECT COUNT(*) FROM key_facts WHERE user_id = ?) - 30)
                )
            """, (self.user_id, self.user_id))
            conn.commit()
        conn.close()

    def add_past_issue(self, issue: str):
        """Ghi nhận vấn đề đã gặp (giữ max 20)."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO past_issues (user_id, issue, created_at) VALUES (?, ?, ?)",
            (self.user_id, issue, datetime.now().isoformat()),
        )
        conn.execute("""
            DELETE FROM past_issues WHERE id IN (
                SELECT id FROM past_issues WHERE user_id = ?
                ORDER BY created_at ASC
                LIMIT MAX(0, (SELECT COUNT(*) FROM past_issues WHERE user_id = ?) - 20)
            )
        """, (self.user_id, self.user_id))
        conn.commit()
        conn.close()

    def add_conversation_summary(self, summary: str):
        """Lưu tóm tắt cuộc hội thoại (giữ max 10)."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO conversation_summaries (user_id, summary, created_at) VALUES (?, ?, ?)",
            (self.user_id, summary, datetime.now().isoformat()),
        )
        conn.execute("""
            DELETE FROM conversation_summaries WHERE id IN (
                SELECT id FROM conversation_summaries WHERE user_id = ?
                ORDER BY created_at ASC
                LIMIT MAX(0, (SELECT COUNT(*) FROM conversation_summaries WHERE user_id = ?) - 10)
            )
        """, (self.user_id, self.user_id))
        conn.commit()
        conn.close()

    def increment_interaction(self):
        """Tăng số lần tương tác."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE users SET interaction_count = interaction_count + 1, last_seen = ? WHERE user_id = ?",
            (datetime.now().isoformat(), self.user_id),
        )
        conn.commit()
        conn.close()

    # ── Query helpers ────────────────────────────────────────

    def _get_kv_dict(self, table: str) -> dict:
        conn = self._get_conn()
        rows = conn.execute(
            f"SELECT key, value FROM {table} WHERE user_id = ?", (self.user_id,)
        ).fetchall()
        conn.close()
        return {r["key"]: r["value"] for r in rows}

    def _get_list(self, table: str, column: str, limit: int) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            f"SELECT {column}, created_at FROM {table} WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (self.user_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    def _get_user_stats(self) -> dict:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (self.user_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else {}

    # ── Context generation ───────────────────────────────────

    def get_context(self) -> str:
        """Tạo context string từ long-term memory để inject vào prompt."""
        parts = []
        profile = self._get_kv_dict("profile")
        if profile:
            parts.append(f"👤 Profile: {', '.join(f'{k}: {v}' for k, v in profile.items())}")
        prefs = self._get_kv_dict("preferences")
        if prefs:
            parts.append(f"⭐ Preferences: {', '.join(f'{k}: {v}' for k, v in prefs.items())}")
        facts = self._get_list("key_facts", "fact", 5)
        if facts:
            parts.append(f"📌 Key facts: {'; '.join(f['fact'] for f in facts)}")
        issues = self._get_list("past_issues", "issue", 3)
        if issues:
            parts.append(f"⚠️ Past issues: {'; '.join(i['issue'] for i in issues)}")
        summaries = self._get_list("conversation_summaries", "summary", 2)
        if summaries:
            parts.append(f"📜 Previous conversations: {'; '.join(s['summary'] for s in summaries)}")
        stats = self._get_user_stats()
        parts.append(f"📊 Interactions: {stats.get('interaction_count', 0)}")
        return "\n".join(parts) if parts else "(Chưa có thông tin)"

    # ── Display ──────────────────────────────────────────────

    def print_status(self):
        """In trạng thái long-term memory."""
        stats = self._get_user_stats()
        profile = self._get_kv_dict("profile")
        prefs = self._get_kv_dict("preferences")
        conn = self._get_conn()
        fact_count = conn.execute(
            "SELECT COUNT(*) as c FROM key_facts WHERE user_id = ?", (self.user_id,)
        ).fetchone()["c"]
        issue_count = conn.execute(
            "SELECT COUNT(*) as c FROM past_issues WHERE user_id = ?", (self.user_id,)
        ).fetchone()["c"]
        summary_count = conn.execute(
            "SELECT COUNT(*) as c FROM conversation_summaries WHERE user_id = ?", (self.user_id,)
        ).fetchone()["c"]
        conn.close()

        tbl = Table(
            title=f"🧠 Long-term Memory (SQLite) — {self.user_id}",
            border_style="magenta", show_lines=True,
        )
        tbl.add_column("Key", style="bold", width=20)
        tbl.add_column("Value", width=50)
        tbl.add_row("User ID", self.user_id)
        tbl.add_row("Storage", f"🗄️  SQLite: {self.db_path}")
        tbl.add_row("Profile", json.dumps(profile, ensure_ascii=False) or "{}")
        tbl.add_row("Preferences", json.dumps(prefs, ensure_ascii=False) or "{}")
        tbl.add_row("Key Facts", f"{fact_count} items")
        tbl.add_row("Past Issues", f"{issue_count} items")
        tbl.add_row("Summaries", f"{summary_count} items")
        tbl.add_row("Interactions", str(stats.get("interaction_count", 0)))
        tbl.add_row("First Seen", stats.get("first_seen", "—"))
        tbl.add_row("Last Seen", stats.get("last_seen", "—"))
        console.print(tbl)

    def get_raw_data(self):
        """Trả về dữ liệu gốc để hiển thị trên web UI."""
        stats = self._get_user_stats()
        profile = self._get_kv_dict("profile")
        prefs = self._get_kv_dict("preferences")
        conn = self._get_conn()
        fact_count = conn.execute(
            "SELECT COUNT(*) as c FROM key_facts WHERE user_id = ?", (self.user_id,)
        ).fetchone()["c"]
        issue_count = conn.execute(
            "SELECT COUNT(*) as c FROM past_issues WHERE user_id = ?", (self.user_id,)
        ).fetchone()["c"]
        summary_count = conn.execute(
            "SELECT COUNT(*) as c FROM conversation_summaries WHERE user_id = ?", (self.user_id,)
        ).fetchone()["c"]
        conn.close()
        
        return profile, prefs, fact_count, issue_count, summary_count, stats
