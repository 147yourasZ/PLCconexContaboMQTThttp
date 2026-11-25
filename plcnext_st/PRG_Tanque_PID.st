(* ============================================================================
   PROGRAMA: PRG_Tanque_PID
   ENTORNO : Phoenix Contact PLCnext Engineer (AXC F 2152 - 2404267)
   MÓDULOS : -A2 (AXL F DI8/1 DO8/1 - 2701916) | -A3 (AXL F AI2 AO2 - 2702072)
   OBJETIVO: Única rutina de control PID de nivel de tanque con:
             - Perillas Start/Stop en -A2 + pilotos LED en -A2 y HMI Web
             - Potenciómetro local en -A3 (AI1 0..10V) para cambiar Setpoint
             - Barra LED en -A3 (AO1 0..10V) mostrando el nivel actual
   ============================================================================ *)
PROGRAM PRG_Tanque_PID
VAR
    (* Entradas físicas del Kit PLCnext (-A2 DI8/1 y -A3 AI1) *)
    DI_Start            : BOOL := FALSE;  (* Perilla 1 (-A2 DI1): Start *)
    DI_Stop             : BOOL := FALSE;  (* Perilla 2 (-A2 DI2): Stop *)
    DI_Modo_Local       : BOOL := FALSE;  (* Perilla 3 (-A2 DI3): TRUE = Setpoint desde potenciómetro local *)
    DI_Reset            : BOOL := FALSE;  (* Perilla 4 (-A2 DI4): Reset integral *)
    AI_Pot_Setpoint_Raw : REAL := 0.0;    (* -A3 AI1 (0..10V -> 0..30000): Potenciómetro Setpoint local *)

    (* Entradas desde Factory I/O (Modbus TCP) *)
    Level_Meter_Raw     : INT := 0;       (* Input Reg 0: 0..1000 (0.0..10.0 V) *)
    Flow_Meter_Raw      : INT := 0;       (* Input Reg 1: 0..1000 (0.0..10.0 V) *)
    Setpoint_Pot_Raw    : INT := 0;       (* Input Reg 2: 0..1000 (0.0..10.0 V) *)
    DI_FIO_Running      : BOOL := FALSE;  (* Discrete Input 3: Estado Run/Play Factory I/O *)

    (* Salidas físicas del Kit PLCnext (-A2 DO8/1 y -A3 AO1) *)
    DO_Light_Start      : BOOL := FALSE;  (* -A2 DO1: LED verde sistema activo / Start *)
    DO_Light_Stop       : BOOL := FALSE;  (* -A2 DO2: LED sistema detenido / Stop *)
    DO_Light_Local      : BOOL := FALSE;  (* -A2 DO3: LED modo potenciómetro local *)
    AO_Bargraph_Raw     : INT := 0;       (* -A3 AO1 (0..30000): Barra LED de nivel actual *)

    (* Salidas hacia Factory I/O (Modbus TCP) *)
    Fill_Valve_Raw      : INT := 0;       (* Holding Reg 0: 0..1000 (0.0..100.0 %) *)
    Discharge_Valve_Raw : INT := 0;       (* Holding Reg 1: 0..1000 (0.0..100.0 %) *)
    SP_Display_CM       : INT := 0;       (* Holding Reg 2: 0..300 cm *)
    PV_Display_CM       : INT := 0;       (* Holding Reg 3: 0..300 cm *)
    COIL_Start_Light    : BOOL := FALSE;  (* Coil 0: Piloto Start *)
    COIL_Reset_Light    : BOOL := FALSE;  (* Coil 1: Piloto Reset *)
    COIL_Stop_Light     : BOOL := FALSE;  (* Coil 2: Piloto Stop *)

    (* Variables de Medición e Ingeniería *)
    Nivel_Voltios       : REAL := 0.0;    (* Voltaje sensor nivel [0.0..10.0 V] *)
    Nivel_Pct           : REAL := 0.0;    (* Nivel actual [0.0..100.0 %] *)
    Nivel_CM            : REAL := 0.0;    (* Altura de agua [0.0..300.0 cm] *)
    Flow_Voltios        : REAL := 0.0;    (* Voltaje caudalímetro descarga [0.0..10.0 V] *)
    Setpoint_Pct        : REAL := 50.0;   (* Consigna deseada [0.0..100.0 %] *)
    Setpoint_CM         : REAL := 150.0;  (* Consigna en cm [0.0..300.0 cm] *)

    (* Variables del Controlador PID + Torricelli *)
    Sistema_Activo      : BOOL := TRUE;   (* TRUE = Activo, FALSE = Desactivado *)
    Modo_Control        : BOOL := TRUE;   (* TRUE = PID, FALSE = MANUAL *)
    Usar_Pot_FIO        : BOOL := TRUE;   (* TRUE = Usar potenciómetro del panel por defecto *)
    Descarga_Auto       : BOOL := TRUE;   (* TRUE = Ayuda con válvula de descarga si error < -0.8% *)
    PID_Kp              : REAL := 3.2000; (* Ganancia proporcional optimizada *)
    PID_Ki              : REAL := 0.2500; (* Ganancia integral optimizada *)
    PID_Kd              : REAL := 1.8000; (* Ganancia derivativa optimizada *)
    K_FF_Torricelli     : REAL := 0.8454; (* Factor de prealimentación Torricelli *)
    Ts                  : REAL := 0.2;    (* Periodo de muestreo [s] *)
    Altura_Max_CM       : REAL := 300.0;  (* Altura máxima del tanque [cm] *)

    PV_Filtrado         : REAL := 0.0;    (* Nivel filtrado EMA (alpha=0.25) *)
    dPV_Filtrado        : REAL := 0.0;    (* Derivada filtrada sobre PV (alpha_d=0.20) *)
    Error_Pct           : REAL := 0.0;    (* Error: Setpoint_Pct - PV_Filtrado [%] *)
    U_Feedforward       : REAL := 0.0;    (* Término feedforward [%] *)
    Fill_Valve_Pct      : REAL := 0.0;    (* Apertura comandada Fill valve [%] *)
    Fill_Manual_Pct     : REAL := 0.0;    (* Apertura manual Fill valve [%] *)
    Discharge_Valve_Pct : REAL := 35.0;   (* Apertura comandada Discharge valve [%] *)
    Discharge_Base_Pct  : REAL := 35.0;   (* Apertura base de descarga [%] *)

    (* Auxiliares internos del PID *)
    Integral_Error      : REAL := 0.0;
    Prev_PV_Filtrado    : REAL := 0.0;
    First_Scan          : BOOL := TRUE;
    rSP_Norm            : REAL := 0.0;
    rD_PV_Raw           : REAL := 0.0;
    rP_Term             : REAL := 0.0;
    rD_Term             : REAL := 0.0;
    rCand_I             : REAL := 0.0;
    rU_Raw              : REAL := 0.0;
    rU_PID              : REAL := 0.0;
    rExtra_Desc         : REAL := 0.0;
