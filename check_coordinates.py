#!/usr/bin/env python3
"""
Check Z coordinates from Starter file to verify BC setup.
Analyzes initial positions of Punch, Die, and Material nodes.
"""

import re

def analyze_starter_file(filepath):
    """Parse starter file to get initial node positions and part assignments."""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    nodes = {}  # {node_id: (x, y, z)}
    parts = {}  # {part_id: {'name': name, 'elements': []}}
    elements = {}  # {elem_id: [node_ids]}
    punch_nodes = set()
    die_nodes = set()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Parse nodes
        if line == '/NODE':
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('/'):
                parts_data = lines[i].split()
                if len(parts_data) >= 4:
                    try:
                        nid = int(parts_data[0])
                        x = float(parts_data[1])
                        y = float(parts_data[2])
                        z = float(parts_data[3])
                        nodes[nid] = (x, y, z)
                    except:
                        pass
                i += 1
            continue
        
        # Parse parts
        if line.startswith('/PART/'):
            pid = int(line.split('/')[-1])
            i += 1
            name = lines[i].strip() if i < len(lines) else ''
            parts[pid] = {'name': name, 'elements': []}
            i += 1
            continue
        
        # Parse elements (TETRA4)
        if line.startswith('/TETRA4/'):
            pid = int(line.split('/')[-1])
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('/'):
                parts_data = lines[i].split()
                if len(parts_data) >= 5:
                    try:
                        eid = int(parts_data[0])
                        elem_nodes = [int(p) for p in parts_data[1:5]]
                        elements[eid] = elem_nodes
                        if pid in parts:
                            parts[pid]['elements'].append(eid)
                    except:
                        pass
                i += 1
            continue
        
        # Parse punch node group
        if '/GRNOD/NODE/100' in line:
            i += 2  # Skip name
            while i < len(lines) and not lines[i].strip().startswith('/'):
                for nid_str in lines[i].split():
                    try:
                        punch_nodes.add(int(nid_str))
                    except:
                        pass
                i += 1
            continue
        
        # Parse die node group
        if '/GRNOD/NODE/200' in line:
            i += 2  # Skip name
            while i < len(lines) and not lines[i].strip().startswith('/'):
                for nid_str in lines[i].split():
                    try:
                        die_nodes.add(int(nid_str))
                    except:
                        pass
                i += 1
            continue
        
        i += 1
    
    return nodes, parts, elements, punch_nodes, die_nodes


def main():
    starter_file = r"C:\Users\mhn15\dynamic_20251218\Punch_Die_Shearing_v3_0000.rad"
    
    print("="*60)
    print("OpenRadioss Model Coordinate Analysis")
    print("="*60)
    
    nodes, parts, elements, punch_nodes, die_nodes = analyze_starter_file(starter_file)
    
    print(f"\nTotal nodes: {len(nodes)}")
    print(f"Total elements: {len(elements)}")
    print(f"Parts: {len(parts)}")
    
    for pid, pdata in parts.items():
        print(f"  Part {pid}: {pdata['name']} ({len(pdata['elements'])} elements)")
    
    print(f"\nPunch nodes (GRNOD 100): {len(punch_nodes)}")
    print(f"Die nodes (GRNOD 200): {len(die_nodes)}")
    
    # Get Z coordinates for each part
    print("\n" + "="*60)
    print("INITIAL Z COORDINATES (in meters)")
    print("="*60)
    
    for pid, pdata in parts.items():
        part_nodes = set()
        for eid in pdata['elements']:
            if eid in elements:
                for nid in elements[eid]:
                    part_nodes.add(nid)
        
        if part_nodes:
            z_coords = [nodes[nid][2] for nid in part_nodes if nid in nodes]
            if z_coords:
                print(f"\nPart {pid} ({pdata['name']}):")
                print(f"  Nodes: {len(part_nodes)}")
                print(f"  Z min: {min(z_coords)*1000:.3f} mm")
                print(f"  Z max: {max(z_coords)*1000:.3f} mm")
                print(f"  Z avg: {sum(z_coords)/len(z_coords)*1000:.3f} mm")
    
    # Punch nodes
    if punch_nodes:
        z_coords = [nodes[nid][2] for nid in punch_nodes if nid in nodes]
        if z_coords:
            print(f"\nPUNCH NODES (GRNOD 100 - velocity applied):")
            print(f"  Count: {len(punch_nodes)}")
            print(f"  Z min: {min(z_coords)*1000:.3f} mm")
            print(f"  Z max: {max(z_coords)*1000:.3f} mm")
            print(f"  Z avg: {sum(z_coords)/len(z_coords)*1000:.3f} mm")
    
    # Die nodes
    if die_nodes:
        z_coords = [nodes[nid][2] for nid in die_nodes if nid in nodes]
        if z_coords:
            print(f"\nDIE NODES (GRNOD 200 - fixed):")
            print(f"  Count: {len(die_nodes)}")
            print(f"  Z min: {min(z_coords)*1000:.3f} mm")
            print(f"  Z max: {max(z_coords)*1000:.3f} mm")
            print(f"  Z avg: {sum(z_coords)/len(z_coords)*1000:.3f} mm")
    
    print("\n" + "="*60)
    print("EXPECTED BEHAVIOR:")
    print("  - Punch (Part 1): Should move DOWN (Z decreasing)")
    print("  - Material (Part 2): Should deform")
    print("  - Die (Part 3): Should remain FIXED")
    print("="*60)


if __name__ == "__main__":
    main()
