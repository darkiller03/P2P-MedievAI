#!/usr/bin/env python3
from pathlib import Path

# Read the current file
path = Path(r'c:\Users\ilyas\Documents\P2P-MedievAI\connection.c')
text = path.read_text(encoding='utf-8')

# Find duplicate parse_relay_message (second occurrence) and remove everything up to handle_peer_line
lines = text.split('\n')
result = []
skip = False
skip_start = -1

for i, line in enumerate(lines):
    if i > 100 and 'static bool parse_relay_message(const char *line' in line and skip_start == -1:
        skip = True
        skip_start = i
        continue
    
    if skip:
        if 'static bool handle_peer_line(' in line:
            skip = False
        else:
            continue
    
    result.append(line)

# Write back
path.write_text('\n'.join(result), encoding='utf-8')
print(f'Cleaned: {len(lines)} -> {len(result)} lines, removed {skip_start} duplicate section')
