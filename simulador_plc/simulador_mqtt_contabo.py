"""
Simulador PLC en Python -> Envía estados en vivo por MQTT al servidor Contabo (169.58.165.54:1883)
y permite verificar en http://169.58.165.54/api/estado-actual que los datos están llegando.
"""

import argparse
import json
import math
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

BROKER_HOST = "169.58.165.54"
BROKER_PORT = 1883

TOPIC_DATOS = "planta/plc1756/datos"
TOPIC_ORDENES = "planta/plc1756/ordenes"
TOPIC_RESPUESTAS = "planta/plc1756/respuestas"
TOPIC_ESTADO_GW = "planta/plc1756/estado_gateway"


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador PLC -> MQTT Contabo")
    parser.add_argument("--host", default=BROKER_HOST)
    parser.add_argument("--port", type=int, default=BROKER_PORT)
    parser.add_argument("--user", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--count", type=int, default=0, help="0 = infinito, >0 = enviar N ciclos y salir")
    args = parser.parse_args()

    estado = {
        "Temperatura_Tanque": 25.0,
        "Nivel_Entrada_Litros": 350,
        "Motor_Mezclador": False,
        "Valvula_Sustancia_1": True,
        "Valvula_Sustancia_2": False,
        "Valvula_Sustancia_3": False,
        "Valvula_Sustancia_4": False,
        "Valvula_Vaciado": False,
        "Estado_Proceso": 100,
        "Fallo_Proceso": False,
        "Emergencia": False,
        "Alarma_Temperatura": False,
        "Contador_Lotes": 5072,
        "Heartbeat": 1,
    }

    connected_flag = {"ok": False, "rc": None}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        connected_flag["rc"] = reason_code
        connected_flag["ok"] = (reason_code == 0)
        print(f"[MQTT] Conectado a {args.host}:{args.port} -> rc={reason_code}")
        if reason_code == 0:
            client.subscribe(TOPIC_ORDENES, qos=1)
            gw_status = {
                "plc": "AXC F 2152 (Simulador Python)",
                "ip": "192.168.1.10",
                "plc_conectado": True,
                "escritura_habilitada": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            client.publish(TOPIC_ESTADO_GW, json.dumps(gw_status), qos=1, retain=True)

    def on_message(client, userdata, msg):
        try:
            cmd = json.loads(msg.payload.decode("utf-8"))
            print(f"[ORDEN RECIBIDA] {cmd}")
            req_id = cmd.get("request_id") or cmd.get("comando_id") or "sim_ack"
            tag = cmd.get("tag")
            val = cmd.get("valor")
            if tag in estado:
                estado[tag] = val
            ack = {
                "request_id": req_id,
                "comando_id": req_id,
                "comando": cmd.get("comando", "escribir_tag"),
                "tag": tag,
                "valor": val,
                "exito": True,
                "escritura_realizada": True,
                "estado": "CONFIRMADO_GATEWAY",
                "mensaje": f"Simulador Python aplicó {tag}={val}",
                "timestamp_gateway": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            client.publish(TOPIC_RESPUESTAS, json.dumps(ack), qos=1)
        except Exception as exc:
            print(f"[ERROR ORDEN] {exc}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sim_plc_python_local")
    if args.user:
        client.username_pw_set(args.user, args.password)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(args.host, args.port, keepalive=30)
    client.loop_start()

    # Esperar breve conexión
    for _ in range(20):
        if connected_flag["rc"] is not None:
            break
        time.sleep(0.1)

    if not connected_flag["ok"]:
        print(f"[ERROR] No se pudo conectar/autenticar en {args.host}:{args.port} (rc={connected_flag['rc']})")
        client.loop_stop()
        return

    t0 = time.monotonic()
    sent = 0
    try:
        while True:
            elapsed = time.monotonic() - t0
            # Simular ciclo dinámico realista
            fase = int(elapsed // 5) % 4
            estado["Temperatura_Tanque"] = round(26.0 + 4.5 * math.sin(elapsed * 0.3), 1)
            estado["Nivel_Entrada_Litros"] = int(500 + 350 * math.sin(elapsed * 0.2))
            estado["Valvula_Sustancia_1"] = (fase == 0)
            estado["Valvula_Sustancia_2"] = (fase == 1)
            estado["Motor_Mezclador"] = (fase == 2)
            estado["Valvula_Vaciado"] = (fase == 3)
            estado["Estado_Proceso"] = [100, 200, 300, 400][fase]
            estado["Heartbeat"] += 1

            payload = json.dumps(estado)
            info = client.publish(TOPIC_DATOS, payload, qos=0)
            info.wait_for_publish(timeout=3)
            sent += 1
            print(f"[TX #{sent}] HB={estado['Heartbeat']} Temp={estado['Temperatura_Tanque']}C Nivel={estado['Nivel_Entrada_Litros']}L Motor={estado['Motor_Mezclador']}")

            if args.count > 0 and sent >= args.count:
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nSimulador detenido por usuario.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
