from pyscript import document
from datetime import datetime
from js import window
import json
from pyodide.http import pyfetch

def get_last_action(event):
    lst_action, action = last_action()
    statusDiv = document.querySelector('#status')
    statusDiv.innerText = lst_action

def last_action():
    log = window.localStorage.getItem("action_log")
    if log:
        log = json.loads(log)
    else:
        log = []
    
    opt = document.querySelector('#selectCategory')
    opt1 = [x for x in log if 'category' in x.keys() and x["category"] =='3dme']
    opt2 = [x for x in log if 'category' in x.keys() and x["category"] =='Housekeeping']
    opt3 = [x for x in log if 'category' in x.keys() and x["category"] =='Other']
    if opt.value == '3dme' and opt1:
        last_action_str = f"You last {opt1[-1]['action'].replace('_','ed ')} on {opt1[-1]['timestamp'][:10]} at {opt1[-1]['timestamp'][11:19]} for {opt1[-1]['category']}"
        action = opt1[-1]['action']
    elif opt.value == 'Housekeeping' and opt2:
        last_action_str = f"You last {opt2[-1]['action'].replace('_','ed ')} on {opt2[-1]['timestamp'][:10]} at {opt2[-1]['timestamp'][11:19]} for {opt2[-1]['category']}"
        action = opt2[-1]['action']
    elif opt.value == 'Other' and opt3:
        last_action_str = f"You last {opt3[-1]['action'].replace('_','ed ')} on {opt3[-1]['timestamp'][:10]} at {opt3[-1]['timestamp'][11:19]} for {opt3[-1]['category']}"
        action = opt3[-1]['action']
    else:
        last_action_str = f"No action for {opt.value} yet"
        action = None
    return last_action_str , action

async def clock_in(event):
    current_time = datetime.now().strftime('%H:%M:%S')
    statusDiv = document.querySelector('#status')
    opt = document.querySelector('#selectCategory')
    last_action_str, action = last_action()
    if action is None:
        action = 'init'
        last_action_str='First entry'
    if statusDiv and  ("clock_out" in action or 'init' in action):
        statusDiv.innerText = f"Status: Clocked in at {current_time} for {opt.value}"
        await log_action('clock_in',opt.value)
    else:
        statusDiv.innerText = f"You're already clocked in: {last_action_str}."
        
async def clock_out(event):
    current_time = datetime.now().strftime('%H:%M:%S')
    statusDiv = document.querySelector('#status')
    opt = document.querySelector('#selectCategory')
    last_action_str, action = last_action()
    if action is None:
        action = 'init'
        last_action_str='First entry'
    if statusDiv and "clock_in" in action:
        statusDiv.innerText = f"Status: Clocked out at {current_time} for {opt.value}"
        await log_action('clock_out',opt.value)
    elif action == 'init':
        statusDiv.innerText = f"You must first clock IN, before attempting to clock OUT"
    else:
        statusDiv.innerText = f"You're already clocked out: {last_action_str}. You must first clock IN."

def send_action(time,action):
    pass

async def log_action(action,category):
    # Load existing log
    log = window.localStorage.getItem("action_log")
    if log:
        log = json.loads(log)
    else:
        log = []

    # Append new action with timestamp
    action_data= {
        "category":category,
        "action": action,
        "timestamp": datetime.now().isoformat()
    }
    await send_action_log(action_data)
    log.append(action_data)

    # Save back to localStorage
    window.localStorage.setItem("action_log", json.dumps(log))

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
    api_res_div.innerText = txt
    