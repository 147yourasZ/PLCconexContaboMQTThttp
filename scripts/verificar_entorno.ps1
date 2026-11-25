# Script de verificación rápida del entorno Gateway (Windows 11)
Write-Host "=== 1. Adaptadores de Red ===" -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" } |
    Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table -AutoSize

Write-Host "=== 2. Conectividad hacia PLC (192.168.1.10) ===" -ForegroundColor Cyan
Test-Connection -ComputerName 192.168.1.10 -Count 2 -Quiet
Test-NetConnection -ComputerName 192.168.1.10 -Port 4840 | Select-Object ComputerName, RemotePort, TcpTestSucceeded

Write-Host "=== 3. Puertos locales (Node-RED 1880 / Mosquitto 1883) ===" -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 1880, 1883 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table -AutoSize

Write-Host "=== 4. Servicio Mosquitto ===" -ForegroundColor Cyan
Get-Service -Name "*mosquitto*" -ErrorAction SilentlyContinue | Format-Table Name, Status, StartType
