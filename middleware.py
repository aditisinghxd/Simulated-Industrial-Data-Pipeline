"""
Middleware: connects to the machine's OPC UA server, subscribes to tag
changes, applies a small transform/alerting layer, and writes readings
into a SQLite database that acts as a stand-in "MES data store".

This is the piece that maps directly onto: "develop and maintain
middleware as an interface between the machine and existing systems."

Run: python middleware.py
(server.py must already be running)
"""

import asyncio
import sqlite3
import time

from asyncua import Client, ua

OPC_URL = "opc.tcp://localhost:4840/freeopcua/server/"
DB_PATH = "mes_data.db"

# Fahrenheit conversion + overheat threshold, standing in for a
# real transform you'd do between machine units and MES/ERP units.
OVERHEAT_THRESHOLD_C = 80.0


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            spindle_speed REAL,
            temperature_c REAL,
            temperature_f REAL,
            part_count INTEGER,
            machine_status TEXT,
            overheat_alert INTEGER
        )
        """
    )
    conn.commit()
    return conn


class SubscriptionHandler:
    """Handles OPC UA data change notifications and writes to the DB."""

    def __init__(self, conn, node_names):
        self.conn = conn
        self.node_names = node_names
        self.latest = {}

    def datachange_notification(self, node, val, data):
        name = self.node_names.get(node.nodeid.Identifier, str(node))
        self.latest[name] = val
        self._maybe_flush()

    def _maybe_flush(self):
        # Only insert a row once we have a fresh value for all four tags
        required = {"SpindleSpeed", "Temperature", "PartCount", "MachineStatus"}
        if not required.issubset(self.latest.keys()):
            return

        temp_c = self.latest["Temperature"]
        temp_f = round(temp_c * 9 / 5 + 32, 1)
        overheat = 1 if temp_c >= OVERHEAT_THRESHOLD_C else 0

        if overheat:
            print(f"[ALERT] Overheat detected: {temp_c} C")

        self.conn.execute(
            """
            INSERT INTO machine_readings
            (timestamp, spindle_speed, temperature_c, temperature_f,
             part_count, machine_status, overheat_alert)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                self.latest["SpindleSpeed"],
                temp_c,
                temp_f,
                self.latest["PartCount"],
                self.latest["MachineStatus"],
                overheat,
            ),
        )
        self.conn.commit()


async def main():
    conn = init_db()

    async with Client(url=OPC_URL) as client:
        idx = await client.get_namespace_index("http://example.org/machinetool")
        machine_obj = await client.nodes.objects.get_child(f"{idx}:MachineTool_01")

        spindle_speed = await machine_obj.get_child(f"{idx}:SpindleSpeed")
        temperature = await machine_obj.get_child(f"{idx}:Temperature")
        part_count = await machine_obj.get_child(f"{idx}:PartCount")
        machine_status = await machine_obj.get_child(f"{idx}:MachineStatus")

        node_names = {
            spindle_speed.nodeid.Identifier: "SpindleSpeed",
            temperature.nodeid.Identifier: "Temperature",
            part_count.nodeid.Identifier: "PartCount",
            machine_status.nodeid.Identifier: "MachineStatus",
        }

        handler = SubscriptionHandler(conn, node_names)
        sub = await client.create_subscription(500, handler)
        await sub.subscribe_data_change(
            [spindle_speed, temperature, part_count, machine_status]
        )

        print("Middleware running. Subscribed to machine tags. Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
