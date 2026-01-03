#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Calculix/Abaqus INP to OpenRadioss Starter (.rad) Converter
Format based on actual working OpenRadioss file
"""

import sys
import os

def parse_inp_sections(inp_file):
    """Pass 1: Identify Node ownership based on Node Sets"""
    print("  Pass 1: Parsing Node Sets...")
    node_to_part = {}
    part_map_names = {
        'Node_Set-Material': 1,
        'Node_Set-Punch_Hole': 2,
        'Node_Set-Punch_Trim': 3,
        'Node_Set-Punch_Rectangle': 4,
        'Node_Set-Stripper': 5,
        'Node_Set-Die': 6
    }
    current_nset = None
    
    with open(inp_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('*Nset'):
                parts = line.split(',')
                current_nset = None
                for p in parts:
                    if 'nset=' in p.lower():
                        name = p.split('=')[1].strip()
                        if name in part_map_names:
                            current_nset = part_map_names[name]
                continue
            if line.startswith('*'):
                current_nset = None
                continue
            if current_nset is not None:
                try:
                    ids = [int(x) for x in line.split(',') if x.strip()]
                    for nid in ids:
                        node_to_part[nid] = current_nset
                except:
                    pass
    return node_to_part

def convert_inp_to_rad(inp_file):
    rad_file = os.path.splitext(inp_file)[0] + "_0000.rad"
    engine_file = os.path.splitext(inp_file)[0] + "_0001.rad"
    
    print(f"Converting {inp_file} (Original Format)...")
    node_part_map = parse_inp_sections(inp_file)
    
    print("  Pass 2: Processing Geometry...")
    nodes = []
    elements = []
    current_section = None
    
    # First pass - collect all data
    with open(inp_file, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            line = line.strip()
            if not line or line.startswith('**'): continue
            
            if line.startswith('*'):
                keyword = line.split(',')[0].lower()
                if keyword == '*node':
                    current_section = 'node'
                elif keyword == '*element':
                    current_section = 'element'
                    is_tetra = 'type=c3d4' in line.lower()
                    if not is_tetra: current_section = 'skip_element'
                else:
                    current_section = None
                continue
            
            if current_section == 'node':
                parts = line.split(',')
                if len(parts) >= 4:
                    nid = int(parts[0])
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    nodes.append((nid, x, y, z))
                    
            elif current_section == 'element':
                parts = line.split(',')
                if len(parts) >= 5:
                    eid = int(parts[0])
                    n = [int(x) for x in parts[1:5]]
                    pid = 1
                    if n[0] in node_part_map:
                        pid = node_part_map[n[0]]
                    elements.append((eid, pid, n))

    # Write output in original format
    with open(rad_file, 'w', encoding='utf-8', newline='\n') as f:
        # Header
        f.write("#RADIOSS STARTER\n")
        f.write("/BEGIN\n")
        f.write("ASSY_OpenRadioss_PM7T1C\n")  # Run name
        f.write("      2022         0\n")     # Ivers=2022, Irun=0 (NEW RUN)
        f.write("/TITLE\n")
        f.write("Punch Die Shearing Analysis\n")
        f.write("/UNIT/1\n")
        f.write("MASS   LENGTH   TIME\n")
        f.write("Mg      mm       s\n")
        
        # Nodes - /NODE/ID format with coords on next line
        for nid, x, y, z in nodes:
            f.write(f"/NODE/{nid}\n")
            f.write(f" {x:.8E} {y:.8E} {z:.8E}\n")
        
        # Materials - using simple ELASTIC for now to test format
        f.write("/MAT/PLAS_JOHNS/1/Tool_Steel\n")
        f.write(" 7.8000E-09\n")  # rho (Mg/mm^3)
        f.write(" 2.1000E+05 2.8000E-01\n")  # E, nu
        f.write(" 3.5500E+02 6.0000E+02 2.0000E-01 0.0000E+00 0.0000E+00\n")  # A,B,n
        f.write(" 0.0000E+00 0.0000E+00\n")  # C, EPS0
        f.write(" 0.0000E+00 0.0000E+00 0.0000E+00\n")  # ICC, Fcut, Emax
        
        f.write("/MAT/PLAS_JOHNS/2/Aluminum\n")
        f.write(" 2.7000E-09\n")  # rho (Mg/mm^3)
        f.write(" 6.9000E+04 3.3000E-01\n")  # E, nu
        f.write(" 2.8000E+01 8.5000E+01 2.0000E-01 0.0000E+00 0.0000E+00\n")
        f.write(" 0.0000E+00 0.0000E+00\n")
        f.write(" 0.0000E+00 0.0000E+00 0.0000E+00\n")
        
        # Properties
        f.write("/PROP/SOLID/1/Material_Prop\n")
        f.write("         0\n")
        f.write("         0         0         0         0         0\n")
        
        f.write("/PROP/SOLID/2/Tool_Prop\n")
        f.write("         0\n")
        f.write("         0         0         0         0         0\n")
        
        # Parts
        parts_info = {
            1: ("Material", 1, 2),
            2: ("Punch_Hole", 2, 1),
            3: ("Punch_Trim", 2, 1),
            4: ("Punch_Rectangle", 2, 1),
            5: ("Stripper", 2, 1),
            6: ("Die", 2, 1)
        }
        
        for pid, (name, prop_id, mat_id) in parts_info.items():
            f.write(f"/PART/{pid}/{name}\n")
            f.write(f"         {prop_id}         {mat_id}         0\n")
        
        # Elements - /TETRA4/ID/PID format
        for eid, pid, n in elements:
            f.write(f"/TETRA4/{eid}/{pid}\n")
            f.write(f"{n[0]:10d}{n[1]:10d}{n[2]:10d}{n[3]:10d}\n")
        
        # Boundary Conditions
        die_nodes = sorted([nid for nid, p in node_part_map.items() if p == 6])
        if die_nodes:
            f.write("/GRNOD/NODE/1/Die_Fixed\n")
            for i in range(0, len(die_nodes), 5): 
                chunk = die_nodes[i:i+5]
                line_str = "".join([f"{nid:10d}" for nid in chunk])
                f.write(line_str + "\n")
            
            f.write("/BCS/1/Fixed_Die\n")
            f.write("         1\n")  # Grnod_ID
            f.write("    111111         0         0         0\n")  # Trarot, etc.
        
        f.write("/END\n")

    # Engine
    with open(engine_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write("/RUN/ASSY_OpenRadioss_PM7T1C/1\n")
        f.write(" 1.0000E-04\n")  # End time
        f.write("/TFILE\n")
        f.write(" 4.0000E-06\n")
        f.write("/ANIM/DT\n")
        f.write(" 0.0000E+00 1.0000E-05\n")
        f.write("/ANIM/ELEM/EPSP\n")
        f.write("/ANIM/ELEM/VONM\n")
        f.write("/ANIM/VECT/VEL\n")
        f.write("/ANIM/VECT/CONT\n")
        f.write("/PRINT/-1\n")
        f.write("/STOP\n")
        f.write("/END\n")

    print(f"Done. Starter: {rad_file} ({len(elements)} elements, {len(nodes)} nodes)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert_inp_to_rad(sys.argv[1])
    else:
        print("Usage: python inp2radioss.py file.inp")
