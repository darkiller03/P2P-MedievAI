"""
V1 Network Metrics Tracking - Best-effort Inconsistency Measurement

This module tracks:
1. Message latency (send to receive)
2. Race conditions (concurrent modifications)
3. State mismatches (position, HP, alive status)
4. Network events (joins, disconnects, resends)
"""

import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class MessageMetric:
    """Track a single message's latency."""
    msg_id: str
    sent_time: float
    received_time: float = 0.0
    latency_ms: float = 0.0

    def complete(self, received_time: float):
        self.received_time = received_time
        self.latency_ms = (received_time - self.sent_time) * 1000


@dataclass
class RaceCondition:
    """Record a race condition (concurrent modification)."""
    unit_id: int
    local_value: any
    remote_value: any
    timestamp: float = field(default_factory=time.time)
    race_type: str = "UNKNOWN"  # POSITION, HP, ALIVE, etc.


@dataclass
class NetworkMetrics:
    """Aggregate metrics for V1 demonstration."""
    
    total_messages_sent: int = 0
    total_messages_received: int = 0
    message_latencies: List[float] = field(default_factory=list)
    
    total_race_conditions: int = 0
    races_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    race_log: List[RaceCondition] = field(default_factory=list)
    
    total_state_mismatches: int = 0
    state_mismatches_by_unit: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    player_joins: List[Tuple[float, int]] = field(default_factory=list)  # (timestamp, player_id)
    disconnects: List[Tuple[float, int]] = field(default_factory=list)
    
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    
    def record_message_sent(self) -> str:
        """Record outbound message, return unique ID for tracking."""
        self.total_messages_sent += 1
        msg_id = f"msg_{self.total_messages_sent}"
        return msg_id
    
    def record_message_received(self, latency_ms: float):
        """Record inbound message latency."""
        self.total_messages_received += 1
        self.message_latencies.append(latency_ms)
    
    def record_race_condition(self, unit_id: int, race_type: str, local_val, remote_val):
        """Log a race condition."""
        self.total_race_conditions += 1
        self.races_by_type[race_type] += 1
        race = RaceCondition(
            unit_id=unit_id,
            local_value=local_val,
            remote_value=remote_val,
            race_type=race_type
        )
        self.race_log.append(race)
    
    def record_state_mismatch(self, unit_id: int):
        """Log a state mismatch for a unit."""
        self.total_state_mismatches += 1
        self.state_mismatches_by_unit[unit_id] += 1
    
    def record_player_join(self, player_id: int):
        """Log player join event."""
        self.player_joins.append((time.time(), player_id))
    
    def record_disconnect(self, player_id: int):
        """Log player disconnect event."""
        self.disconnects.append((time.time(), player_id))
    
    def finalize(self):
        """Mark end of metrics collection."""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict:
        """Return human-readable summary of all metrics."""
        avg_latency = (
            sum(self.message_latencies) / len(self.message_latencies)
            if self.message_latencies
            else 0.0
        )
        
        duration = self.end_time - self.start_time if self.end_time > 0 else time.time() - self.start_time
        
        return {
            'duration_sec': round(duration, 2),
            'messages': {
                'sent': self.total_messages_sent,
                'received': self.total_messages_received,
                'avg_latency_ms': round(avg_latency, 2),
                'max_latency_ms': max(self.message_latencies) if self.message_latencies else 0,
                'min_latency_ms': min(self.message_latencies) if self.message_latencies else 0,
            },
            'races': {
                'total': self.total_race_conditions,
                'by_type': dict(self.races_by_type),
            },
            'mismatches': {
                'total': self.total_state_mismatches,
                'affected_units': len(self.state_mismatches_by_unit),
            },
            'players': {
                'joins': len(self.player_joins),
                'disconnects': len(self.disconnects),
            }
        }
    
    def print_summary(self):
        """Print formatted metrics report."""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("NETWORK METRICS SUMMARY (V1 - Best-Effort)")
        print("="*60)
        
        print(f"\nDuration: {summary['duration_sec']}s")
        
        print(f"\nMessages:")
        print(f"  Sent: {summary['messages']['sent']}")
        print(f"  Received: {summary['messages']['received']}")
        print(f"  Latency - Avg: {summary['messages']['avg_latency_ms']:.2f}ms, "
              f"Max: {summary['messages']['max_latency_ms']:.2f}ms, "
              f"Min: {summary['messages']['min_latency_ms']:.2f}ms")
        
        print(f"\nRace Conditions: {summary['races']['total']}")
        for race_type, count in summary['races']['by_type'].items():
            print(f"  {race_type}: {count}")
        
        print(f"\nState Mismatches: {summary['mismatches']['total']} "
              f"(affecting {summary['mismatches']['affected_units']} units)")
        
        print(f"\nPlayer Events:")
        print(f"  Joins: {summary['players']['joins']}")
        print(f"  Disconnects: {summary['players']['disconnects']}")
        
        print("="*60 + "\n")


# Global metrics instance (shared across NetworkBridge)
_global_metrics: NetworkMetrics = NetworkMetrics()


def get_global_metrics() -> NetworkMetrics:
    """Access the global metrics instance."""
    return _global_metrics


def reset_metrics():
    """Reset metrics for new battle."""
    global _global_metrics
    _global_metrics = NetworkMetrics()
