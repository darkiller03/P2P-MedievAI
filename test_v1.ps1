# VERSION 1 Test Script for Windows
# Best-effort network synchronization demonstration

$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$GAME_DIR = Join-Path $PROJECT_DIR "age" "FinalCode"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VERSION 1: Best-Effort Network Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$SERVER_PORT = 9001

# Function to check if server is running
function Test-Server {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $SERVER_PORT)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

# Check if server is running
if (Test-Server) {
    Write-Host "[+] Relay server already running on port $SERVER_PORT" -ForegroundColor Green
} else {
    Write-Host "[!] Relay server NOT running on port $SERVER_PORT" -ForegroundColor Yellow
    Write-Host "[*] Please start the relay server manually:" -ForegroundColor Yellow
    Write-Host "    cd $PROJECT_DIR" -ForegroundColor Yellow
    Write-Host "    .\tcp_relay_server.exe $SERVER_PORT" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""
Write-Host "[*] Launching game in offline mode (no network)..." -ForegroundColor Blue
Write-Host "    This runs the simulation locally to establish a baseline." -ForegroundColor Yellow
Write-Host ""

Set-Location $GAME_DIR

# Run offline test
Write-Host "[TEST 1] Offline battle (baseline)" -ForegroundColor Cyan
python Main.py run tiny_scenario DAFT BrainDead -d test_offline.txt

Write-Host ""
Write-Host "[+] Offline test complete. Results saved to test_offline.txt" -ForegroundColor Green
Write-Host ""

# Check if we can run networked test
if (Test-Server) {
    Write-Host "[TEST 2] Networked battle (V1 best-effort)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[PLAYER 1 MODE]" -ForegroundColor Yellow
    Write-Host "Running as Player 1..." -ForegroundColor Yellow
    python Main.py run tiny_scenario DAFT BrainDead --net-enable --net-local-player 1 -d test_net_p1.txt
    
    Write-Host ""
    Write-Host "[+] Player 1 test complete. Results saved to test_net_p1.txt" -ForegroundColor Green
    Write-Host ""
    Write-Host "[OPTIONAL] To also run Player 2 in another terminal:" -ForegroundColor Yellow
    Write-Host "    python Main.py run tiny_scenario DAFT BrainDead --net-enable --net-local-player 2 -d test_net_p2.txt" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "[!] Relay server not available. Skipping networked test." -ForegroundColor Red
    Write-Host "[*] Start the relay server and run this script again." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Results" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (Test-Path "test_offline.txt") {
    Write-Host ""
    Write-Host "[+] Offline test results:" -ForegroundColor Green
    (Get-Content test_offline.txt) | Select-String -Pattern "Winner|Battle ended" | ForEach-Object { Write-Host "    $_" }
}

if (Test-Path "test_net_p1.txt") {
    Write-Host ""
    Write-Host "[+] Player 1 network results:" -ForegroundColor Green
    (Get-Content test_net_p1.txt) | Select-String -Pattern "Winner|Battle ended|Total inconsistencies" | ForEach-Object { Write-Host "    $_" }
}

Write-Host ""
Write-Host "[*] Summary:" -ForegroundColor Blue
Write-Host "    Compare results between offline and networked modes to see"
Write-Host "    how inconsistencies emerge in best-effort synchronization."
Write-Host ""
Write-Host "[*] Documentation: see VERSION1.md for protocol details" -ForegroundColor Blue
Write-Host ""
