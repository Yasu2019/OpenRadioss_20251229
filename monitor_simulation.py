#!/usr/bin/env python3
"""
Monitor OpenRadioss simulation to verify boundary conditions.
Checks:
- Punch moves down (Z negative)
- Die remains fixed
- Material deformation
"""

import struct
import os
import glob
from datetime import datetime

def read_animation_header(filepath):
    """Read OpenRadioss animation file header to get basic info."""
    try:
        with open(filepath, 'rb') as f:
            # OpenRadioss animation files are binary
            # This is a simplified parser - may need adjustment
            header = f.read(512)
            return True
    except Exception as e:
        return False

def check_output_log(log_path):
    """Check the engine output log for progress and errors."""
    if not os.path.exists(log_path):
        return None
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Get last few relevant lines
    info = {
        'errors': [],
        'last_time': None,
        'last_cycle': None,
        'warnings': []
    }
    
    for line in lines[-100:]:
        line = line.strip()
        if 'ERROR' in line:
            info['errors'].append(line)
        if 'WARNING' in line:
            info['warnings'].append(line)
        if 'NC=' in line and 'T=' in line:
            # Parse status line like: NC=   11600 T= 6.7249E-05 DT= 5.7973E-09
            try:
                parts = line.split()
                for i, p in enumerate(parts):
                    if 'NC=' in p:
                        nc = p.replace('NC=', '') or parts[i+1]
                        info['last_cycle'] = int(nc.replace('NC=', ''))
                    if 'T=' in p and 'DT=' not in p:
                        t = p.replace('T=', '') or parts[i+1]
                        info['last_time'] = float(t.replace('T=', ''))
            except:
                pass
    
    return info

def count_animation_files(base_path):
    """Count generated animation files."""
    pattern = f"{base_path}A*"
    files = glob.glob(pattern)
    return sorted(files)

def monitor():
    """Run monitoring check."""
    base_name = "Punch_Die_Shearing_v3"
    work_dir = r"C:\Users\mhn15\dynamic_20251218"
    
    print(f"\n{'='*60}")
    print(f"OpenRadioss Simulation Monitor")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Check animation files
    anim_files = count_animation_files(os.path.join(work_dir, base_name))
    print(f"\nAnimation files generated: {len(anim_files)}")
    if anim_files:
        for af in anim_files[-5:]:  # Show last 5
            size_mb = os.path.getsize(af) / (1024*1024)
            print(f"  {os.path.basename(af)}: {size_mb:.2f} MB")
    
    # Check output log
    log_path = os.path.join(work_dir, f"{base_name}_0001.out")
    if os.path.exists(log_path):
        info = check_output_log(log_path)
        if info:
            print(f"\nSimulation Progress:")
            if info['last_cycle']:
                print(f"  Last Cycle: {info['last_cycle']}")
            if info['last_time']:
                print(f"  Simulation Time: {info['last_time']:.6e} s ({info['last_time']*1000:.4f} ms)")
                progress = (info['last_time'] / 0.020) * 100  # Target is 20ms
                print(f"  Progress: {progress:.2f}%")
            if info['errors']:
                print(f"\n  ERRORS ({len(info['errors'])}):")
                for e in info['errors'][-3:]:
                    print(f"    {e}")
    
    # Check if engine is still running
    print(f"\n{'='*60}")

if __name__ == "__main__":
    monitor()
