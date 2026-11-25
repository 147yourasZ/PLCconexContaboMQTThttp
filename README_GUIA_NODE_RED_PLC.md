# Guía Completa de Instalación, Configuración y Conexión de Node-RED con PLC

**Carpeta del Proyecto:** `C:\Users\Albert\Desktop\PLC2 entrega 2`  
**Fecha de Configuración:** 19 de Noviembre de 2026  
**Proyecto PLC Detectado:** `App1.plcnx2` (Phoenix Contact PLCnext)  

---

## 1. Resumen de Instalación Local Realizada

Node-RED y sus nodos industriales clave han sido instalados satisfactoriamente en tu computador local.

| Componente | Versión / Estado | Descripción |
| :--- | :--- | :--- |
| **Node.js** | `v24.15.0` | Entorno de ejecución |
| **npm** | `11.12.1` | Gestor de paquetes |
| **Node-RED Core** | `v5.0.10` | Motor principal de flujos de automatización |
| **Directorio de Usuario** | `C:\Users\Albert\.node-red` | Ubicación de nodos e historial |
| **Servidor Web Local** | `http://localhost:1880` | Interfaz gráfica del editor de flujos |

---

## 2. Nodos Industriales e IP Instalados

Se instalaron los paquetes más importantes para comunicación con PLCs mediante red IP/Ethernet:

```text
C:\Users\Albert\.node-red
├── node-red-contrib-opcua         (Comunicación OPC UA - Recomendado PLCnext)
├── node-red-contrib-modbus        (Modbus TCP y RTU por Ethernet)
├── node-red-contrib-s7            (Siemens S7-300/400/1200/1500)
├── node-red-contrib-cip           (EtherNet/IP - Rockwell/Allen-Bradley/Omron)
├── node-red-dashboard             (Dashboard Clásico v1 - http://localhost:1880/ui)
└── @flowfuse/node-red-dashboard   (Dashboard Moderno v2)
```

---

## 3. Protocolos de Red, Puertos e IPs para Conexión con PLC

Para conectar un PLC físico o virtual a Node-RED por Ethernet, asegúrate de configurar tu tarjeta de red PC en el mismo rango de IP que el PLC.

### A. Protocolo OPC UA (Especial para Phoenix Contact AXC F 2152)
* **Puerto Predeterminado:** `4840`
* **URL del Endpoint:** `opc.tcp://<IP_PLC>:4840`  *(Ejemplo: `opc.tcp://192.168.1.10:4840`)*
* **Modo de Seguridad:** `None` / `Sign & Encrypt` (según configuración de PLCnext Engineer)
* **Ventajas:** Lectura directa por nombre de variable (tags) sin preocuparse por direcciones de memoria numéricas.

### B. Protocolo Modbus TCP
* **Puerto Predeterminado:** `502`
* **Dirección IP:** `<IP_DEL_PLC>` *(Ejemplo: `192.168.1.10`)*
* **Unit ID (Slave ID):** `1` (por defecto)
* **Funciones Comunes:**
  * **FC 1 (Read Coils):** Lectura de Salidas Digitales / Bits (`00001` - `09999`)
  * **FC 2 (Read Discrete Inputs):** Lectura de Entradas Digitales (`10001` - `19999`)
  * **FC 3 (Read Holding Registers):** Lectura de Registros / Variables Numéricas (`40001` - `49999`)
  * **FC 5 / FC 6 / FC 16:** Escritura de Bits y Registros.

### C. Protocolo Siemens S7 TCP/IP
* **Puerto Predeterminado:** `102`
* **Configuración:** Rack `0`, Slot `1` (S7-1200/1500) o Slot `2` (S7-300/400)
* **Direccionamiento:** `DB1,X0.0` (Bit), `DB1,INT2` (Entero), `DB1,REAL4` (Flotante)

### D. Protocolo MQTT
* **Puerto Predeterminado:** `1883` (sin SSL) / `8883` (con TLS)
* **Broker Local opcional:** `localhost`
* **Uso:** Telemetría e integración con nubes como Firebase o AWS IoT.

---

## 4. Pasos para Iniciar y Usar Node-RED

### Método 1: Mediante el archivo ejecutable creado
1. Ve a la carpeta: `C:\Users\Albert\Desktop\PLC2 entrega 2`
2. Haz doble clic en el archivo **`iniciar_node_red.bat`**.

### Método 2: Desde PowerShell o CMD
1. Abre PowerShell o el Símbolo del sistema.
2. Ejecuta el comando:
   ```powershell
   node-red
   ```
3. Abre Chrome o Edge y navega a:
   * **Editor de Flujos:** `http://localhost:1880`
   * **Dashboard de Control:** `http://localhost:1880/ui`

---

## 5. Configuración Específica para Phoenix Contact AXC F 2152 (`App1.plcnx2`)

1. **Configurar la IP en PLCnext Engineer:**
   * La IP por defecto del AXC F 2152 suele ser `192.168.1.10`.
   * Verifica la IP asignada en tu proyecto `App1.plcnx2`.
   * Configura la IP de la PC en estática (Ejemplo: `192.168.1.100`, Máscara: `255.255.255.0`).

