#include "conflict_resolution.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

ClockManager* clock_manager_new(const char *player_id) {
    if (!player_id) {
        fprintf(stderr, "[ERROR] clock_manager_new: player_id is NULL\n");
        return NULL;
    }

    ClockManager *cm = (ClockManager *)malloc(sizeof(ClockManager));
    if (!cm) {
        perror("malloc");
        return NULL;
    }

    cm->local_clock = 0;
    cm->player_id = player_id;  // Assume static or caller-managed

    return cm;
}

void clock_manager_free(ClockManager *cm) {
    if (!cm) return;
    free(cm);
}

LamportClock clock_increment(ClockManager *cm) {
    if (!cm) return 0;
    cm->local_clock++;
    return cm->local_clock;
}

LamportClock clock_update(ClockManager *cm, LamportClock received_clock) {
    if (!cm) return received_clock;
    
    if (received_clock > cm->local_clock) {
        cm->local_clock = received_clock + 1;
    } else {
        cm->local_clock++;
    }
    
    return cm->local_clock;
}

LamportClock clock_get_current(const ClockManager *cm) {
    if (!cm) return 0;
    return cm->local_clock;
}

int resolve_conflict(
    LamportClock this_clock, const char *this_player_id,
    LamportClock other_clock, const char *other_player_id
) {
    if (!this_player_id || !other_player_id) {
        fprintf(stderr, "[ERROR] resolve_conflict: NULL player_id\n");
        return 0;
    }

    // Rule 1: Lower clock wins (earlier causality)
    if (this_clock < other_clock) {
        return 1;  // This player wins
    }
    if (this_clock > other_clock) {
        return -1; // Other player wins
    }

    // Rule 2: Same clock, use player_id alphabetically
    int cmp = strcmp(this_player_id, other_player_id);
    if (cmp < 0) {
        return 1;  // this_player_id is alphabetically before
    }
    if (cmp > 0) {
        return -1; // other_player_id is alphabetically before
    }

    // Should not happen (comparing same player)
    return 0;
}

bool causality_violated(LamportClock local_clock, LamportClock received_clock) {
    // Very simple check: if received clock is too far in the past relative to local,
    // it might indicate a problem
    // 
    // For now, we accept any received_clock that's <= local_clock
    // A more sophisticated check would track per-peer clocks and detect
    // anomalies (e.g., message from peer going backwards)
    
    if (received_clock > local_clock + 1000) {
        // Received clock is suspiciously far in the future
        // Could indicate tampering or very bad clock skew
        return true;
    }

    return false;
}