END_VAR

(* 1. Lógica de marcha / parada con perillas físicas de -A2 (Stop tiene prioridad) *)
IF DI_Stop THEN
    Sistema_Activo := FALSE;
ELSIF DI_Start THEN
    Sistema_Activo := TRUE;
END_IF;

IF DI_Reset THEN
    Integral_Error := 0.0;
    First_Scan     := TRUE;
END_IF;

(* Luces indicadoras físicas en módulo -A2 y Factory I/O *)
DO_Light_Start   := Sistema_Activo;
DO_Light_Stop    := NOT Sistema_Activo;
DO_Light_Local   := DI_Modo_Local OR Usar_Pot_FIO;
COIL_Start_Light := Sistema_Activo;
COIL_Stop_Light  := NOT Sistema_Activo;
COIL_Reset_Light := DI_Reset;

(* 2. Lectura y escalamiento de sensores (Factory I/O Scale=100 -> 0..1000) *)
Nivel_Voltios := INT_TO_REAL(Level_Meter_Raw) / 100.0;
IF Nivel_Voltios < 0.0 THEN Nivel_Voltios := 0.0; END_IF;
IF Nivel_Voltios > 10.0 THEN Nivel_Voltios := 10.0; END_IF;

Nivel_Pct    := (Nivel_Voltios / 10.0) * 100.0;
Nivel_CM     := (Nivel_Voltios / 10.0) * Altura_Max_CM;
Flow_Voltios := INT_TO_REAL(Flow_Meter_Raw) / 100.0;

(* Salida analógica -A3 AO1 (0..30000) para la barra LED del kit *)
AO_Bargraph_Raw := REAL_TO_INT((Nivel_Pct / 100.0) * 30000.0);

(* 3. Selección de Setpoint: Potenciómetro local del Kit (-A3 AI1) o Remoto (HMI Web) *)
IF DI_Modo_Local OR Usar_Pot_FIO THEN
    Setpoint_Pct := (AI_Pot_Setpoint_Raw / 30000.0) * 100.0;
