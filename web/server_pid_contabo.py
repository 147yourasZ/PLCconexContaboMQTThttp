import csv
import json
import os
import threading
import time
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import paho.mqtt.client as mqtt

WEB_PORT = 8090
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, "dashboard_scada.html")
CSV_PATH = os.path.join(BASE_DIR, "registro_pid_tanque.csv")

MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883
MQTT_USER = "scada_web"
MQTT_PASS = "PLC_Scada2026!"
TOPIC_DATOS = "planta/plc1756/datos"
TOPIC_ORDENES = "planta/plc1756/ordenes"


class ContaboTankState:
    def __init__(self):
        self.lock = threading.Lock()
        self.t0 = time.monotonic()
        self.last_rx = 0.0
        self.modo = "PID"
        self.sistema_activo = True
        self.di_start = False
        self.di_stop = False
        self.usar_pot_fio = False
        self.descarga_auto = True
        self.setpoint_pct = 50.0
        self.nivel_pct = 0.0
        self.nivel_cm = 0.0
        self.nivel_v = 0.0
        self.flow_v = 0.0
        self.fill_pct = 0.0
        self.discharge_pct = 35.0
        self.kp = 3.2
        self.ki = 0.25
        self.kd = 1.8

        self.max_points = 600
        self.hist_t = deque(maxlen=self.max_points)
        self.hist_sp = deque(maxlen=self.max_points)
        self.hist_pv = deque(maxlen=self.max_points)
        self.hist_fill = deque(maxlen=self.max_points)
        self.hist_desc = deque(maxlen=self.max_points)

        self.registrando_csv = True
        self.muestras_guardadas = 0
        self.csv_file = None
        self.csv_writer = None
        self.iniciar_csv(sobrescribir=False)

    def iniciar_csv(self, sobrescribir: bool = False):
        if self.csv_file:
            try:
                self.csv_file.close()
            except Exception:
                pass
        existe = (not sobrescribir) and os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0
        self.csv_file = open(CSV_PATH, "a" if existe else "w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        if not existe:
            self.csv_writer.writerow([
                "timestamp", "tiempo_s", "modo_control", "setpoint_pct", "setpoint_cm",
                "nivel_pct", "nivel_cm", "nivel_voltios", "error_pct",
                "fill_valve_pct", "discharge_valve_pct", "flow_voltios", "kp", "ki", "kd"
            ])
            self.csv_file.flush()
            self.muestras_guardadas = 0
        else:
            try:
                with open(CSV_PATH, "r", encoding="utf-8") as fr:
                    self.muestras_guardadas = max(0, sum(1 for _ in fr) - 1)
            except Exception:
                self.muestras_guardadas = 0

    def reset_hist(self):
        with self.lock:
            self.t0 = time.monotonic()
            self.hist_t.clear()
            self.hist_sp.clear()
            self.hist_pv.clear()
            self.hist_fill.clear()
            self.hist_desc.clear()
            self.iniciar_csv(sobrescribir=True)

    def on_telemetry(self, data: dict):
        # Accept only tank PID payloads (or map fields safely)
        if "nivel_pct" not in data and "Nivel_Pct" not in data:
            return
        now = time.monotonic()
        t_s = now - self.t0
        with self.lock:
            self.last_rx = now
            self.modo = str(data.get("modo", self.modo))
            self.sistema_activo = bool(data.get("sistema_activo", self.sistema_activo))
            self.di_start = bool(data.get("di_start", self.di_start))
            self.di_stop = bool(data.get("di_stop", self.di_stop))
            if "usar_pot_fio" in data:
                self.usar_pot_fio = bool(data["usar_pot_fio"])
            self.setpoint_pct = float(data.get("setpoint_pct", self.setpoint_pct))
            self.nivel_pct = float(data.get("nivel_pct", self.nivel_pct))
            self.nivel_cm = float(data.get("nivel_cm", (self.nivel_pct / 100.0) * 300.0))
            self.nivel_v = float(data.get("nivel_v", (self.nivel_pct / 100.0) * 10.0))
            self.flow_v = float(data.get("flow_v", self.flow_v))
            self.fill_pct = float(data.get("fill_valve_pct", data.get("fill_pct", self.fill_pct)))
            self.discharge_pct = float(data.get("discharge_valve_pct", data.get("discharge_pct", self.discharge_pct)))
            self.kp = float(data.get("kp", self.kp))
            self.ki = float(data.get("ki", self.ki))
            self.kd = float(data.get("kd", self.kd))

            self.hist_t.append(round(t_s, 2))
            self.hist_sp.append(round(self.setpoint_pct, 2))
            self.hist_pv.append(round(self.nivel_pct, 2))
            self.hist_fill.append(round(self.fill_pct, 2))
            self.hist_desc.append(round(self.discharge_pct, 2))

            if self.registrando_csv and self.csv_writer:
                sp_cm = (self.setpoint_pct / 100.0) * 300.0
                err_pct = self.setpoint_pct - self.nivel_pct
                self.csv_writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    f"{t_s:.3f}", self.modo, f"{self.setpoint_pct:.2f}", f"{sp_cm:.2f}",
                    f"{self.nivel_pct:.2f}", f"{self.nivel_cm:.2f}", f"{self.nivel_v:.3f}",
                    f"{err_pct:.2f}", f"{self.fill_pct:.2f}", f"{self.discharge_pct:.2f}",
                    f"{self.flow_v:.3f}", f"{self.kp:.4f}", f"{self.ki:.4f}", f"{self.kd:.4f}"
                ])
                self.csv_file.flush()
                self.muestras_guardadas += 1

    def to_dict(self):
        with self.lock:
            conectado = (time.monotonic() - self.last_rx) < 5.0 if self.last_rx > 0 else False
            return {
                "conectado": conectado,
                "host": "169.58.165.54",
                "port": 1883,
                "modo": self.modo,
                "sistema_activo": self.sistema_activo,
                "di_start": self.di_start,
                "di_stop": self.di_stop,
                "usar_pot_fio": self.usar_pot_fio,
                "descarga_auto": self.descarga_auto,
                "setpoint_pct": self.setpoint_pct,
                "nivel_pct": self.nivel_pct,
                "nivel_cm": self.nivel_cm,
                "nivel_v": self.nivel_v,
                "flow_v": self.flow_v,
                "fill_pct": self.fill_pct,
                "discharge_pct": self.discharge_pct,
                "kp": self.kp,
                "ki": self.ki,
                "kd": self.kd,
                "registrando_csv": self.registrando_csv,
                "muestras_guardadas": self.muestras_guardadas,
                "hist_t": list(self.hist_t),
                "hist_sp": list(self.hist_sp),
                "hist_pv": list(self.hist_pv),
                "hist_fill": list(self.hist_fill),
                "hist_desc": list(self.hist_desc),
            }


