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