END_IF;
IF Setpoint_Pct < 0.0 THEN Setpoint_Pct := 0.0; END_IF;
IF Setpoint_Pct > 100.0 THEN Setpoint_Pct := 100.0; END_IF;
Setpoint_CM := (Setpoint_Pct / 100.0) * Altura_Max_CM;

(* 4. Filtro exponencial EMA (alpha=0.25) y derivada filtrada (alpha_d=0.20) *)
IF First_Scan THEN
    PV_Filtrado      := Nivel_Pct;
    Prev_PV_Filtrado := Nivel_Pct;
    dPV_Filtrado     := 0.0;
    First_Scan       := FALSE;
ELSE
    Prev_PV_Filtrado := PV_Filtrado;
    PV_Filtrado      := (0.25 * Nivel_Pct) + (0.75 * PV_Filtrado);
    IF Ts > 0.0 THEN
        rD_PV_Raw    := (PV_Filtrado - Prev_PV_Filtrado) / Ts;
        dPV_Filtrado := (0.20 * rD_PV_Raw) + (0.80 * dPV_Filtrado);
    END_IF;
END_IF;

Error_Pct := Setpoint_Pct - PV_Filtrado;

(* 5. Cálculo de control PID + Feedforward de Torricelli o Manual *)
IF NOT Sistema_Activo THEN
    Fill_Valve_Pct      := 0.0;
    Discharge_Valve_Pct := 0.0;
    Integral_Error      := 0.0;
ELSIF Modo_Control THEN
    rSP_Norm := Setpoint_Pct / 100.0;
    IF rSP_Norm < 0.0 THEN rSP_Norm := 0.0; END_IF;
    U_Feedforward := K_FF_Torricelli * Discharge_Base_Pct * SQRT(rSP_Norm);

    IF Descarga_Auto AND (Error_Pct < -0.8) THEN
        Fill_Valve_Pct := 0.0;
        rExtra_Desc    := ABS(Error_Pct) * 3.5;
        IF rExtra_Desc > (100.0 - Discharge_Base_Pct) THEN
            rExtra_Desc := 100.0 - Discharge_Base_Pct;
        END_IF;
        Discharge_Valve_Pct := Discharge_Base_Pct + rExtra_Desc;
        Integral_Error      := Integral_Error * 0.95;
    ELSE
        Discharge_Valve_Pct := Discharge_Base_Pct;
        rP_Term             := PID_Kp * Error_Pct;
        rD_Term             := -PID_Kd * dPV_Filtrado;
        rCand_I             := Integral_Error + (Error_Pct * Ts);
        rU_Raw              := U_Feedforward + rP_Term + (PID_Ki * rCand_I) + rD_Term;

        IF ((rU_Raw >= 0.0) AND (rU_Raw <= 100.0)) OR
           ((rU_Raw > 100.0) AND (Error_Pct < 0.0)) OR
           ((rU_Raw < 0.0) AND (Error_Pct > 0.0)) THEN
            Integral_Error := rCand_I;
            IF Integral_Error > 150.0 THEN Integral_Error := 150.0; END_IF;
            IF Integral_Error < -150.0 THEN Integral_Error := -150.0; END_IF;
        END_IF;

        rU_PID := U_Feedforward + rP_Term + (PID_Ki * Integral_Error) + rD_Term;
        Fill_Valve_Pct := rU_PID;
    END_IF;
ELSE
    Fill_Valve_Pct      := Fill_Manual_Pct;
    Discharge_Valve_Pct := Discharge_Base_Pct;
END_IF;

(* Limitar aperturas de válvulas [0.0 .. 100.0 %] *)
IF Fill_Valve_Pct < 0.0 THEN Fill_Valve_Pct := 0.0; END_IF;
IF Fill_Valve_Pct > 100.0 THEN Fill_Valve_Pct := 100.0; END_IF;
IF Discharge_Valve_Pct < 0.0 THEN Discharge_Valve_Pct := 0.0; END_IF;
IF Discharge_Valve_Pct > 100.0 THEN Discharge_Valve_Pct := 100.0; END_IF;

(* 6. Conversión a registros enteros para Factory I/O *)
Fill_Valve_Raw      := REAL_TO_INT((Fill_Valve_Pct / 100.0) * 1000.0);
Discharge_Valve_Raw := REAL_TO_INT((Discharge_Valve_Pct / 100.0) * 1000.0);
SP_Display_CM       := REAL_TO_INT(Setpoint_CM);
PV_Display_CM       := REAL_TO_INT(Nivel_CM);

END_PROGRAM
