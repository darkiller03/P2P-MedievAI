# P2P-MedievAI: Complete Architecture Redesign

## Overview
Transform from **relay-based** to **fully distributed P2P** with proper Python/C IPC.

---

## New Architecture

### Process Layout
```
┌─────────────────────────────────────────────┐
│ Python Process (Game Logic)                 │
│ ├─ Main.py (entry point)                    │
│ ├─ GameEngine (state management)            │
│ └─ network_integration.py (sends commands)  │
└────────────┬────────────────────────────────┘
             │ IPC: Named Pipe or Unix Socket
             │ Protocol: Length-prefixed JSON
             │
┌────────────▼────────────────────────────────┐
│ C Process (P2P Network Node)                │
│ ├─ p2p_node.c (main entry)                  │
│ ├─ ipc_server.c (Python communication)      │
│ ├─ peer_manager.c (P2P connections)         │
│ ├─ message_protocol.c (framing + parsing)   │
│ ├─ peer_discovery.c (find other peers)      │
│ └─ state_sync.c (coherence handling)        │
└────────────┬────────────────────────────────┘
             │ TCP/UDP to other P2P nodes
             │ Direct peer connections
    ┌────────┼────────┐
    │                 │
┌───▼──────┐      ┌──▼──────┐
│ Peer B   │      │ Peer C   │
│ (Port N) │      │ (Port M) │
└──────────┘      └──────────┘
```

---

## Message Protocols

### 1. Python ↔ C IPC (Named Pipe on Windows, Unix Socket on Unix)

**Format**: Length-prefixed JSON
```
[4 bytes: uint32 length in network byte order][variable bytes: UTF-8 JSON]
```

**Example frames**:
```json
// Request ownership
{"cmd": "ACTION", "type": "REQUEST_OWNERSHIP", "unit_id": 42, "clock": 100}

// Send update
{"cmd": "UPDATE", "type": "MOVE", "unit_id": 42, "x": 10.5, "y": 20.3, "clock": 101}

// Receive state from peer
{"cmd": "STATE", "type": "GRANT_OWNERSHIP", "unit_id": 42, "owner_id": "player_a", "state": {...}, "clock": 102}
```

### 2. P2P Network Protocol (Direct Peer Connections via TCP)

**Format**: Same length-prefixed JSON

**Message Types**:
```json
// Peer handshake
{"type": "HELLO", "player_id": "player_a", "port": 9001, "clock": 0}

// Ownership transfer
{"type": "REQUEST_OWNERSHIP", "unit_id": 42, "player_id": "player_a", "clock": 100}
{"type": "GRANT_OWNERSHIP", "unit_id": 42, "owner_id": "player_a", "state": {...}, "clock": 101}

// Action broadcast
{"type": "MOVE", "unit_id": 42, "x": 10.5, "y": 20.3, "owner_id": "player_a", "clock": 102}
{"type": "ATTACK", "attacker_id": 1, "target_id": 2, "owner_id": "player_a", "clock": 103}

// Full state sync (on join)
{"type": "FULL_STATE", "units": [...], "clock": 500}

// Coherence check
{"type": "STATE_HASH", "hash": "abc123...", "clock": 501}
```

---

## Conflict Resolution

### Logical Clock
- **Definition**: Each local action increments clock
- **Broadcast**: Clock sent with every message
- **Received Messages**: Update local clock = max(local_clock, received_clock) + 1

### Concurrent Request Resolution
```
If Player A and B simultaneously request ownership of Unit X:
1. A sends: {"type": "REQUEST_OWNERSHIP", "unit_id": X, "player_id": "A", "clock": 100}
2. B sends: {"type": "REQUEST_OWNERSHIP", "unit_id": X, "player_id": "B", "clock": 100}

Resolution (tiebreaker):
- Current owner: "A" or "B" (compare player_id alphabetically)
- If same player: Lower clock wins
- If same clock: player_id alphabetically wins

Result: Loser gets OWNERSHIP_DENIED, must wait
```

---

## Peer Discovery

### Configuration File (`peers.conf`)
```
my_player_id=player_a
my_port=9001
peers=127.0.0.1:9002 127.0.0.1:9003 127.0.0.1:9004
```

On startup:
1. Read own player_id and port
2. Try connecting to each peer in `peers` list
3. Accept incoming connections on `my_port`
4. When peer joins, broadcast HELLO to verify connection

---

## IPC Message Flow

### Python sends action to C:
```python
# Python side
client.send_ipc_message({
    "cmd": "ACTION",
    "type": "REQUEST_OWNERSHIP",
    "unit_id": 42
})
```

