import sys
import re

def rad_to_vtk(rad_file, vtk_file):
    print(f"Converting {rad_file} to {vtk_file}...")
    
    nodes = {}
    hex20_elems = []
    
    # Read RAD file with explicit encoding handling
    lines = []
    try:
        with open(rad_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print("UTF-8 decode failed, trying cp932/shift_jis...")
        try:
            with open(rad_file, 'r', encoding='cp932') as f:
                lines = f.readlines()
        except:
             print("Fallback to latin-1...")
             with open(rad_file, 'r', encoding='latin-1') as f:
                lines = f.readlines()

    # Pre-process lines to remove comments and strip whitespace
    clean_lines = []
    for line in lines:
        l = line.strip()
        if not l or l.startswith("#"):
            continue
        clean_lines.append(l)
        
    # --- PHASE 1: Parse NODES ---
    print("Parsing Nodes...")
    i = 0
    while i < len(clean_lines):
        line = clean_lines[i]
        if line.startswith("/NODE"):
            # Enter Node Block
            # Format usually: /NODE (header) then lines of ID X Y Z
            # Or /NODE/ID then X Y Z
            
            # Check if it is /NODE/ID
            if line.startswith("/NODE/"):
                # One node definition
                # /NODE/1
                # 0.0 0.0 0.0
                try:
                    parts = line.split('/')
                    if len(parts) > 2:
                        nid = int(parts[2])
                        i += 1
                        if i < len(clean_lines):
                            coords_line = clean_lines[i]
                            vals = coords_line.split()
                            if len(vals) >= 3:
                                nodes[nid] = [float(v) for v in vals[:3]]
                except: pass
            else:
                # Bulk definition /NODE
                i += 1
                while i < len(clean_lines):
                    line = clean_lines[i]
                    if line.startswith("/"): # New keyword
                        i -= 1 # Back step
                        break
                    
                    # Try parse ID X Y Z
                    # Could be fixed width or space separated
                    # Try space separated first
                    vals = line.split()
                    try:
                        if len(vals) >= 4:
                            nid = int(vals[0])
                            # Check if vals[0] looks like ID (integer)
                            nodes[nid] = [float(vals[1]), float(vals[2]), float(vals[3])]
                        elif len(line) > 30: # Try fixed width fall back
                             nid = int(line[0:10])
                             x = float(line[10:30])
                             y = float(line[30:50])
                             z = float(line[50:70])
                             nodes[nid] = [x,y,z]
                    except: pass
                    i += 1
        i += 1
        
    print(f"Parsed {len(nodes)} nodes.")

    # --- PHASE 2: Parse BRIC20 Elements ---
    print("Parsing BRIC20 Elements...")
    i = 0
    while i < len(clean_lines):
        line = clean_lines[i]
        if line.startswith("/BRIC20"):
            # Found an element definition
            # Can be /BRIC20 (bulk) or /BRIC20/ID (single)
            
            elem_tokens = []
            
            if line.startswith("/BRIC20/"):
                 # Single element mode
                 # /BRIC20/1
                 # PID n1 ... n20
                 # Collect all numbers from following lines until next keyword
                 i += 1
                 while i < len(clean_lines):
                     sub_line = clean_lines[i]
                     if sub_line.startswith("/"):
                         i -= 1
                         break
                     # Split line and add integers
                     # Fixed width splitting is safer for huge numbers sticking together
                     # But split() is usually robust enough for generated files
                     tokens = sub_line.split()
                     elem_tokens.extend(tokens)
                     i += 1
                     
                 # Now process tokens. 
                 # If PID was in header, we have 20 node tokens.
                 # If PID was in body, we have 21 tokens.
                 
                 try:
                     int_tokens = [int(t) for t in elem_tokens if t.replace('-','').isdigit()]
                     
                     if len(int_tokens) >= 21:
                         # PID = int_tokens[0]
                         nids = int_tokens[1:21] 
                         hex20_elems.append(nids)
                     elif len(int_tokens) == 20:
                         # PID presumably in header, just take 20 nodes
                         nids = int_tokens
                         hex20_elems.append(nids)
                 except: pass

            else:
                 # Bulk mode logic (if needed, but file seems to be single mode)
                 pass
                 
        i += 1

    print(f"Parsed {len(hex20_elems)} HEX20 elements.")

    # --- PHASE 3: Write VTK ---
    with open(vtk_file, 'w') as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("OpenRadioss Model converted\n")
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
        valid_elems = []
        for nids in hex20_elems:
            # Only keep elements where all nodes exist
            mapped = [node_map[n] for n in nids if n in node_map]
            if len(mapped) == 20:
                valid_elems.append(mapped)
                
        total_size = len(valid_elems) * (20 + 1)
        f.write(f"CELLS {len(valid_elems)} {total_size}\n")
        
        for mapped in valid_elems:
            f.write(f"20 {' '.join(map(str, mapped))}\n")
            
        f.write(f"CELL_TYPES {len(valid_elems)}\n")
        for _ in valid_elems:
            f.write("25\n") # 25 = VTK_QUADRATIC_HEXAHEDRON

    print(f"VTK generation complete. Written to {vtk_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python rad2vtk_robust.py input.rad output.vtk")
    else:
        rad_to_vtk(sys.argv[1], sys.argv[2])
