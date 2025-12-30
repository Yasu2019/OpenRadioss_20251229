import sys

def rad_to_vtk(rad_file, vtk_file):
    print(f"Converting {rad_file} to {vtk_file}...")
    
    nodes = {}
    hex20_elems = []
    
    # Read RAD file with explicit encoding
    try:
        with open(rad_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(rad_file, 'r', encoding='cp932') as f: # Fallback
            lines = f.readlines()
    
    i = 0
    current_section = None
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("/"):
            if line.startswith("/NODE") and not line.startswith("/NODE/"):
                current_section = "NODE"
                i += 1
                continue
            elif line.startswith("/BRIC20/"):
                try:
                    # Format: /BRIC20/EID
                    parts = line.split('/')
                    
                    i += 1
                    # Read line 1
                    l = lines[i].rstrip()
                    # Skip empty/comments
                    while i < len(lines) and (not l or l.startswith("#")):
                         i+=1
                         if i < len(lines): l = lines[i].rstrip()
                         else: l = None
                    
                    if not l: continue

                    node_ids = []
                    # Read n1-n8 from line 1 (starting col 10)
                    for col in range(10, 90, 10):
                        if col+10 <= len(l):
                            s = l[col:col+10].strip()
                            if s: 
                                try:
                                    node_ids.append(int(s))
                                except: pass
                    
                    # Read line 2 for n9-n20
                    i += 1
                    if i < len(lines):
                        l2 = lines[i].rstrip()
                        for col in range(20, 140, 10):
                             if col+10 <= len(l2):
                                s = l2[col:col+10].strip()
                                if s: 
                                    try:
                                        node_ids.append(int(s))
                                    except: pass
                    
                    if len(node_ids) == 20:
                        hex20_elems.append(node_ids)
                except:
                    pass
                continue
            elif line.startswith("/BRIC20") and not line.startswith("/BRIC20/"):
                current_section = "BRIC20"
                i += 1
                continue
            else:
                current_section = None
        
        if current_section == "NODE":
            try:
                # Format: ID X Y Z (fixed width or space separated)
                # Fixed width splitting is safer
                l = lines[i].rstrip() # get raw line
                if len(l) > 10:
                    nid = int(l[0:10])
                    x = float(l[10:30])
                    y = float(l[30:50])
                    z = float(l[50:70])
                    nodes[nid] = [x,y,z]
            except Exception as e:
                pass
                
        i += 1
        
    print(f"Read {len(nodes)} nodes and {len(hex20_elems)} HEX20 elements.")

    # Write VTK (Unstructured Grid)
    with open(vtk_file, 'w') as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("OpenRadioss Model\n")
        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n")
        
        # Nodes
        sorted_nids = sorted(nodes.keys())
        node_map = {nid: idx for idx, nid in enumerate(sorted_nids)} 
        
        f.write(f"POINTS {len(nodes)} float\n")
        for nid in sorted_nids:
            x, y, z = nodes[nid]
            f.write(f"{x} {y} {z}\n")
            
        # Cells
        total_size = len(hex20_elems) * (20 + 1)
        f.write(f"CELLS {len(hex20_elems)} {total_size}\n")
        
        for nids in hex20_elems:
            mapped_ids = [node_map[n] for n in nids if n in node_map]
            if len(mapped_ids) == 20:
                f.write(f"20 {' '.join(map(str, mapped_ids))}\n")
            else:
                pass # incomplete element
                
        f.write(f"CELL_TYPES {len(hex20_elems)}\n")
        for _ in hex20_elems:
            f.write("25\n") # 25 = VTK_QUADRATIC_HEXAHEDRON

    print("VTK generation complete.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python rad2vtk.py input.rad output.vtk")
    else:
        rad_to_vtk(sys.argv[1], sys.argv[2])
