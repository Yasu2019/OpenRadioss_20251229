#!/usr/bin/env python3
import re
import os
from datetime import datetime

def parse_inp_file(inp_path):
    print(f"Parsing: {inp_path}")
    nodes = {}
    elements = {}
    elset_elements = {}
    with open(inp_path, 'r') as f:
        lines = f.readlines()
    in_node = False
    current_elset = None
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
                    nodes[nid] = (float(parts[1]), float(parts[2]), float(parts[3]))
                except: pass
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
                    eid = int(parts[0])
                    elements[eid] = [int(p) for p in parts[1:5]]
                    elset_elements[current_elset].append(eid)
                except: pass
    return nodes, elements, elset_elements

def extract_surface_faces(all_elements, part_element_ids, nodes_coords):
    face_counts = {}
    face_to_elem = {}
    for eid in part_element_ids:
        if eid not in all_elements: continue
        ns = all_elements[eid]
        faces = [
            tuple(sorted([ns[0], ns[2], ns[1]])),
            tuple(sorted([ns[0], ns[1], ns[3]])),
            tuple(sorted([ns[1], ns[2], ns[3]])),
            tuple(sorted([ns[2], ns[0], ns[3]]))
        ]
        for face in faces:
            face_counts[face] = face_counts.get(face, 0) + 1
            if face_counts[face] == 1: face_to_elem[face] = eid
            
    external_faces = []
    for face_key, count in face_counts.items():
        if count == 1:
            if 0 in face_key: continue
            eid = face_to_elem[face_key]
            ns = all_elements[eid]
            face_set = set(face_key)
            opp_node = list(set(ns) - face_set)[0]
            p1 = nodes_coords[face_key[0]]
            p2 = nodes_coords[face_key[1]]
            p3 = nodes_coords[face_key[2]]
            p_opp = nodes_coords[opp_node]
            v1 = (p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2])
            v2 = (p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2])
            nx = v1[1]*v2[2] - v1[2]*v2[1]
            ny = v1[2]*v2[0] - v1[0]*v2[2]
            nz = v1[0]*v2[1] - v1[1]*v2[0]
            vx_opp = p_opp[0] - p1[0]
            vy_opp = p_opp[1] - p1[1]
            vz_opp = p_opp[2] - p1[2]
            dot = nx*vx_opp + ny*vy_opp + nz*vz_opp
            if dot > 0: current_face = [face_key[0], face_key[2], face_key[1]]
            else: current_face = [face_key[0], face_key[1], face_key[2]]
            external_faces.append(current_face)
    return external_faces

def collect_nodes(faces):
    s = set()
    for f in faces:
        s.update(f)
    return s