```c
// C side receives via named pipe
struct ipc_message msg = read_ipc_message(ipc_fd);
// msg.cmd = "ACTION"
// msg.type = "REQUEST_OWNERSHIP"
// msg.unit_id = 42
// msg.local_clock = <incremented>

// C forwards to all peers:
broadcast_peer_message({
    "type": "REQUEST_OWNERSHIP",
    "unit_id": 42,
    "player_id": "player_a",
    "clock": <local_clock>
});
```

### C receives action from peer, forwards to Python:
```c
// C receives from peer
struct network_message net_msg = read_peer_message(peer_sock);
// net_msg.type = "GRANT_OWNERSHIP"
// net_msg.unit_id = 42
// net_msg.owner_id = "player_b"

// C verifies coherence (hidden from Python)
if (is_valid_transition(net_msg)) {
    // Forward to Python
    write_ipc_message(ipc_fd, {
        "cmd": "STATE",
        "type": "GRANT_OWNERSHIP",
        "unit_id": 42,
        "owner_id": "player_b",
        "state": {...},
        "clock": net_msg.clock
    });
} else {
    // Drop invalid message, don't send to Python
    log_rejection(net_msg);
}
```

---

## File Structure

```
C Network Process (NEW):
├── p2p_node.c/h                 (main entry point)
├── ipc_server.c/h               (named pipe server for Python)
├── peer_manager.c/h             (manages peer connections)
├── message_protocol.c/h         (length-prefixed framing)
├── peer_discovery.c/h           (initial peer list + HELLO handshake)
├── state_sync.c/h               (coherence via clocks + hashing)
├── conflict_resolution.c/h      (Lamport clock + tiebreaker)
└── peers.conf                   (configuration)

Python Game Process (MODIFIED):
├── p2p_ipc_client.py            (replaces p2p_client.py - use named pipe)
├── network_integration.py       (add clock tracking)
└── Main.py                      (unchanged)
```

---

## Implementation Phases

### Phase 1: Message Framing (Foundation)
- ✅ Implement length-prefixed protocol
- ✅ Binary-safe message parsing
- ✅ Validation + error handling

### Phase 2: Peer Discovery & Connection (P2P)
- ✅ Configuration file parser
- ✅ TCP peer connections (outbound + inbound)
- ✅ HELLO handshake
- ✅ Connection pooling

### Phase 3: IPC Layer (Python ↔ C)
- ✅ Named pipe (Windows) / Unix socket (Linux)
- ✅ Length-prefixed message exchange
- ✅ Bidirectional communication

### Phase 4: Conflict Resolution
- ✅ Lamport clock implementation
- ✅ Tiebreaker logic
- ✅ Request/grant protocol

### Phase 5: State Coherence
- ✅ Rollback on invalid transitions
- ✅ State hash verification
- ✅ Full sync on join

### Phase 6: Python Integration
- ✅ Replace P2PClient with IPC version
- ✅ Track local clock in GameEngine
- ✅ Request ownership before actions

---

## Coherence Guarantees

### Property 1: Single Owner
```
At any time T, unit U has exactly one owner O (no split-brain)

Proof:
1. All ownership grants handled at C process (single authority per peer)
2. Concurrent requests use deterministic tiebreaker (player_id + clock)
3. Loser doesn't execute action, waits for grant
```

### Property 2: State Consistency
```
When player receives state from owner, state matches owner's local state

Proof:
1. Owner sends state with ownership grant
2. Receiver accepts only if from current owner
3. If state diverges later, clock mismatch detected → full sync
```

### Property 3: Action Integrity
```
No action executes on dead unit (already killed by another player)

Proof:
1. Before action, requestor asks for ownership
2. If unit already owned by player B, ownership denied
3. If unit already dead, state received reflects death
```

---

## Testing Strategy

### Test 1: Two Peers, Sequential Ownership
```
1. Player A starts, places unit U
2. Player B joins, receives full state
3. Player A requests ownership of U → gets it
4. Player A moves U → broadcasts to B
5. Player B sees update
Verify: No conflicts, coherent state
```

### Test 2: Concurrent Ownership Requests
```
1. Player A and B both try to move same unit U
2. A sends REQUEST at clock 100
3. B sends REQUEST at clock 100
4. Owner (say A) gets grant
5. B gets OWNERSHIP_DENIED
Verify: Deterministic, no race condition
```

### Test 3: Three Peers, Chain Updates
```
1. Peers A, B, C initialized
2. A modifies unit → B receives → C receives
3. Verify all have same state
4. Hash check passes
Verify: Transitive update propagation
```

### Test 4: Peer Joining After Activity
```
1. A and B playing, have done 50 actions
2. C joins
3. C requests full state
4. C receives all units + current clocks
5. C continues playing coherently
Verify: New peer catches up correctly
```

