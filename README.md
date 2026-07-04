# Simulated Industrial Data Pipeline: OPC UA to MES Integration

A small, self-contained demo of the core integration pattern behind
machine data acquisition and MES/ERP integration: a machine exposes data
over **OPC UA**, a **middleware** layer subscribes to it, transforms it,
and writes it into a data store, and a simple **dashboard** reads that
store the way a MES/monitoring system would.

This is a learning/demo project, not a production deployment — it uses a
simulated machine rather than real hardware, and SQLite rather than a
real MES/SAP system. The architecture and integration pattern are the
same as a real deployment; the specific systems are simplified stand-ins.

## Architecture

```
+-------------------+       OPC UA        +------------------+      SQL      +-----------------+      HTTP     +-----------+
| Simulated Machine  | -----------------> |    Middleware     | -----------> |   SQLite ("MES")  | -----------> | Dashboard |
| (server.py)        |   tag subscription |  (middleware.py)  |   insert     |   mes_data.db      |   read/query | (dashboard.py) |
+-------------------+                     +------------------+              +-----------------+               +-----------+
     SpindleSpeed                          - subscribes to tags                 machine_readings table            localhost:8000
     Temperature                           - converts C -> F                                                      live table view
     PartCount                             - flags overheat (>80C)
     MachineStatus                         - writes each reading to DB
```

- **server.py** — an OPC UA server simulating a machine tool. Exposes four
  tags (`SpindleSpeed`, `Temperature`, `PartCount`, `MachineStatus`) that
  update every second with randomized-but-realistic values, including
  occasional `FAULT` states.
- **middleware.py** — an OPC UA client that subscribes to those tags,
  applies a transform (Celsius to Fahrenheit, overheat alerting), and
  writes each reading into a SQLite table (`mes_data.db`), acting as the
  interface between the machine and a downstream system.
- **dashboard.py** — a FastAPI app that reads the SQLite store and serves
  a live-updating table of recent readings, standing in for a MES/monitoring
  frontend.

## Why this maps to real industrial IT work

- OPC UA is the standard protocol for machine data acquisition in modern
  manufacturing (used by Siemens, Beckhoff, and most machine tool vendors).
- The middleware pattern here (subscribe -> transform -> forward to
  system-of-record) is the same shape as connecting a machine to a real
  MES/ERP/SAP system, just with SQLite standing in for the enterprise system.
- The project deliberately separates concerns (acquisition, transformation,
  storage, presentation) the way a real integration would.

## Running it

Requires Python 3.10+.

```bash
pip install -r requirements.txt

# Terminal 1
python server.py

# Terminal 2 (after server is running)
python middleware.py

# Terminal 3
python dashboard.py
# then open http://localhost:8000
```

## What this is / isn't

- **Is:** a working demonstration of OPC UA data acquisition, middleware
  transformation, and downstream integration, built and tested end-to-end.
- **Isn't:** a production deployment, a real MES/SAP integration, or
  professional industrial experience. Framed and used as a self-directed
  learning project.

## Possible extensions

- Multiple simulated machines on one server
- Write-back to the machine (e.g. remote stop on FAULT)
- Swap SQLite for a real MES-style REST API or MQTT broker
- Add authentication/encryption to the OPC UA connection (the demo runs
  with no security policy for simplicity)