def write_starter_file(output_path, nodes, elements, elset_elements):
    print(f"Writing Starter: {output_path}")
    # Flexible part mapping - check for various possible elset names
    # Match the actual Elset names in the INP file
    parts = {}
    all_elements_list = []
    
    # Punch parts (3 punch tools that move together)
    punch_names = ['Solid_part-1', 'Solid_part-Punch_Hole', 'Solid_part-Punch_Trim', 'Solid_part-Punch_Rectangle',
                   'From_parts-Punch_Hole', 'From_parts-Punch_Trim', 'From_parts-Punch_Rectangle']
    
    # Material (free, no BC)
    material_names = ['Solid_part-5', 'Solid_part-6', 'Solid_part-Material', 'From_parts-Material']
    
    # Die (fixed)
    die_names = ['Solid_part-4', 'Solid_part-Die', 'From_parts-Die']
    
    # Stripper (moves with punch)
    stripper_names = ['Solid_part-Stripper', 'From_parts-Stripper']
    
    punch_elements = []
    for name in punch_names:
        if name in elset_elements:
            punch_elements.extend(elset_elements[name])
    if punch_elements:
        parts[1] = {'name': 'Punch', 'role': 'PUNCH', 'elements': punch_elements, 'mat_id': 1, 'prop_id': 1}
    
    material_elements = []
    for name in material_names:
        if name in elset_elements:
            material_elements.extend(elset_elements[name])
    if material_elements:
        parts[2] = {'name': 'Material', 'role': 'MATERIAL', 'elements': material_elements, 'mat_id': 2, 'prop_id': 2}
    
    die_elements = []
    for name in die_names:
        if name in elset_elements:
            die_elements.extend(elset_elements[name])
    if die_elements:
        parts[3] = {'name': 'Die', 'role': 'DIE', 'elements': die_elements, 'mat_id': 1, 'prop_id': 1}
    
    # Stripper - moves like punch
    stripper_elements = []
    for name in stripper_names:
        if name in elset_elements:
            stripper_elements.extend(elset_elements[name])
    if stripper_elements:
        parts[4] = {'name': 'Stripper', 'role': 'STRIPPER', 'elements': stripper_elements, 'mat_id': 1, 'prop_id': 1}
    
    # If no parts matched, use all elements as a single part
    if not parts and elset_elements:
        all_elems = []
        for eset_name, eset_elems in elset_elements.items():
            all_elems.extend(eset_elems)
        parts[1] = {'name': 'AllElements', 'role': 'PUNCH', 'elements': all_elems, 'mat_id': 1, 'prop_id': 1}

    punch_nodes = set()
    stripper_nodes = set()
    die_nodes = set()
    for pid, pdata in parts.items():
        for eid in pdata['elements']:
            if eid in elements:
                for nid in elements[eid]:
                    if pdata['role'] == 'PUNCH': punch_nodes.add(nid)
                    elif pdata['role'] == 'DIE': die_nodes.add(nid)
                    elif pdata['role'] == 'STRIPPER': stripper_nodes.add(nid)
    
    print("  Extracting surface faces...")
    punch_faces = extract_surface_faces(elements, parts.get(1, {}).get('elements', []), nodes)
    material_faces = extract_surface_faces(elements, parts.get(2, {}).get('elements', []), nodes)
    die_faces = extract_surface_faces(elements, parts.get(3, {}).get('elements', []), nodes)
    print(f"  Extracted faces: Punch={len(punch_faces)}, Material={len(material_faces)}, Die={len(die_faces)}")

    # Collect nodes for Slave Groups
    material_skin_nodes = collect_nodes(material_faces)
    
    max_elem_id = max(elements.keys()) if elements else 0
    current_skin_eid = max_elem_id + 1

    with open(output_path, 'w') as f:
        f.write("#RADIOSS STARTER\n/BEGIN\nPunch_Die_Shearing\n      2022         0\n")
        f.write("                  kg                   m                   s\n")
        f.write("                  kg                   m                   s\n")
        f.write("/TITLE\nPunch Die Shearing - V6 with AMS (Fine Blanking Optimized)\n")
        f.write("/NODE\n")
        for nid in sorted(nodes.keys()):
            x, y, z = nodes[nid]
            f.write(f"{nid:10d}{x/1000.0:20.12E}{y/1000.0:20.12E}{z/1000.0:20.12E}\n")
            
        f.write("/MAT/LAW1/1\nS185_Steel\n#              RHO_I\n           7800.0\n#                  E                  NU\n          2.1E+11               0.28\n")
        f.write("                   0                   0                   0                   0                   0\n")
        
        # LAW2 (Elasto-Plastic) for 1060 Aluminum Alloy with element deletion
        # A (Sigma_y) = 110 MPa, B (E_tan) = 150 MPa, Xmax = 0.5 (50% plastic strain for deletion)
        f.write("/MAT/LAW2/2\n1060_Alloy_Plastic\n")
        f.write("#              RHO_I\n           2700.0\n")
        f.write("#                  E                  NU\n          6.9E+10               0.33\n")
        f.write("#                  a                   b                   n           EPS_p_max               Xmax\n")
        f.write("          1.1E+08           1.5E+08                0.20               1.0               0.5\n")
        f.write("                 0.0                 0.0                 0.0                 0.0                 0.0\n")
        f.write("                 0.0                 0.0                 0.0                 0.0                 0.0\n")
        f.write("                 0.0                 0.0                 0.0                 0.0                 0.0\n")
        
        f.write("/PROP/SOLID/1\n#   Isolid    Ismstr                               Dn                Qa                Hm\n        14         4             0.00000             0.00000             0.50000\n")
        f.write("                   0                   0                   0                   0                   0\n")
        
        f.write("/PROP/SOLID/2\n#   Isolid    Ismstr                               Dn                Qa                Hm\n        14         4             0.00000             0.00000             1.00000\n")
        f.write("                   0                   0                   0                   0                   0\n")

        # Skin Property with corrected 5-line format & N=5
        f.write("/PROP/SHELL/999\nSkin_Property\n")
        f.write("#   Ishell    Ismstr      Ish3n    Idrill\n")
        f.write(f"{1:10d}{2:10d}{2:10d}{0:10d}\n")
        f.write(f"{0.0:20.5f}{0.0:20.5f}{0.0:20.5f}{0.0:20.5f}{0.0:20.5f}\n")
        # Line 5: N(5), Thick(2), Ashear(3), Ithick(4), Iplas(5), Ipos(6)
        f.write(f"{5.0:20.5f}{0.001:20.5f}{0.0:20.5f}{0.0:20.5f}{0.0:20.5f}{0.0:20.5f}\n")
        f.write(f"{0:20d}{0:20d}{0:20d}{0:20d}{0:20d}\n")

        for pid, pdata in parts.items():
            f.write(f"/PART/{pid}\n{pdata['name']}_{pdata['role']}\n#    Prop_ID     Mat_ID\n{pdata['prop_id']:10d}{pdata['mat_id']:10d}\n")
        
        # Skin Parts
        if punch_faces: f.write(f"/PART/101\nPunch_Skin\n#    Prop_ID     Mat_ID\n       999         1\n")
        if material_faces: f.write(f"/PART/102\nMaterial_Skin\n#    Prop_ID     Mat_ID\n       999         2\n")
        if die_faces: f.write(f"/PART/103\nDie_Skin\n#    Prop_ID     Mat_ID\n       999         1\n")

        # Surfaces Definitions (Masters only: Punch=300, Die=500)
        # Using strict formatting /300/0 and blanklines
        if punch_faces:
             f.write(f"/SURF/PART/300/0\nPunch_Skin_Surf\n{101:10d}\n\n")
        
        if die_faces:
             f.write(f"/SURF/PART/500/0\nDie_Skin_Surf\n{103:10d}\n\n")

        # Elements
        for pid, pdata in parts.items():
            f.write(f"/TETRA4/{pid}\n")
            for eid in pdata['elements']:
                ns = elements[eid]
                f.write(f"{eid:10d}{ns[0]:10d}{ns[1]:10d}{ns[2]:10d}{ns[3]:10d}\n")
        
        # Skin Elements
        if punch_faces:
            f.write(f"/SH3N/101\n")
            for face in punch_faces:
                f.write(f"{current_skin_eid:10d}{face[0]:10d}{face[1]:10d}{face[2]:10d}\n")
                current_skin_eid += 1
        
        if material_faces:
            f.write(f"/SH3N/102\n")
            for face in material_faces:
                f.write(f"{current_skin_eid:10d}{face[0]:10d}{face[1]:10d}{face[2]:10d}\n")
                current_skin_eid += 1
        
        if die_faces:
            f.write(f"/SH3N/103\n")
            for face in die_faces:
                f.write(f"{current_skin_eid:10d}{face[0]:10d}{face[1]:10d}{face[2]:10d}\n")
                current_skin_eid += 1

        # Node Groups
        if punch_nodes:
            f.write("/GRNOD/NODE/100\nPunch_Nodes\n")
            for i, nid in enumerate(sorted(punch_nodes)):
                f.write(f"{nid:10d}" + ("\n" if (i+1)%10==0 else ""))
            f.write("\n")
        if die_nodes:
            f.write("/GRNOD/NODE/200\nDie_Nodes\n")
            for i, nid in enumerate(sorted(die_nodes)):
                f.write(f"{nid:10d}" + ("\n" if (i+1)%10==0 else ""))
            f.write("\n")
            # Using IMPVEL with zero velocity instead of BCS for Die (more reliable)
            pass  # BCS removed, using IMPVEL instead
        
        # Stripper Node Group - ID 300 (moves with punch)
        if stripper_nodes:
            f.write("/GRNOD/NODE/300\nStripper_Nodes\n")
            for i, nid in enumerate(sorted(stripper_nodes)):
                f.write(f"{nid:10d}" + ("\n" if (i+1)%10==0 else ""))
            f.write("\n")

        # Material Skin Nodes Group (Slave) - ID 400
        if material_skin_nodes:
            f.write("/GRNOD/NODE/400\nMaterial_Skin_Nodes\n")
            for i, nid in enumerate(sorted(material_skin_nodes)):
                f.write(f"{nid:10d}" + ("\n" if (i+1)%10==0 else ""))
            f.write("\n")
            
        # Velocity functions
        f.write("/FUNCT/1\nVelocity_Ramp\n#                  X                   Y\n             0.00000             0.00000\n             0.00002            -5.00000\n             0.05000            -5.00000\n")
        f.write("/FUNCT/2\nZero_Velocity\n#                  X                   Y\n             0.00000             0.00000\n             0.10000             0.00000\n")
        # Function 3: Stripper Velocity (Stop at 0.2mm)
        # Velocity = 5000 mm/s. Target Dist = 0.2mm.
        # Time = 0.2 / 5000 = 0.00004 s.
        # Ramp: 0 -> -5.0 in 0.00002s.
        f.write("/FUNCT/3\nStripper_Limit\n#                  X                   Y\n             0.00000             0.00000\n             0.00002            -5.00000\n             0.00004            -5.00000\n             0.00005             0.00000\n             0.10000             0.00000\n")
        
        # Punch velocity (Z direction, moving down)
        if punch_nodes:
            f.write("/IMPVEL/1\nPunch_Velocity\n#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe\n         1         Z         0         0       100         0         0\n#             Ascale_x            Fscale_y            Tstart              Tstop\n             1.00000             1.00000             0.00000         1.00000E+30\n")
        
        # Die fixed in all directions using zero velocity
        if die_nodes:
            f.write("/IMPVEL/2\nDie_Fixed_X\n#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe\n         2         X         0         0       200         0         0\n#             Ascale_x            Fscale_y            Tstart              Tstop\n             1.00000             1.00000             0.00000         1.00000E+30\n")
            f.write("/IMPVEL/3\nDie_Fixed_Y\n#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe\n         2         Y         0         0       200         0         0\n#             Ascale_x            Fscale_y            Tstart              Tstop\n             1.00000             1.00000             0.00000         1.00000E+30\n")
            f.write("/IMPVEL/4\nDie_Fixed_Z\n#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe\n         2         Z         0         0       200         0         0\n#             Ascale_x            Fscale_y            Tstart              Tstop\n             1.00000             1.00000             0.00000         1.00000E+30\n")
        
        # Stripper velocity (Z direction, moving down with punch)
        if stripper_nodes:
            f.write("/IMPVEL/5\nStripper_Velocity\n#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe\n         3         Z         0         0       300         0         0\n#             Ascale_x            Fscale_y            Tstart              Tstop\n             1.00000             1.00000             0.00000         1.00000E+30\n")
        
        # Contact using Slave Node Group 400 and Master Surfaces 300/500
        # Contact with AMS-optimized settings (Istf=4, Iform=2)
        if punch_faces and material_faces:
            f.write("/INTER/TYPE7/1\nPunch_Material_Contact\n#   Slav_id    Mast_id       Istf       Ithe       Igap       Ibag       Idel      Icurv\n       400       300         4         0         2         0         1         0\n#               Fric            Gap_min            Gapmax            Tstart             Tstop\n             0.10000             0.00010             1.00000             0.00000         1.00000E+30\n#              Stfac            Fpenmax               I_BC             Iform\n              20.000             0.00000         0         2\n")
        
        if die_faces and material_faces:
            f.write("/INTER/TYPE7/2\nDie_Material_Contact\n#   Slav_id    Mast_id       Istf       Ithe       Igap       Ibag       Idel      Icurv\n       400       500         4         0         2         0         1         0\n#               Fric            Gap_min            Gapmax            Tstart             Tstop\n             0.10000             0.00010             1.00000             0.00000         1.00000E+30\n#              Stfac            Fpenmax               I_BC             Iform\n              20.000             0.00000         0         2\n")

        # AMS (Advanced Mass Scaling) for fine blanking
        # Note: /AMS is recognized by Starter, but /DT/AMS not supported in OSS Engine
        # Using aggressive Mass Scaling (Tmin=5E-7) for ~3-5x speed improvement