2. **Habilitar servidor OPC UA en PLCnext Engineer:**
   * En el árbol del proyecto PLCnext, ve a `PLCnext -> OPC UA Server`.
   * Habilita el servidor OPC UA y marca las variables que deseas visibilizar con el atributo `OPC UA: Read/Write`.

3. **Importar Flujo de Ejemplo en Node-RED:**
   * En Node-RED, haz clic en el menú superior derecho `☰ -> Import`.
   * Selecciona el archivo `flow_ejemplo_plc.json` ubicado en esta misma carpeta (`C:\Users\Albert\Desktop\PLC2 entrega 2\flow_ejemplo_plc.json`).
   * Edita el nodo de conexión con la IP real de tu PLC y haz clic en **Deploy**.

---

## 6. Comandos de Verificación de Red

Antes de conectar Node-RED, prueba la comunicación física abriendo PowerShell y ejecutando:

```powershell
# 1. Probar conectividad IP con el PLC
ping 192.168.1.10

# 2. Verificar puerto OPC UA abierto
Test-NetConnection -ComputerName 192.168.1.10 -Port 4840

# 3. Verificar puerto Modbus TCP abierto
Test-NetConnection -ComputerName 192.168.1.10 -Port 502
```

---

## 7. Estructura Actual del Proyecto y Simulador OPC UA

El proyecto ha sido organizado de forma modular en `C:\Users\Albert\Desktop\PLC2 entrega 2`:

```text
PLC2 entrega 2/
├── App1.plcnx2                         # Proyecto PLCnext Engineer 2026.6 (AXC F 2152)
├── plcnext_st/                         # Rutinas IEC 61131-3 Structured Text (ST)
│   ├── PRG_Main.st
│   ├── PRG_Inputs.st
│   ├── PRG_Analog.st
│   ├── PRG_Communication.st
│   ├── PRG_Alarms.st
│   └── PRG_Motor.st
├── node-red/
│   └── flow_plcnext_scada.json         # Flujo importable (OPC UA + MQTT + Dashboard SCADA)
├── simulador_plc/
│   ├── simulador_axcf2152.py           # Simulador Python OPC UA local (127.0.0.1:4841)
│   └── simulador_mqtt_contabo.py       # Simulador Python -> MQTT Contabo (169.58.165.54:1883)
├── docs/
│   └── TABLA_MAESTRA_TAGS.md           # Tabla maestra de variables (Tags)
├── scripts/
│   └── verificar_entorno.ps1           # Script de diagnóstico de red y servicios
└── README_GUIA_NODE_RED_PLC.md
```

### A. Uso del Simulador Python OPC UA (Pruebas sin PLC físico)

Para probar el flujo completo de Node-RED y el Dashboard SCADA sin tener conectado el PLC físico:

1. Ejecuta el simulador en PowerShell:
   ```powershell
   python "C:\Users\Albert\Desktop\PLC2 entrega 2\simulador_plc\simulador_axcf2152.py"
   ```
2. **Endpoint del simulador:** `opc.tcp://127.0.0.1:4841`  
   *(Usa el puerto `4841` por defecto para evitar conflicto con el servicio `opcualds` de Windows en el puerto `4840`)*.
3. **Importar flujo en Node-RED (`http://localhost:1880`):**
   * Menú `☰ -> Import` y selecciona `node-red\flow_plcnext_scada.json`.
   * En el nodo `OPC UA Read PLC`, cambia temporalmente el endpoint a `opc.tcp://127.0.0.1:4841` (`Security Policy: None`, `Security Mode: None`).
   * En el nodo `Mosquitto Local (127.0.0.1)`, configura el usuario y contraseña definidos en `C:\Program Files\mosquitto\passwd` (ya que `allow_anonymous false` está activo).
   * Haz clic en **Deploy** y abre el SCADA en `http://localhost:1880/ui`.

### B. Simulador Python → MQTT Contabo (`169.58.165.54`)

Para enviar estados simulados directamente al broker MQTT del servidor Contabo (requiere credenciales MQTT) y verlos reflejados en `http://169.58.165.54/`:

```powershell
python "C:\Users\Albert\Desktop\PLC2 entrega 2\simulador_plc\simulador_mqtt_contabo.py" --user TU_USUARIO_MQTT --password TU_PASSWORD_MQTT
```

* Tópicos utilizados: `planta/plc1756/datos`, `planta/plc1756/ordenes`, `planta/plc1756/respuestas`, `planta/plc1756/estado_gateway`.
* Verificación de llegada en el servidor: `http://169.58.165.54/api/estado-actual` (campo `mensajes_mqtt_recibidos`).

### C. Paso a PLC Físico (`AXC F 2152`)

* **PLC Físico (`AXC F 2152`):** Una vez identificados los módulos Axioline F reales y cargadas las rutinas `plcnext_st/*.st` en `App1.plcnx2` (**PLCnext Engineer 2026.6**), cambia el endpoint en Node-RED a `opc.tcp://192.168.1.10:4840` y verifica los `NodeId` reales con UA Expert.

---

*Documentación actualizada para el proyecto de automatización industrial PLCnext + OPC UA + Node-RED + MQTT.*
