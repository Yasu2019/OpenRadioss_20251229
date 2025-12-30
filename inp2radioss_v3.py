#!/usr/bin/env python3
"""
Calculix INP to OpenRadioss Converter for Shearing Simulation - V3
- Fixed part identification based on user's model structure:
  - Solid_part-1 (Z: 1.1-2.1) → PUNCH (moves down)
  - Solid_part-5, Solid_part-6 (Z: 0-1) → MATERIAL (merged, one fine mesh for shear zone)
  - Solid_part-4 (Z: -1.1 to -0.1) → DIE (fixed)
"""

import re
import os
from datetime import datetime

def parse_inp_file(inp_path):
    """Parse Calculix INP file."""
    print(f"Parsing: {inp_path}")
    
    nodes = {}
    elements = {}
    elset_elements = {}  # Elements directly from *ELEMENT cards
    
    with open(inp_path, 'r') as f:
        lines = f.readlines()
    
    # Parse nodes
    in_node = False
    for line in lines:
        line_s = line.strip()
        if line_s.upper().startswith('*NODE') and 'NSET' not in line_s.upper() and 'FILE' not in line_s.upper():
            in_node = True
            continue
        if line_s.startswith('*') and not line_s.startswith('**'):
            in_node = False
        if in_node and line_s and not line_s.startswith('*'):
            parts = line_s.replace(' ', '').split(',')
            if len(parts) >= 4:
                try:
                    nid = int(parts[0])
                    x = float(parts[1])
                    y = float(parts[2])
                    z = float(parts[3])
                    nodes[nid] = (x, y, z)
                except:
                    pass
    
    # Parse elements
    current_elset = None
    for line in lines:
        line_s = line.strip()
        if line_s.upper().startswith('*ELEMENT'):
            match = re.search(r'ELSET=([^,\s]+)', line_s, re.IGNORECASE)
            if match:
                current_elset = match.group(1)
                if current_elset not in elset_elements:
                    elset_elements[current_elset] = []
        elif line_s.startswith('*') and not line_s.startswith('**'):
            current_elset = None
        elif current_elset and line_s and not line_s.startswith('*'):
            parts = line_s.replace(' ', '').split(',')
            if len(parts) >= 5:
                try:
                    elem_id = int(parts[0])
                    elem_nodes = [int(p) for p in parts[1:5]]
                    elements[elem_id] = elem_nodes
                    elset_elements[current_elset].append(elem_id)
                except:
                    pass
    
    print(f"  Nodes: {len(nodes)}")
    print(f"  Elements: {len(elements)}")
    print(f"  Element Sets: {list(elset_elements.keys())}")
    
    return nodes, elements, elset_elements