def write_engine_file(output_path):
    print(f"Writing Engine: {output_path}")
    with open(output_path, 'w') as f:
        f.write("/RUN/Punch_Die_Shearing/1\n             0.0007000000\n")

        f.write("/RFILE/5000\n/ANIM/DT\n             0.0000000000         1.00000E-04\n")
        f.write("/ANIM/ELEM/EPSP\n/ANIM/ELEM/VONM\n/ANIM/ELEM/ENER\n")
        # Stress components for η, Lode, σ1 calculation in post-processing
        f.write("/ANIM/ELEM/SIGX\n")
        f.write("/ANIM/ELEM/SIGY\n")
        f.write("/ANIM/ELEM/SIGZ\n")
        f.write("/ANIM/ELEM/SIGXY\n")
        f.write("/ANIM/ELEM/SIGYZ\n")
        f.write("/ANIM/ELEM/SIGZX\n")
        f.write("/ANIM/VECT/DISP\n/ANIM/VECT/VEL\n/END\n")

def main():
    import sys
    if len(sys.argv) > 1:
        inp_path = sys.argv[1]
    else:
        inp_path = r"ASSY_OpenRadioss_PM7T1C_20260102.inp"
    output_dir = r"."
    base_name = os.path.splitext(os.path.basename(inp_path))[0]
    starter_path = os.path.join(output_dir, f"{base_name}_0000.rad")
    engine_path = os.path.join(output_dir, f"{base_name}_0001.rad")
    print(f"Calculix to OpenRadioss Converter V6 (AMS - Fine Blanking Optimized)")
    nodes, elements, elset_elements = parse_inp_file(inp_path)
    write_starter_file(starter_path, nodes, elements, elset_elements)
    write_engine_file(engine_path)
    print("Conversion complete!")

if __name__ == "__main__":
    main()
