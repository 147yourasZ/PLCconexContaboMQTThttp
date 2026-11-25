"""
Simulador OPC UA del PLC Phoenix Contact AXC F 2152
Expone las mismas variables y NodeIds (ns=6;s=Arp.Plc.Eclr/MainInstance.<TAG>)
que el flujo de Node-RED (flow_plcnext_scada.json).
"""

import argparse
import asyncio
import math
import time
from asyncua import Server, ua


async def main(host: str, port: int) -> None:
    server = Server()
    await server.init()

    endpoint = f"opc.tcp://{host}:{port}"
    server.set_endpoint(endpoint)
    server.set_server_name("AXC F 2152 Simulator (Python OPC UA)")

    # Permitir conexión sin seguridad (None) para pruebas locales con Node-RED / UA Expert
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    # Registrar namespaces hasta alcanzar ns=6 para coincidir con PLCnext
    for n in range(2, 6):
        await server.register_namespace(f"urn:plcnext:sim:ns{n}")
    idx = await server.register_namespace("http://www.phoenixcontact.com/PLCnext/Arp.Plc.Eclr")
    assert idx == 6, f"Se esperaba ns=6 pero se obtuvo ns={idx}"

    objects = server.nodes.objects
    plc_obj = await objects.add_object(ua.NodeId("Arp.Plc.Eclr/MainInstance", idx), "MainInstance")

    async def add_tag(name: str, val, vtype: ua.VariantType, writable: bool = False):
        node = await plc_obj.add_variable(
            ua.NodeId(f"Arp.Plc.Eclr/MainInstance.{name}", idx),
            name,
            ua.Variant(val, vtype),
            varianttype=vtype,
        )
        if writable:
            await node.set_writable()
        return node

    tags = {
        "DI_Start": await add_tag("DI_Start", False, ua.VariantType.Boolean),
        "DI_Stop": await add_tag("DI_Stop", False, ua.VariantType.Boolean),
        "AI_Sensor_Raw": await add_tag("AI_Sensor_Raw", 0, ua.VariantType.Int32),
        "AI_Sensor_Voltage": await add_tag("AI_Sensor_Voltage", 0.0, ua.VariantType.Float),
        "AI_Sensor_Percent": await add_tag("AI_Sensor_Percent", 0.0, ua.VariantType.Float),
        "DO_Motor": await add_tag("DO_Motor", False, ua.VariantType.Boolean),
        "DO_LED": await add_tag("DO_LED", False, ua.VariantType.Boolean),
        "CMD_Motor_Start": await add_tag("CMD_Motor_Start", False, ua.VariantType.Boolean, writable=True),
        "CMD_Motor_Stop": await add_tag("CMD_Motor_Stop", False, ua.VariantType.Boolean, writable=True),
        "CMD_LED": await add_tag("CMD_LED", False, ua.VariantType.Boolean, writable=True),
        "CMD_Reset_Alarm": await add_tag("CMD_Reset_Alarm", False, ua.VariantType.Boolean, writable=True),
        "SYS_PLC_Heartbeat": await add_tag("SYS_PLC_Heartbeat", 0, ua.VariantType.UInt32),
        "SYS_Gateway_Heartbeat": await add_tag("SYS_Gateway_Heartbeat", 0, ua.VariantType.UInt32, writable=True),
        "SYS_Communication_OK": await add_tag("SYS_Communication_OK", False, ua.VariantType.Boolean),
        "SYS_Motor_Status": await add_tag("SYS_Motor_Status", False, ua.VariantType.Boolean),
        "SYS_Alarm": await add_tag("SYS_Alarm", False, ua.VariantType.Boolean),
        "SYS_Sensor_Valid": await add_tag("SYS_Sensor_Valid", True, ua.VariantType.Boolean),
        "SYS_System_Ready": await add_tag("SYS_System_Ready", True, ua.VariantType.Boolean),
        "DIAG_Last_Error": await add_tag("DIAG_Last_Error", "", ua.VariantType.String),
    }

    print("=" * 60)
    print(" Simulador PLC AXC F 2152 (OPC UA) iniciado")
    print(f" Endpoint local : {endpoint}")
    print(" Namespace      : ns=6 (Arp.Plc.Eclr/MainInstance.*)")
    print(" Presiona Ctrl+C para detener")
    print("=" * 60)

    motor_latch = False
    alarm_latched = False
    plc_hb = 0
    last_gw_hb = 0
    last_gw_time = time.monotonic()
    last_hb_tick = time.monotonic()
    t0 = time.monotonic()

    async with server:
        while True:
            now = time.monotonic()

            # 1. Simular sensor analógico 0-10 V (onda senoidal suave)
            elapsed = now - t0
            voltage = 5.0 + 4.5 * math.sin(elapsed * 0.25)
            percent = (voltage / 10.0) * 100.0
            raw = int((voltage / 10.0) * 30000)

            await tags["AI_Sensor_Raw"].write_value(ua.Variant(raw, ua.VariantType.Int32))
            await tags["AI_Sensor_Voltage"].write_value(ua.Variant(round(voltage, 2), ua.VariantType.Float))
            await tags["AI_Sensor_Percent"].write_value(ua.Variant(round(percent, 1), ua.VariantType.Float))

            # 2. Heartbeat del PLC (cada 1 s)
            if now - last_hb_tick >= 1.0:
                plc_hb += 1
                last_hb_tick = now
                await tags["SYS_PLC_Heartbeat"].write_value(ua.Variant(plc_hb, ua.VariantType.UInt32))

            # 3. Watchdog sobre SYS_Gateway_Heartbeat
            gw_hb = await tags["SYS_Gateway_Heartbeat"].read_value()
            if gw_hb != last_gw_hb:
                last_gw_hb = gw_hb
                last_gw_time = now
                comm_ok = True
            else:
                comm_ok = (now - last_gw_time) < 5.0

            await tags["SYS_Communication_OK"].write_value(ua.Variant(comm_ok, ua.VariantType.Boolean))

            # 4. Procesar comandos remotos escritos por Node-RED
            cmd_start = await tags["CMD_Motor_Start"].read_value()
            cmd_stop = await tags["CMD_Motor_Stop"].read_value()
            cmd_led = await tags["CMD_LED"].read_value()
            cmd_reset = await tags["CMD_Reset_Alarm"].read_value()

            if cmd_stop:
                motor_latch = False
                await tags["CMD_Motor_Stop"].write_value(ua.Variant(False, ua.VariantType.Boolean))
                print("[PLC SIM] CMD_Motor_Stop recibido -> Motor DETENIDO")

            if cmd_start:
                if not alarm_latched and comm_ok:
                    motor_latch = True
                    print("[PLC SIM] CMD_Motor_Start recibido -> Motor EN MARCHA")
                else:
                    await tags["DIAG_Last_Error"].write_value(
                        ua.Variant("CMD_REMOTE_START_REJECTED_INTERLOCK", ua.VariantType.String)
                    )
                await tags["CMD_Motor_Start"].write_value(ua.Variant(False, ua.VariantType.Boolean))

            if cmd_reset:
                alarm_latched = False
                await tags["DIAG_Last_Error"].write_value(ua.Variant("OK_ALARM_RESET", ua.VariantType.String))
                await tags["CMD_Reset_Alarm"].write_value(ua.Variant(False, ua.VariantType.Boolean))
                print("[PLC SIM] CMD_Reset_Alarm recibido -> Alarma restablecida")

            # 5. Actualizar salidas físicas simuladas
            do_led = motor_latch or (bool(cmd_led) and comm_ok)
            await tags["DO_Motor"].write_value(ua.Variant(motor_latch, ua.VariantType.Boolean))
            await tags["SYS_Motor_Status"].write_value(ua.Variant(motor_latch, ua.VariantType.Boolean))
            await tags["DO_LED"].write_value(ua.Variant(do_led, ua.VariantType.Boolean))
            await tags["SYS_Alarm"].write_value(ua.Variant(alarm_latched, ua.VariantType.Boolean))
            await tags["SYS_System_Ready"].write_value(ua.Variant(not alarm_latched, ua.VariantType.Boolean))

            await asyncio.sleep(0.2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador OPC UA AXC F 2152")
    parser.add_argument("--host", default="127.0.0.1", help="IP local de escucha (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=4841, help="Puerto OPC UA (default: 4841, evita conflicto con opcualds en 4840)")
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port))
