# SelfConnect Mesh — Setup Guide

Step-by-step bring-up of the three-node Windows ↔ Spark-1 ↔ Spark-2 mesh.

---

## Prerequisites

| Node | Requirement |
|------|-------------|
| Windows PC | Python 3.10+, `pywin32`, SSH server on :9877 |
| Spark-1 | Python 3.10+, Hub service on :8765 |
| Spark-2 | Python 3.10+, `xdotool` (for Linux injection) |

Network: Windows ↔ Spark-1 over LAN; Spark-1 ↔ Spark-2 over internal network.

---

## Step 1 — Windows Side

### 1a. Start windows_agent.py (I/O pipe)

```bash
# On Windows PC
python windows_agent.py --port 9877
```

This opens a TCP server. Accepts commands: `send`, `read`, `capture`, `list_windows`.

### 1b. Start hub_relay.py (discovery pipe)

```bash
# On Windows PC
python core/hub_relay.py --hub-url http://SPARK1_IP:8765
```

This polls the Hub for incoming `CMD:` messages and executes them using `self_connect.py`.

---

## Step 2 — Spark-1 Side

### 2a. Start the Hub

```bash
# On Spark-1
cd ~/ai-business/
python hub.py --port 8765
```

The Hub is the relay broker for discovery messages. It doesn't handle I/O — just CMD routing.

---

## Step 3 — Spark-2 Side

### 3a. Verify SSH tunnel to Windows

```bash
# On Spark-2
ssh -N -L 9877:WINDOWS_IP:9877 rblake2320@SPARK1_IP &
# Now localhost:9877 on Spark-2 reaches windows_agent.py on Windows
```

### 3b. Test the I/O pipe

```python
# On Spark-2
from windows_agent_client import WindowsAgentClient
client = WindowsAgentClient(host='localhost', port=9877)
windows = client.list_windows()
print(windows)
```

### 3c. Test the discovery pipe

```python
# On Spark-2
from spark2_client import Spark2Client
client = Spark2Client(hub_url='http://SPARK1_IP:8765')
windows = client.list_windows()
print(windows)
```

---

## Step 4 — Full Round-Trip Test

```python
# On Spark-2 — inject text into a Windows terminal
from windows_agent_client import WindowsAgentClient
from mesh_wire import MeshWire

wire = MeshWire()
client = WindowsAgentClient(host='localhost', port=9877)

# Find the Windows Claude terminal
windows = client.list_windows()
target = next(w for w in windows if w['title'].startswith('AXIOM'))

# Governed inject
wire.dispatch({
    'agent_id': 'cc-spark2',
    'target_id': 'axiom-windows-claude',  # logical name, not raw HWND
    'action': 'terminal.inject.chat',
    'payload': 'Hello from Spark-2\r'
})
```

Expected: text appears in the AXIOM Windows terminal. The ledger (`mesh_wire_ledger.jsonl`) gains a new entry.

---

## Kill Switch

To stop all injection immediately:

```bash
# On Windows
set WIRE_ENABLED=0
# Or set the env var in windows_agent.py's process
```

`mesh_wire.py` checks `WIRE_ENABLED` before every dispatch. Set to `0` to deny all.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `list_windows()` returns empty | hub_relay.py not running on Windows | Start it |
| Injection drops characters | `char_delay` too low | Use `char_delay=0.02` minimum |
| `Unknown target_id` denied | TARGET_REGISTRY out of date | Update registry with current HWND |
| HWNDs changed | Rebooted Windows | Re-enumerate: run `list_windows()` and update TARGET_REGISTRY |
| SSH tunnel not connecting | Port 9877 not forwarded | Check SSH config, firewall |
