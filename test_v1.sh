#!/bin/bash
# VERSION 1 Test Script - Best-effort network synchronization

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="$(dirname "$(realpath "$0")")"
GAME_DIR="$PROJECT_DIR/age/FinalCode"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}VERSION 1: Best-Effort Network Test${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if server is running
SERVER_PORT=9001

check_server() {
    if nc -z 127.0.0.1 $SERVER_PORT 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to start relay server
start_relay_server() {
    echo -e "${YELLOW}[*] Attempting to compile and start relay server...${NC}"
    
    # Compile C server
    if command -v gcc &> /dev/null; then
        pushd "$PROJECT_DIR" > /dev/null
        gcc -o tcp_relay_server tcp_relay_server.c -lws2_32 -Wall 2>/dev/null || {
            echo -e "${RED}[!] GCC not available for Windows MinGW. Skipping server compilation.${NC}"
            popd > /dev/null
            return 1
        }
        
        # Start server in background
        ./tcp_relay_server.exe $SERVER_PORT &
        SERVER_PID=$!
        echo -e "${GREEN}[+] Relay server started (PID: $SERVER_PID)${NC}"
        
        popd > /dev/null
        sleep 2
        return 0
    else
        echo -e "${RED}[!] GCC not found. Please compile tcp_relay_server.c manually.${NC}"
        return 1
    fi
}

# Check if server is already running
if check_server; then
    echo -e "${GREEN}[+] Relay server already running on port $SERVER_PORT${NC}"
    SKIP_SERVER_STOP=1
else
    echo -e "${YELLOW}[*] Relay server not detected on port $SERVER_PORT${NC}"
    start_relay_server
    if [ $? -ne 0 ]; then
        echo -e "${RED}[!] Failed to start relay server. You can run it manually:${NC}"
        echo -e "${YELLOW}    cd $PROJECT_DIR${NC}"
        echo -e "${YELLOW}    ./tcp_relay_server.exe 9001${NC}"
        echo ""
    fi
fi

echo ""
echo -e "${BLUE}[*] Launching game in offline mode (no network)...${NC}"
echo -e "${YELLOW}    This runs the simulation locally to establish a baseline.${NC}"

cd "$GAME_DIR"

# Run offline test
echo ""
echo -e "${BLUE}[TEST 1] Offline battle (baseline)${NC}"
python Main.py run tiny_scenario DAFT BrainDead -d test_offline.txt

echo ""
echo -e "${GREEN}[+] Offline test complete. Results saved to test_offline.txt${NC}"
echo ""

# Check if we can run networked test
if check_server; then
    echo -e "${BLUE}[TEST 2] Networked battle (V1 best-effort)${NC}"
    echo -e "${YELLOW}    Start another terminal and run:${NC}"
    echo -e "${YELLOW}    cd '$GAME_DIR'${NC}"
    echo -e "${YELLOW}    python Main.py run tiny_scenario DAFT BrainDead --net-enable --net-local-player 2 -d test_net_p2.txt${NC}"
    echo ""
    
    # Run as player 1
    python Main.py run tiny_scenario DAFT BrainDead --net-enable --net-local-player 1 -d test_net_p1.txt
    
    echo ""
    echo -e "${GREEN}[+] Networked test complete.${NC}"
    echo -e "${GREEN}    Player 1 results: test_net_p1.txt${NC}"
    echo -e "${YELLOW}    (Wait for Player 2 to finish, results will be in test_net_p2.txt)${NC}"
else
    echo -e "${RED}[!] Relay server not available. Skipping networked test.${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Results${NC}"
echo -e "${BLUE}========================================${NC}"

if [ -f test_offline.txt ]; then
    echo ""
    echo -e "${GREEN}[+] Offline test results:${NC}"
    grep -E "Winner|inconsistencies|total_inconsistencies" test_offline.txt 2>/dev/null || echo "    (no metrics in file)"
fi

if [ -f test_net_p1.txt ]; then
    echo ""
    echo -e "${GREEN}[+] Player 1 network results:${NC}"
    grep -E "Winner|inconsistencies|NETWORK METRICS" test_net_p1.txt 2>/dev/null | head -10 || echo "    (no metrics in file)"
fi

echo ""
echo -e "${BLUE}[*] Summary:${NC}"
echo -e "    Compare results between offline and networked modes to see"
echo -e "    how inconsistencies emerge in best-effort synchronization."
echo ""

# Cleanup (optional)
if [ $SKIP_SERVER_STOP -ne 1 ] && [ ! -z "$SERVER_PID" ]; then
    read -p "Stop relay server? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $SERVER_PID
        echo -e "${GREEN}[+] Server stopped${NC}"
    fi
fi

echo -e "${BLUE}[*] Documentation: see VERSION1.md for protocol details${NC}"