STATE = ContaboTankState()
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="contabo_tanque_pid_web")


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        client.subscribe(TOPIC_DATOS, qos=0)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        STATE.on_telemetry(data)
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path in ("/", "/index.html", "/dashboard_scada.html"):
            with open(HTML_PATH, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif self.path.startswith("/api/state"):
            data = json.dumps(STATE.to_dict()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path.startswith("/api/download-csv"):
            if os.path.exists(CSV_PATH):
                with open(CSV_PATH, "rb") as f:
                    b = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="registro_pid_tanque.csv"')
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            else:
                self.send_error(404, "CSV no encontrado")
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        if self.path.startswith("/api/control"):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            with STATE.lock:
                if "setpoint_pct" in payload:
                    STATE.setpoint_pct = max(0.0, min(100.0, float(payload["setpoint_pct"])))
                if "usar_pot_fio" in payload:
                    STATE.usar_pot_fio = bool(payload["usar_pot_fio"])
                if "modo" in payload and payload["modo"] in ("PID", "MANUAL"):
                    STATE.modo = payload["modo"]
                if "sistema_activo" in payload:
                    STATE.sistema_activo = bool(payload["sistema_activo"])
                if "descarga_auto" in payload:
                    STATE.descarga_auto = bool(payload["descarga_auto"])
                if "kp" in payload and "ki" in payload and "kd" in payload:
                    STATE.kp = float(payload["kp"])
                    STATE.ki = float(payload["ki"])
                    STATE.kd = float(payload["kd"])
                if "csv_action" in payload:
                    if payload["csv_action"] == "toggle":
                        STATE.registrando_csv = not STATE.registrando_csv
                    elif payload["csv_action"] == "reset":
                        STATE.t0 = time.monotonic()
                        STATE.hist_t.clear()
                        STATE.hist_sp.clear()
                        STATE.hist_pv.clear()
                        STATE.hist_fill.clear()
                        STATE.hist_desc.clear()
                        STATE.iniciar_csv(sobrescribir=True)
            mqtt_client.publish(TOPIC_ORDENES, json.dumps(payload), qos=1)
            resp = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_error(404, "Not found")


def main():
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    mqtt_client.loop_start()

    srv = ThreadingHTTPServer(("0.0.0.0", WEB_PORT), Handler)
    print(f"Tank PID SCADA Web running on 0.0.0.0:{WEB_PORT}")
    try:
        srv.serve_forever()
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        srv.server_close()


if __name__ == "__main__":
    main()

