from pyscript import document
from datetime import datetime
from js import window
import json
from pyodide.http import pyfetch
import sqlite3
try:
    from pyodide.ffi import create_proxy
except Exception:
    try:
        from pyodide import create_proxy
    except Exception:
        # fallback: return the original callable (works if Pyodide accepts Python callables directly)
        def create_proxy(fn):
            return fn

DB_PATH = "/data/actions.db"
_conn = None
_cur = None

def _init_db_after_load(err):
    global _conn, _cur
    window.console.log("IDBFS load callback, err:", err)
    try:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _cur = _conn.cursor()
        _cur.execute(
            """
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        _conn.commit()
        window.console.log("DB opened and table ensured at", DB_PATH)
    except sqlite3.Error as e:
        api_res_div = document.querySelector('#api_res')
        if api_res_div:
            api_res_div.innerText = f"DB init error: {e}"

# ensure /data exists and is mounted to IDBFS
try:
    window.FS.mkdir('/data')
except Exception:
    pass

try:
    window.FS.mount(window.IDBFS, {}, '/data')
except Exception:
    pass

window.FS.syncfs(True, create_proxy(_init_db_after_load))

def _persist_db():
    def _done(err):
        window.console.log("IDBFS persist callback, err:", err)
    try:
        window.FS.syncfs(False, create_proxy(_done))
    except Exception as e:
        window.console.error("Failed to persist DB:", e)

def get_last_action(event):
    lst_action, action = last_action()
    statusDiv = document.querySelector('#status')
    if statusDiv:
        statusDiv.innerText = lst_action

def last_action():
    if _cur is None:
        return ("DB not ready yet", None)

    opt = document.querySelector('#selectCategory')
    if not opt:
        return ("No category selected", None)
    cat = opt.value

    if not cat:
        return ("No category selected", None)

    try:
        _cur.execute(
            "SELECT category, action, timestamp FROM actions WHERE category = ? ORDER BY timestamp DESC LIMIT 1",
            (cat,)
        )
        row = _cur.fetchone()
    except sqlite3.Error as e:
        return (f"DB error: {e}", None)

    if row:
        last_action_str = f"You last {row['action'].replace('_','ed ')} on {row['timestamp'][:10]} at {row['timestamp'][11:19]} for {row['category']}"
        action = row['action']
    else:
        last_action_str = f"No action for {cat} yet"
        action = None
    return last_action_str, action

async def clock_in(event):
    current_time = datetime.now().strftime('%H:%M:%S')
    statusDiv = document.querySelector('#status')
    opt = document.querySelector('#selectCategory')
    last_action_str, action = last_action()
    if action is None:
        action = 'init'
        last_action_str = 'First entry'
    if statusDiv and ("clock_out" in action or 'init' in action):
        statusDiv.innerText = f"Status: Clocked in at {current_time} for {opt.value}"
        await log_action('clock_in', opt.value)
    else:
        statusDiv.innerText = f"You're already clocked in: {last_action_str}."

async def clock_out(event):
    current_time = datetime.now().strftime('%H:%M:%S')
    statusDiv = document.querySelector('#status')
    opt = document.querySelector('#selectCategory')
    last_action_str, action = last_action()
    if action is None:
        action = 'init'
        last_action_str = 'First entry'
    if statusDiv and "clock_in" in action:
        statusDiv.innerText = f"Status: Clocked out at {current_time} for {opt.value}"
        await log_action('clock_out', opt.value)
    elif action == 'init':
        statusDiv.innerText = f"You must first clock IN, before attempting to clock OUT"
    else:
        statusDiv.innerText = f"You're already clocked out: {last_action_str}. You must first clock IN."

def send_action(time, action):
    # preserved placeholder from original; no-op by design
    pass

async def log_action(action, category):
    # Build action record
    action_data = {
        "category": category,
        "action": action,
        "timestamp": datetime.now().isoformat()
    }

    # Attempt to send to remote API (non-blocking for local DB write)
    try:
        await send_action_log(action_data)
    except Exception:
        # ignore send errors; still log locally
        pass

    if _cur is None:
        api_res_div = document.querySelector('#api_res')
        if api_res_div:
            api_res_div.innerText = "DB not ready yet; action not saved locally."
        return

    try:
        _cur.execute(
            "INSERT INTO actions (category, action, timestamp) VALUES (?, ?, ?)",
            (action_data["category"], action_data["action"], action_data["timestamp"])
        )
        _conn.commit()
        _persist_db()
    except sqlite3.Error as e:
        api_res_div = document.querySelector('#api_res')
        if api_res_div:
            api_res_div.innerText = f"DB insert failed: {e}"

async def send_action_log(payload):
    url = 'http://192.168.12.184:8000/record'
    response = await pyfetch(
        url,
        method="PUT",
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload)
    )
    txt = await response.text()
    api_res_div = document.querySelector('#api_res')
    if api_res_div:
        api_res_div.innerText = txt