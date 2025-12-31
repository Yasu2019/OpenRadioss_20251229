#!/usr/bin/env python3
"""
Enhanced OpenRadioss Animation to VTK Converter
Automatically calculates derived indicators:
- Triaxiality (η)
- Lode parameter
- Principal stresses (σ1, σ2, σ3)

Usage:
    python anim_to_vtk_enhanced.py <input_anim_file> <output_vtk_file>
    
Example:
    python anim_to_vtk_enhanced.py Punch_Die_Shearing_v5A001 output.vtk
"""

import subprocess
import sys
import numpy as np
import re
import os

def compute_principal_stresses(sxx, syy, szz, sxy, syz, szx):
    """
    Compute principal stresses from stress tensor components.
    Returns σ1 >= σ2 >= σ3 (sorted from max to min)
    """
    stress_tensor = np.array([
        [sxx, sxy, szx],
        [sxy, syy, syz],
        [szx, syz, szz]
    ])
    eigenvalues = np.linalg.eigvalsh(stress_tensor)
    return np.sort(eigenvalues)[::-1]  # Sort descending: σ1, σ2, σ3

def compute_von_mises(sxx, syy, szz, sxy, syz, szx):
    """Compute Von Mises stress from stress tensor components."""
    return np.sqrt(0.5 * ((sxx - syy)**2 + (syy - szz)**2 + (szz - sxx)**2 + 
                          6 * (sxy**2 + syz**2 + szx**2)))

def compute_triaxiality(sigma_m, sigma_vm):
    """
    Compute stress triaxiality η = σ_m / σ_VM
    η > 0.33: tension-dominated (ductile void growth)
    η ≈ 0: pure shear
    η < 0: compression-dominated
    """
    if abs(sigma_vm) < 1e-10:
        return 0.0
    return sigma_m / sigma_vm

def compute_lode_parameter(s1, s2, s3):
    """
    Compute Lode parameter θ = (2σ2 - σ1 - σ3) / (σ1 - σ3)
    θ = -1: axisymmetric tension
    θ = 0: pure shear
    θ = +1: axisymmetric compression
    """
    denominator = s1 - s3
    if abs(denominator) < 1e-10:
        return 0.0
    return (2*s2 - s1 - s3) / denominator

