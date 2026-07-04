"""
Simulated OPC UA server for a machine tool.

Exposes a handful of tags that a real machine tool would expose:
- SpindleSpeed (rpm)
- Temperature (C)
- PartCount (int)
- MachineStatus (string: RUNNING / IDLE / FAULT)

Run: python server.py
Server endpoint: opc.tcp://0.0.0.0:4840/freeopcua/server/
"""

import asyncio
import random
import logging

from asyncua import Server, ua

logging.basicConfig(level=logging.WARNING)


async def main():
    server = Server()
    await server.init()

    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_server_name("Simulated Machine Tool OPC UA Server")

    # Set up a namespace for our machine, like a real vendor would
    uri = "http://example.org/machinetool"
    idx = await server.register_namespace(uri)

    # Create a folder/object representing the machine
    machine_obj = await server.nodes.objects.add_object(idx, "MachineTool_01")

    spindle_speed = await machine_obj.add_variable(idx, "SpindleSpeed", 0.0)
    temperature = await machine_obj.add_variable(idx, "Temperature", 20.0)
    part_count = await machine_obj.add_variable(idx, "PartCount", 0)
    machine_status = await machine_obj.add_variable(idx, "MachineStatus", "IDLE")

    # Make them writable in case the middleware or a test client wants to write
    for node in (spindle_speed, temperature, part_count, machine_status):
        await node.set_writable()

    print(f"Starting OPC UA server at opc.tcp://0.0.0.0:4840/freeopcua/server/")
    print(f"Namespace index: {idx}")

    parts_made = 0

    async with server:
        while True:
            await asyncio.sleep(1)

            # Simulate a machine running with some noise
            status_roll = random.random()
            if status_roll < 0.05:
                status = "FAULT"
                speed = 0.0
                temp = round(random.uniform(85, 95), 1)  # fault -> overheat
            elif status_roll < 0.15:
                status = "IDLE"
                speed = 0.0
                temp = round(random.uniform(20, 30), 1)
            else:
                status = "RUNNING"
                speed = round(random.uniform(1200, 1800), 1)
                temp = round(random.uniform(45, 75), 1)
                parts_made += 1

            await spindle_speed.write_value(speed)
            await temperature.write_value(temp)
            await part_count.write_value(parts_made)
            await machine_status.write_value(status)


if __name__ == "__main__":
    asyncio.run(main())