def write_starter_file(output_path, nodes, elements, elset_elements):
    """Write OpenRadioss Starter file with correct part assignments."""
    print(f"Writing Starter: {output_path}")
    
    # Define parts based on user's model structure
    # Solid_part-1 → PUNCH
    # Solid_part-5, Solid_part-6 → MATERIAL (merged)
    # Solid_part-4 → DIE
    
    parts = {}
    
    # PUNCH - Part 1
    if 'Solid_part-1' in elset_elements:
        parts[1] = {
            'name': 'Punch',
            'role': 'PUNCH',
            'elements': elset_elements['Solid_part-1'],
            'mat_id': 1,  # Steel
            'prop_id': 1
        }
    
    # MATERIAL - Part 2 (merged from Solid_part-5 and Solid_part-6)
    material_elements = []
    if 'Solid_part-5' in elset_elements:
        material_elements.extend(elset_elements['Solid_part-5'])
    if 'Solid_part-6' in elset_elements:
        material_elements.extend(elset_elements['Solid_part-6'])
    if material_elements:
        parts[2] = {
            'name': 'Material',
            'role': 'MATERIAL',
            'elements': material_elements,
            'mat_id': 2,  # Aluminum with failure
            'prop_id': 2
        }
    
    # DIE - Part 3
    if 'Solid_part-4' in elset_elements:
        parts[3] = {
            'name': 'Die',
            'role': 'DIE',
            'elements': elset_elements['Solid_part-4'],
            'mat_id': 1,  # Steel
            'prop_id': 1
        }
    
    # Get nodes for each part
    punch_nodes = set()
    die_nodes = set()
    material_nodes = set()
    
    for pid, pdata in parts.items():
        for eid in pdata['elements']:
            if eid in elements:
                for nid in elements[eid]:
                    if pdata['role'] == 'PUNCH':
                        punch_nodes.add(nid)
                    elif pdata['role'] == 'DIE':
                        die_nodes.add(nid)
                    elif pdata['role'] == 'MATERIAL':
                        material_nodes.add(nid)
    
    punch_nodes = sorted(punch_nodes)
    die_nodes = sorted(die_nodes)
    material_nodes = sorted(material_nodes)
    
    print(f"  Punch: {len(parts.get(1, {}).get('elements', []))} elements, {len(punch_nodes)} nodes")
    print(f"  Material: {len(parts.get(2, {}).get('elements', []))} elements, {len(material_nodes)} nodes")
    print(f"  Die: {len(parts.get(3, {}).get('elements', []))} elements, {len(die_nodes)} nodes")
    
    with open(output_path, 'w') as f:
        # Header
        f.write("#RADIOSS STARTER\n")
        f.write("/BEGIN\n")
        f.write("Punch_Die_Shearing\n")
        f.write("      2022         0\n")
        f.write("                  kg                   m                   s\n")
        f.write("                  kg                   m                   s\n")
        
        f.write("/TITLE\n")
        f.write("Punch Die Shearing - Correct BC V3\n")
        
        # Nodes - convert mm to m
        f.write("/NODE\n")
        for nid in sorted(nodes.keys()):
            x, y, z = nodes[nid]
            x_m = x / 1000.0
            y_m = y / 1000.0
            z_m = z / 1000.0
            f.write(f"{nid:10d}{x_m:20.12E}{y_m:20.12E}{z_m:20.12E}\n")
        
        # Material 1: S185 Steel (LAW1 - Elastic for Punch/Die)
        f.write("/MAT/LAW1/1\n")
        f.write("S185_Steel\n")
        f.write("#              RHO_I\n")
        f.write("           7800.0\n")
        f.write("#                  E                  NU\n")
        f.write("          2.1E+11               0.28\n")
        
        # Material 2: 1060 Aluminum (LAW2 - Plastic with failure)
        f.write("/MAT/LAW2/2\n")
        f.write("1060_Alloy_Plastic\n")
        f.write("#              RHO_I\n")
        f.write("           2700.0\n")
        f.write("#                  E                  NU\n")
        f.write("          6.9E+10               0.33\n")
        f.write("#                  a                   b                   n           EPS_p_max               c\n")
        f.write("          1.1E+08           1.5E+08                0.20                 0.0                0.0\n")
        
        # Failure criterion for material
        f.write("/FAIL/BIQUAD/1\n")
        f.write("#  Ifail_sh   Ifail_so\n")
        f.write(f"{1:10d}{1:10d}\n")
        f.write("#          Eps_p_max           Eps_t_max           Eps_m_max               d_max\n")
        f.write(f"{0.15:20.5f}{0.20:20.5f}{0.30:20.5f}{0.0:20.5f}\n")
        f.write("#     Dadv      Nmax\n")
        f.write(f"{1:10d}{1:10d}\n")
        
        # Properties
        f.write("/PROP/SOLID/1\n")
        f.write("#   Isolid    Ismstr                               Dn                Qa                Hm\n")
        f.write(f"{14:10d}{4:10d}{0.0:20.5f}{0.0:20.5f}{0.5:20.5f}\n")
        
        f.write("/PROP/SOLID/2\n")
        f.write("#   Isolid    Ismstr                               Dn                Qa                Hm\n")
        f.write(f"{14:10d}{4:10d}{0.0:20.5f}{0.0:20.5f}{1.0:20.5f}\n")
        
        # Parts
        for pid, pdata in parts.items():
            f.write(f"/PART/{pid}\n")
            f.write(f"{pdata['name']}_{pdata['role']}\n")
            f.write(f"#    Prop_ID     Mat_ID\n")
            f.write(f"{pdata['prop_id']:10d}{pdata['mat_id']:10d}\n")
        
        # Elements
        for pid, pdata in parts.items():
            f.write(f"/TETRA4/{pid}\n")
            for eid in pdata['elements']:
                if eid in elements:
                    ns = elements[eid]
                    f.write(f"{eid:10d}{ns[0]:10d}{ns[1]:10d}{ns[2]:10d}{ns[3]:10d}\n")
        
        # Node groups
        # PUNCH nodes
        if punch_nodes:
            f.write("/GRNOD/NODE/100\n")
            f.write("Punch_Nodes\n")
            for i, nid in enumerate(punch_nodes):
                if (i + 1) % 10 == 0 or i == len(punch_nodes) - 1:
                    f.write(f"{nid:10d}\n")
                else:
                    f.write(f"{nid:10d}")
        
        # DIE nodes
        if die_nodes:
            f.write("/GRNOD/NODE/200\n")
            f.write("Die_Nodes\n")
            for i, nid in enumerate(die_nodes):
                if (i + 1) % 10 == 0 or i == len(die_nodes) - 1:
                    f.write(f"{nid:10d}\n")
                else:
                    f.write(f"{nid:10d}")
        
        # Boundary conditions - Fix DIE completely
        if die_nodes:
            f.write("/BCS/100\n")
            f.write("Die_Fixed\n")
            f.write("#  Tra_rot       Skew_ID   Gnod_ID\n")
            f.write(f"{111:10d}{0:10d}{200:10d}\n")
        
        # Velocity function with ramp
        f.write("/FUNCT/1\n")
        f.write("Velocity_Ramp\n")
        f.write("#                  X                   Y\n")
        f.write(f"{0.0:20.5f}{0.0:20.5f}\n")
        f.write(f"{0.001:20.5f}{-0.333:20.5f}\n")  # Ramp up over 1ms
        f.write(f"{0.05:20.5f}{-0.333:20.5f}\n")   # Constant velocity (333 mm/s = 0.333 m/s)
        
        # Imposed velocity on PUNCH (Z direction, negative = downward)
        if punch_nodes:
            f.write("/IMPVEL/1\n")
            f.write("Punch_Velocity\n")
            f.write("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe\n")
            f.write(f"{1:10d}{'Z':>10s}{0:10d}{0:10d}{100:10d}{0:10d}{0:10d}\n")
            f.write("#             Ascale_x            Fscale_y            Tstart              Tstop\n")
            f.write(f"{1.0:20.5f}{1.0:20.5f}{0.0:20.5f}{1E30:20.5E}\n")
        
        # NOTE: Contact disabled temporarily for testing basic BC
        # TYPE7 with /SURF/PART is not compatible with TETRA4 solid elements
        # For solid element contact, use /INTER/TYPE25 instead
        # TODO: Implement TYPE25 contact after verifying basic BC behavior
        
        # Mass scaling
        f.write("/DT/NODA/CST\n")
        f.write("#               Tmin            Tscale\n")
        f.write(f"{5.0E-08:20.5E}{0.9:20.5f}\n")
        
        f.write("/END\n")
    
    print(f"  Starter file written successfully")


