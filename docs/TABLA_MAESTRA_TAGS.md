# Tabla Maestra de Etiquetas — Control PID de Nivel de Tanque (`PRG_Tanque_PID`)

Todas las etiquetas corresponden exclusivamente al nuevo proyecto **Control de Nivel de Tanque mediante PID + Torricelli** (Factory I/O Modbus TCP `172.26.32.1:502` + PLCnext OPC UA `192.168.1.10:4840`).

- **CSV para importar en PLCnext Engineer:** [PRG_Tanque_PID_variables.csv](file:///d:/Entrga2/COMPLCconexMQTT-main/plcnext_st/csv/PRG_Tanque_PID_variables.csv)
- **Diccionario completo de medición:** [etiquetas_variables_medicion.csv](file:///d:/Entrga2/COMPLCconexMQTT-main/plcnext_st/csv/etiquetas_variables_medicion.csv)
- **Rutina única ST:** [PRG_Tanque_PID.st](file:///d:/Entrga2/COMPLCconexMQTT-main/plcnext_st/PRG_Tanque_PID.st)

## Etiquetas Principales (OPC UA / SCADA / Factory I/O)

| Etiqueta PLCnext | Tipo | Origen / Destino | Descripción |
| :--- | :--- | :--- | :--- |
| `Level_Meter_Raw` | `INT` | Factory I/O `Input Reg 0` | Sensor de nivel crudo `0..1000` (`Scale=100`) |
| `Flow_Meter_Raw` | `INT` | Factory I/O `Input Reg 1` | Caudalímetro descarga crudo `0..1000` |
| `Setpoint_Pot_Raw` | `INT` | Factory I/O `Input Reg 2` | Potenciómetro consigna crudo `0..1000` |
| `DI_Start`, `DI_Reset`, `DI_Stop`, `DI_FIO_Running` | `BOOL` | Factory I/O `Input 0..3` | Pulsadores del panel (`Stop` NC) y estado Run |
| `Fill_Valve_Raw`, `Discharge_Valve_Raw` | `INT` | Factory I/O `Holding Reg 0..1` | Comandos `0..1000` hacia válvulas proporcionales |
| `SP_Display_CM`, `PV_Display_CM` | `INT` | Factory I/O `Holding Reg 2..3` | Displays numéricos `0..300 cm` en Factory I/O |
| `COIL_Start_Light`, `COIL_Reset_Light`, `COIL_Stop_Light` | `BOOL` | Factory I/O `Coil 0..2` | Pilotos luminosos del panel |
| `Nivel_Voltios`, `Nivel_Pct`, `Nivel_CM`, `Flow_Voltios` | `REAL` | PLC → SCADA / Web | Mediciones escaladas (`V`, `%`, `cm`) |
| `Setpoint_Pct`, `Setpoint_CM` | `REAL` | SCADA ↔ PLC | Consigna de nivel (`%` y `cm`) |
| `PV_Filtrado`, `dPV_Filtrado`, `Error_Pct`, `U_Feedforward` | `REAL` | PLC → Diagnóstico | Filtro EMA, derivada filtrada, error y feedforward |
| `Fill_Valve_Pct`, `Discharge_Valve_Pct` | `REAL` | PLC → SCADA / Web | Aperturas actuales de válvulas (`0..100 %`) |
| `PID_Kp`, `PID_Ki`, `PID_Kd`, `K_FF_Torricelli` | `REAL` | SCADA ↔ PLC | Ganancias PID (`3.2`, `0.25`, `1.8`) y `K_ff` (`0.8454`) |
| `Sistema_Activo`, `Modo_Control`, `Usar_Pot_FIO`, `Descarga_Auto` | `BOOL` | SCADA ↔ PLC | Estado marcha, modo `PID/MANUAL`, fuente SP y descarga |
| `Fill_Manual_Pct`, `Discharge_Base_Pct` | `REAL` | SCADA ↔ PLC | Consignas manuales de válvulas (`%`) |
