"""
Minimal dashboard: reads from the SQLite "MES" store the middleware writes
to, and serves the latest readings as JSON + a simple auto-refreshing
HTML page. Stands in for the "existing systems" side of the integration.

Run: python dashboard.py
Then open: http://localhost:8000
"""

import sqlite3

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

DB_PATH = "mes_data.db"

app = FastAPI(title="MES Dashboard (demo)")


def get_latest(n=20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM machine_readings ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/readings")
def api_readings():
    return get_latest(20)


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
    <head>
        <title>Simulated MES Dashboard</title>
        <meta http-equiv="refresh" content="2">
        <style>
            body { font-family: sans-serif; margin: 2rem; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
            th { background: #f0f0f0; }
            .alert { background: #ffdede; }
        </style>
    </head>
    <body>
        <h2>MachineTool_01 - Live Readings (via OPC UA -> Middleware -> SQLite)</h2>
        <table id="t">
            <tr>
                <th>Timestamp</th><th>Status</th><th>Spindle Speed (rpm)</th>
                <th>Temp (C)</th><th>Temp (F)</th><th>Part Count</th><th>Overheat</th>
            </tr>
        </table>
        <script>
            fetch('/api/readings').then(r => r.json()).then(data => {
                const t = document.getElementById('t');
                data.forEach(row => {
                    const tr = document.createElement('tr');
                    if (row.overheat_alert) tr.className = 'alert';
                    tr.innerHTML = `<td>${new Date(row.timestamp*1000).toLocaleTimeString()}</td>
                        <td>${row.machine_status}</td><td>${row.spindle_speed}</td>
                        <td>${row.temperature_c}</td><td>${row.temperature_f}</td>
                        <td>${row.part_count}</td><td>${row.overheat_alert ? 'YES' : ''}</td>`;
                    t.appendChild(tr);
                });
            });
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