def parse_vtk_and_enhance(input_vtk_path, output_vtk_path):
    """
    Read VTK file from anim_to_vtk, compute derived indicators, and save enhanced VTK.
    """
    with open(input_vtk_path, 'r') as f:
        lines = f.readlines()
    
    # Parse VTK structure
    header_lines = []
    points_data = []
    cells_data = []
    cell_types_data = []
    scalars_data = {}
    tensors_data = {}
    
    i = 0
    n_points = 0
    n_cells = 0
    current_section = None
    current_scalar_name = None
    current_tensor_name = None
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("POINTS"):
            parts = line.split()
            n_points = int(parts[1])
            header_lines.append(lines[i])
            i += 1
            for j in range(n_points):
                points_data.append(lines[i + j])
            i += n_points
            continue
        
        elif line.startswith("CELLS"):
            parts = line.split()
            n_cells = int(parts[1])
            header_lines.append(lines[i])
            i += 1
            for j in range(n_cells):
                cells_data.append(lines[i + j])
            i += n_cells
            continue
        
        elif line.startswith("CELL_TYPES"):
            header_lines.append(lines[i])
            i += 1
            for j in range(n_cells):
                cell_types_data.append(lines[i + j])
            i += n_cells
            continue
        
        elif line.startswith("CELL_DATA"):
            header_lines.append(lines[i])
            i += 1
            continue
        
        elif line.startswith("SCALARS"):
            parts = line.split()
            current_scalar_name = parts[1]
            scalars_data[current_scalar_name] = {'header': lines[i], 'lookup': '', 'values': []}
            i += 1
            if lines[i].strip().startswith("LOOKUP_TABLE"):
                scalars_data[current_scalar_name]['lookup'] = lines[i]
                i += 1
            for j in range(n_cells):
                if i + j < len(lines):
                    scalars_data[current_scalar_name]['values'].append(float(lines[i + j].strip()))
            i += n_cells
            continue
        
        elif line.startswith("TENSORS"):
            parts = line.split()
            current_tensor_name = parts[1]
            tensors_data[current_tensor_name] = {'header': lines[i], 'values': []}
            i += 1
            for j in range(n_cells):
                tensor_values = []
                for k in range(3):  # 3 rows of tensor
                    if i < len(lines):
                        row = [float(x) for x in lines[i].strip().split()]
                        tensor_values.extend(row)
                        i += 1
                tensors_data[current_tensor_name]['values'].append(tensor_values)
            continue
        
        else:
            header_lines.append(lines[i])
            i += 1
    
    # Check if stress tensor is available
    stress_tensor_name = None
    for name in tensors_data:
        if 'stress' in name.lower() or 'tens' in name.lower():
            stress_tensor_name = name
            break
    
    # Compute derived indicators if stress tensor available
    triaxiality = []
    lode_param = []
    sigma1 = []
    sigma2 = []
    sigma3 = []
    hydrostatic_stress = []
    
    if stress_tensor_name:
        for tensor in tensors_data[stress_tensor_name]['values']:
            # Tensor format: [sxx, sxy, sxz, syx, syy, syz, szx, szy, szz]
            if len(tensor) >= 9:
                sxx, sxy, sxz = tensor[0], tensor[1], tensor[2]
                syx, syy, syz = tensor[3], tensor[4], tensor[5]
                szx, szy, szz = tensor[6], tensor[7], tensor[8]
            else:
                sxx = syy = szz = sxy = syz = szx = 0.0
            
            # Compute principal stresses
            s1, s2, s3 = compute_principal_stresses(sxx, syy, szz, sxy, syz, szx)
            sigma1.append(s1)
            sigma2.append(s2)
            sigma3.append(s3)
            
            # Compute hydrostatic stress
            sigma_m = (sxx + syy + szz) / 3.0
            hydrostatic_stress.append(sigma_m)
            
            # Compute Von Mises
            sigma_vm = compute_von_mises(sxx, syy, szz, sxy, syz, szx)
            
            # Compute triaxiality
            eta = compute_triaxiality(sigma_m, sigma_vm)
            triaxiality.append(eta)
            
            # Compute Lode parameter
            lode = compute_lode_parameter(s1, s2, s3)
            lode_param.append(lode)
    else:
        # If no tensor data, try to compute from Von Mises if available
        print("Warning: No stress tensor found. Computing only from available data.")
        for _ in range(n_cells):
            triaxiality.append(0.0)
            lode_param.append(0.0)
            sigma1.append(0.0)
            sigma2.append(0.0)
            sigma3.append(0.0)
            hydrostatic_stress.append(0.0)
    
    # Write enhanced VTK file
    with open(output_vtk_path, 'w') as f:
        # Write header and geometry
        for line in header_lines:
            if line.strip().startswith("CELL_DATA"):
                f.write(line)
                break
            f.write(line)
        
        f.write(f"CELL_DATA {n_cells}\n")
        
        # Write original scalars
        for name, data in scalars_data.items():
            f.write(data['header'])
            if data['lookup']:
                f.write(data['lookup'])
            for v in data['values']:
                f.write(f"{v}\n")
        
        # Write original tensors
        for name, data in tensors_data.items():
            f.write(data['header'])
            for tensor in data['values']:
                for i in range(0, 9, 3):
                    f.write(f"{tensor[i]} {tensor[i+1]} {tensor[i+2]}\n")
        
        # Write derived indicators
        f.write("SCALARS Triaxiality_Eta float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for v in triaxiality:
            f.write(f"{v}\n")
        
        f.write("SCALARS Lode_Parameter float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for v in lode_param:
            f.write(f"{v}\n")
        
        f.write("SCALARS Principal_Stress_1 float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for v in sigma1:
            f.write(f"{v}\n")
        
        f.write("SCALARS Principal_Stress_2 float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for v in sigma2:
            f.write(f"{v}\n")
        
        f.write("SCALARS Principal_Stress_3 float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for v in sigma3:
            f.write(f"{v}\n")
        
        f.write("SCALARS Hydrostatic_Stress float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for v in hydrostatic_stress:
            f.write(f"{v}\n")
    
    print(f"Enhanced VTK saved: {output_vtk_path}")
    print(f"  - Triaxiality (η): {len(triaxiality)} cells")
    print(f"  - Lode Parameter: {len(lode_param)} cells")
    print(f"  - Principal Stresses (σ1, σ2, σ3): {len(sigma1)} cells")

def convert_anim_to_enhanced_vtk(anim_file, output_vtk):
    """
    Full pipeline: OpenRadioss Anim -> Basic VTK -> Enhanced VTK
    """
    anim_to_vtk_exe = r"D:\OpenRadioss\exec\anim_to_vtk_win64.exe"
    
    # Step 1: Convert to basic VTK using OpenRadioss tool
    temp_vtk = output_vtk + ".temp"
    print(f"Converting {anim_file} to VTK...")
    
    try:
        result = subprocess.run(
            [anim_to_vtk_exe, anim_file],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(anim_file) or "."
        )
        
        # Save output to temp file
        with open(temp_vtk, 'w') as f:
            f.write(result.stdout)
        
        if os.path.getsize(temp_vtk) < 100:
            print(f"Error: VTK conversion failed. Output too small.")
            return False
        
        # Step 2: Enhance with derived indicators
        print("Computing derived indicators (η, Lode, σ1, σ2, σ3)...")
        parse_vtk_and_enhance(temp_vtk, output_vtk)
        
        # Cleanup temp file
        os.remove(temp_vtk)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def batch_convert(base_name, output_dir="."):
    """
    Convert all animation files matching pattern to enhanced VTK.
    """
    import glob
    
    pattern = f"{base_name}A*"
    files = sorted(glob.glob(pattern))
    
    print(f"Found {len(files)} animation files matching '{pattern}'")
    
    for anim_file in files:
        name = os.path.basename(anim_file)
        # Extract number (e.g., A001 -> 001)
        match = re.search(r'A(\d+)', name)
        if match:
            num = match.group(1)
            output_vtk = os.path.join(output_dir, f"{base_name}_A{num}_enhanced.vtk")
            convert_anim_to_enhanced_vtk(anim_file, output_vtk)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nBatch mode:")
        print("  python anim_to_vtk_enhanced.py --batch <base_name>")
        print("  Example: python anim_to_vtk_enhanced.py --batch Punch_Die_Shearing_v5")
        sys.exit(1)
    
    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("Error: Please specify base name for batch conversion")
            sys.exit(1)
        batch_convert(sys.argv[2])
    else:
        anim_file = sys.argv[1]
        output_vtk = sys.argv[2] if len(sys.argv) > 2 else anim_file + "_enhanced.vtk"
        convert_anim_to_enhanced_vtk(anim_file, output_vtk)