def write_engine_file(output_path):
    """Write OpenRadioss Engine file."""
    print(f"Writing Engine: {output_path}")
    
    with open(output_path, 'w') as f:
        f.write("/RUN/Punch_Die_Shearing/1\n")
        f.write(f"{0.020:20.10f}\n")
        
        f.write("/ANIM/DT\n")
        f.write(f"{0.0:20.10f}{5.0E-04:20.10E}\n")
        
        f.write("/ANIM/ELEM/EPSP\n")
        f.write("/ANIM/ELEM/VONM\n")
        f.write("/ANIM/ELEM/ENER\n")
        f.write("/ANIM/VECT/DISP\n")
        f.write("/ANIM/VECT/VEL\n")
        
        f.write("/END\n")
    
    print("  Engine file written: 20ms simulation, 0.5ms animation interval")


def main():
    inp_path = r"C:\Users\mhn15\dynamic_20251218\Rev01_Punch_Die_1Piece_Material_20251229.inp"
    
    output_dir = r"C:\Users\mhn15\dynamic_20251218"
    base_name = "Punch_Die_Shearing_v3"
    starter_path = os.path.join(output_dir, f"{base_name}_0000.rad")
    engine_path = os.path.join(output_dir, f"{base_name}_0001.rad")
    
    print(f"\n{'='*60}")
    print("Calculix to OpenRadioss Converter V3")
    print("Model: Punch (1 part) + Material (2 merged) + Die (1 part)")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    nodes, elements, elset_elements = parse_inp_file(inp_path)
    
    write_starter_file(starter_path, nodes, elements, elset_elements)
    write_engine_file(engine_path)
    
    print(f"\n{'='*60}")
    print("Conversion complete!")
    print(f"Starter: {starter_path}")
    print(f"Engine:  {engine_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
