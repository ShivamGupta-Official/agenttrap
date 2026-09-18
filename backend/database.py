import aiosqlite
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "honeypot.db"

async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                source_ip TEXT DEFAULT 'unknown',
                first_seen REAL,
                last_seen REAL,
                request_count INTEGER DEFAULT 0,
                agenticity_score INTEGER DEFAULT 0,
                agenticity_data TEXT DEFAULT '{}'
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp REAL,
                method TEXT,
                path TEXT,
                headers TEXT DEFAULT '{}',
                body TEXT DEFAULT '',
                source_ip TEXT DEFAULT 'unknown',
                user_agent TEXT DEFAULT 'unknown',
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                status_code INTEGER,
                content_type TEXT DEFAULT '',
                content_id TEXT DEFAULT '',
                probe_triggered TEXT,
                FOREIGN KEY (request_id) REFERENCES requests(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS behaviour_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp REAL,
                event_type TEXT,
                previous_action TEXT DEFAULT '',
                current_action TEXT DEFAULT '',
                delta_time REAL DEFAULT 0.0,
                strategy_changed INTEGER DEFAULT 0,
                detail TEXT DEFAULT '',
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        # Performance & security hardening indexes
        await db.execute('CREATE INDEX IF NOT EXISTS idx_requests_session ON requests(session_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_requests_ts ON requests(timestamp)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_responses_req ON responses(request_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_behaviour_session ON behaviour_events(session_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_sessions_last_seen ON sessions(last_seen)')
        await db.commit()

async def log_request(session_id: str, method: str, path: str, headers: dict, body: str, source_ip: str, user_agent: str) -> dict:
    """Log a request and return it as a dict with id."""
    ts = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'INSERT INTO requests (session_id, timestamp, method, path, headers, body, source_ip, user_agent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (session_id, ts, method, path, json.dumps(headers), body, source_ip, user_agent)
        )
        request_id = cursor.lastrowid
        await db.commit()
    return {
        'id': request_id, 'session_id': session_id, 'timestamp': ts,
        'method': method, 'path': path, 'headers': headers,
        'body': body, 'source_ip': source_ip, 'user_agent': user_agent
    }

async def log_response(request_id: int, status_code: int, content_type: str = '', content_id: str = '', probe_triggered: str = None):
    """Log a response."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO responses (request_id, status_code, content_type, content_id, probe_triggered) VALUES (?, ?, ?, ?, ?)',
            (request_id, status_code, content_type, content_id, probe_triggered)
        )
        await db.commit()

async def log_behaviour_event(session_id: str, event_type: str, previous_action: str = '', current_action: str = '', delta_time: float = 0.0, strategy_changed: bool = False, detail: str = ''):
    """Log a behaviour event."""
    ts = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO behaviour_events (session_id, timestamp, event_type, previous_action, current_action, delta_time, strategy_changed, detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (session_id, ts, event_type, previous_action, current_action, delta_time, 1 if strategy_changed else 0, detail)
        )
        await db.commit()

async def upsert_session(session_id: str, source_ip: str = 'unknown', agenticity_score: int = 0, agenticity_data: dict = None):
    """Create or update a session."""
    ts = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        # Get actual request count
        count_cur = await db.execute('SELECT COUNT(*) FROM requests WHERE session_id = ?', (session_id,))
        count_row = await count_cur.fetchone()
        real_count = count_row[0] if count_row else 1

        existing = await db.execute('SELECT session_id FROM sessions WHERE session_id = ?', (session_id,))
        row = await existing.fetchone()
        if row:
            if agenticity_data is not None:
                await db.execute(
                    'UPDATE sessions SET last_seen = ?, request_count = ?, agenticity_score = ?, agenticity_data = ?, source_ip = ? WHERE session_id = ?',
                    (ts, real_count, agenticity_score, json.dumps(agenticity_data), source_ip, session_id)
                )
            else:
                await db.execute(
                    'UPDATE sessions SET last_seen = ?, request_count = ?, source_ip = ? WHERE session_id = ?',
                    (ts, real_count, source_ip, session_id)
                )
        else:
            await db.execute(
                'INSERT INTO sessions (session_id, source_ip, first_seen, last_seen, request_count, agenticity_score, agenticity_data) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (session_id, source_ip, ts, ts, real_count, agenticity_score, json.dumps(agenticity_data or {}))
            )
        await db.commit()

def _safe_json_loads(val: str, default=None):
    if not val:
        return default if default is not None else {}
    try:
        return json.loads(val)
    except Exception:
        return default if default is not None else {}

async def get_session_requests(session_id: str) -> list[dict]:
    """Get all requests for a session, ordered by timestamp."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT * FROM requests WHERE session_id = ? ORDER BY timestamp ASC',
            (session_id,)
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            r = dict(row)
            r['headers'] = _safe_json_loads(r.get('headers'), {})
            results.append(r)
        return results

async def get_session_responses(session_id: str) -> list[dict]:
    """Get all responses for a session's requests."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            '''SELECT r.* FROM responses r
               JOIN requests req ON r.request_id = req.id
               WHERE req.session_id = ?
               ORDER BY req.timestamp ASC''',
            (session_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_session_events(session_id: str) -> list[dict]:
    """Get all behaviour events for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT * FROM behaviour_events WHERE session_id = ? ORDER BY timestamp ASC',
            (session_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_session(session_id: str) -> dict | None:
    """Get a session with full details."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        session = dict(row)
        session['agenticity_data'] = _safe_json_loads(session.get('agenticity_data'), {})
        return session

async def get_all_sessions() -> list[dict]:
    """Get all sessions, ordered by last_seen desc."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM sessions ORDER BY last_seen DESC')
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            s = dict(row)
            s['agenticity_data'] = _safe_json_loads(s.get('agenticity_data'), {})
            results.append(s)
        return results

async def clear_all_data():
    """Clear all records from all honeypot tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM behaviour_events')
        await db.execute('DELETE FROM responses')
        await db.execute('DELETE FROM requests')
        await db.execute('DELETE FROM sessions')
        await db.commit()
