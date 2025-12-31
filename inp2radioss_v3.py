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


def extract_surface_faces(all_elements, part_element_ids, nodes_coords):
    """
    Extract external faces of TETRA4 elements for a given part.
    Ensures correct normal direction (pointing outward).
    """
    # Count face occurrences
    face_counts = {}  # {tuple(sorted_nodes): count}
    face_to_elem = {} # {tuple(sorted_nodes): elem_id}
    
    # TETRA4 faces (node indices 1-based to 0-based: 0,1,2,3)
    # Faces defined by node indices in element connectivity
    # Face 1: n1, n2, n3 (opposite to n4)
    # Face 2: n1, n4, n2 (opposite to n3)
    # Face 3: n2, n4, n3 (opposite to n1)
    # Face 4: n3, n4, n1 (opposite to n2)
    # Correct winding for outward normal is counter-clockwise looking from outside
    
    tetra_faces_idx = [
        [0, 2, 1], # n1, n3, n2 - Check winding later
        [0, 1, 3], # n1, n2, n4
        [1, 2, 3], # n2, n3, n4
        [2, 0, 3]  # n3, n1, n4
    ]
    
    for eid in part_element_ids:
        if eid not in all_elements:
            continue
        ns = all_elements[eid] # [n1, n2, n3, n4]
        
        # Check all 4 faces
        faces = [
            tuple(sorted([ns[0], ns[2], ns[1]])),
            tuple(sorted([ns[0], ns[1], ns[3]])),
            tuple(sorted([ns[1], ns[2], ns[3]])),
            tuple(sorted([ns[2], ns[0], ns[3]]))
        ]
        
        for face in faces:
            if face in face_counts:
                face_counts[face] += 1
            else:
                face_counts[face] = 1
                face_to_elem[face] = eid

    # Identify external faces (count == 1)
    external_faces = []
    
    for face_key, count in face_counts.items():
        if count == 1:
            # Determine correct node order for outward normal
            eid = face_to_elem[face_key]
            ns = all_elements[eid]
            
            # Identify which nodes constitute the face
            # And which node is the 'opposite' node (internal node)
            face_set = set(face_key)
            all_set = set(ns)
            opp_node_list = list(all_set - face_set)
            
            if not opp_node_list:
                continue # Should not happen for valid tet
            
            opp_node = opp_node_list[0]
            
            # Get coordinates
            p1 = nodes_coords[face_key[0]]
            p2 = nodes_coords[face_key[1]]
            p3 = nodes_coords[face_key[2]]
            p_opp = nodes_coords[opp_node]
            
            # Vector calculation for normal
            # v1 = p2 - p1, v2 = p3 - p1
            v1 = (p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2])
            v2 = (p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2])
            
            # Normal = v1 x v2
            nx = v1[1]*v2[2] - v1[2]*v2[1]
            ny = v1[2]*v2[0] - v1[0]*v2[2]
            nz = v1[0]*v2[1] - v1[1]*v2[0]
            
            # Vector to opposite node: v_opp = p_opp - p1
            vx_opp = p_opp[0] - p1[0]
            vy_opp = p_opp[1] - p1[1]
            vz_opp = p_opp[2] - p1[2]
            
            # Dot product
            dot = nx*vx_opp + ny*vy_opp + nz*vz_opp
            
            # If dot > 0, normal points TOWARDS opposite node (Internal).
            # We want normal pointing OUTWARD (away from opposite node).
            # So if dot > 0, flip winding (swap p2 and p3).
            
            if dot > 0:
                final_face = [face_key[0], face_key[2], face_key[1]]
            else:
                final_face = [face_key[0], face_key[1], face_key[2]]
                
                
            external_faces.append(final_face)
            
    # Validate faces
    valid_faces = []
    for face in external_faces:
        if 0 in face:
            print(f"WARNING: Face with node 0 detected and removed: {face}")
        else:
            valid_faces.append(face)
            
    return valid_faces

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
    
    # Extract surfaces for contact
    print("  Extracting surface faces...")
    punch_faces = extract_surface_faces(elements, parts.get(1, {}).get('elements', []), nodes)
    material_faces = extract_surface_faces(elements, parts.get(2, {}).get('elements', []), nodes)
    die_faces = extract_surface_faces(elements, parts.get(3, {}).get('elements', []), nodes)
    print(f"  Surface faces extracted: Punch={len(punch_faces)}, Material={len(material_faces)}, Die={len(die_faces)}")
    
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
        
        # Surface definitions using /SURF/SEG (explicit segments for solid contact)
        
        # Surface for Punch (Extracted faces)
        if punch_faces:
            f.write("/SURF/SEG/300\n")
            f.write("Punch_Surface\n")
            for face in punch_faces:
                f.write(f"{face[0]:10d}{face[1]:10d}{face[2]:10d}{0:10d}\n")

        # Surface for Material (Extracted faces)
        if material_faces:
            f.write("/SURF/SEG/400\n")
            f.write("Material_Surface\n")
            for face in material_faces:
                f.write(f"{face[0]:10d}{face[1]:10d}{face[2]:10d}{0:10d}\n")

        # Surface for Die (Extracted faces)
        if die_faces:
            f.write("/SURF/SEG/500\n")
            f.write("Die_Surface\n")
            for face in die_faces:
                f.write(f"{face[0]:10d}{face[1]:10d}{face[2]:10d}{0:10d}\n")
        
        # Contact 1: Punch-Material (Surface 400 slave, Surface 300 master)
        if punch_faces and material_faces:
            f.write("/INTER/TYPE7/1\n")
            f.write("Punch_Material_Contact\n")
            f.write("#   Slav_id    Mast_id       Istf       Ithe       Igap       Ibag       Idel      Icurv\n")
            f.write(f"{400:10d}{300:10d}{4:10d}{0:10d}{2:10d}{0:10d}{1:10d}{0:10d}\n")
            f.write("#               Fric            Gap_min            Gapmax            Tstart             Tstop\n")
            f.write(f"{0.10:20.5f}{0.0001:20.5f}{1.0:20.5f}{0.0:20.5f}{1E30:20.5E}\n")
            f.write("#              Stfac            Fpenmax               I_BC             Iform\n")
            f.write(f"{100.0:20.5f}{0.0:20.5f}{0:10d}{0:10d}\n")
        
        # Contact 2: Die-Material (Surface 400 slave, Surface 500 master)
        if die_faces and material_faces:
            f.write("/INTER/TYPE7/2\n")
            f.write("Die_Material_Contact\n")
            f.write("#   Slav_id    Mast_id       Istf       Ithe       Igap       Ibag       Idel      Icurv\n")
            f.write(f"{400:10d}{500:10d}{4:10d}{0:10d}{2:10d}{0:10d}{1:10d}{0:10d}\n")
            f.write("#               Fric            Gap_min            Gapmax            Tstart             Tstop\n")
            f.write(f"{0.10:20.5f}{0.0001:20.5f}{1.0:20.5f}{0.0:20.5f}{1E30:20.5E}\n")
            f.write("#              Stfac            Fpenmax               I_BC             Iform\n")
            f.write(f"{100.0:20.5f}{0.0:20.5f}{0:10d}{0:10d}\n")
        
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
    base_name = "Punch_Die_Shearing_v4"
    starter_path = os.path.join(output_dir, f"{base_name}_0000.rad")
    engine_path = os.path.join(output_dir, f"{base_name}_0001.rad")
    
    print(f"\n{'='*60}")
    print("Calculix to OpenRadioss Converter V3 (with Contact V4)")
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
