"""
Generic middleware: connects to ANY OPC UA server (not just our own
simulated machine), auto-discovers variable tags by browsing the
address space, subscribes to all of them, and logs changes to SQLite.

This demonstrates the middleware pattern generalized beyond one
hardcoded server -- the same script works against:
  - our own simulated machine (server.py in this repo)
  - Prosys OPC UA Simulation Server (opc.tcp://localhost:53530/OPCUA/SimulationServer)
  - in principle, any other OPC UA server

Usage:
    python middleware_generic.py --url opc.tcp://localhost:4840/freeopcua/server/
    python middleware_generic.py --url opc.tcp://localhost:53530/OPCUA/SimulationServer
"""

import argparse
import asyncio
import sqlite3
import time

from asyncua import Client, ua

DB_PATH = "external_readings.db"
MAX_BROWSE_DEPTH = 3

# Every OPC UA server exposes these standard built-in folders
# (server diagnostics, aliases, etc). We skip them so discovery
# only surfaces the actual application/vendor tags.
SKIP_TOP_LEVEL_NAMES = {"Server", "Aliases"}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS external_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            server_url TEXT,
            tag_name TEXT,
            value TEXT
        )
        """
    )
    conn.commit()
    return conn


async def discover_variables(node, depth=0, path=""):
    """Recursively browse from `node`, returning a list of (display_name, Node)
    for every Variable found, up to MAX_BROWSE_DEPTH levels deep."""
    found = []
    if depth > MAX_BROWSE_DEPTH:
        return found

    try:
        children = await node.get_children()
    except Exception:
        return found

    for child in children:
        try:
            browse_name = (await child.read_browse_name()).Name
            node_class = await child.read_node_class()
        except Exception:
            continue

        if depth == 0 and browse_name in SKIP_TOP_LEVEL_NAMES:
            continue

        full_path = f"{path}/{browse_name}" if path else browse_name

        if node_class == ua.NodeClass.Variable:
            found.append((full_path, child))
        elif node_class == ua.NodeClass.Object:
            found.extend(await discover_variables(child, depth + 1, full_path))

    return found


class GenericHandler:
    def __init__(self, conn, server_url, tag_names):
        self.conn = conn
        self.server_url = server_url
        self.tag_names = tag_names  # dict: node identifier -> display name

    def datachange_notification(self, node, val, data):
        name = self.tag_names.get(node.nodeid.Identifier, str(node))
        self.conn.execute(
            "INSERT INTO external_readings (timestamp, server_url, tag_name, value) "
            "VALUES (?, ?, ?, ?)",
            (time.time(), self.server_url, name, str(val)),
        )
        self.conn.commit()
        print(f"[{name}] = {val}")


async def main(url):
    conn = init_db()

    async with Client(url=url) as client:
        print(f"Connected to {url}")
        print("Discovering variable tags (browsing address space)...")

        variables = await discover_variables(client.nodes.objects)

        if not variables:
            print("No variable tags found under Objects. Nothing to subscribe to.")
            return

        print(f"Found {len(variables)} tags:")
        for name, _ in variables:
            print(f"  - {name}")

        tag_names = {node.nodeid.Identifier: name for name, node in variables}
        handler = GenericHandler(conn, url, tag_names)

        sub = await client.create_subscription(500, handler)
        await sub.subscribe_data_change([node for _, node in variables])

        print("\nSubscribed. Logging changes to external_readings.db. Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic OPC UA middleware")
    parser.add_argument(
        "--url",
        required=True,
        help="OPC UA server endpoint, e.g. opc.tcp://localhost:4840/freeopcua/server/",
    )
    args = parser.parse_args()
    asyncio.run(main(args.url))
