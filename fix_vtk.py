import glob
import os

def clean_vtk(file_path):
    print(f"Cleaning {file_path}...")
    with open(file_path, 'r', errors='ignore') as f:
        content = f.read()
    
    # Replace common issues
    # Note: simplistic replacement, but effective for VTK ASCII data
    # Be careful not to replace "infinite" word if it existed, but VTK is mostly numbers.
    # We target isolated "inf" usually, but simplist replacement is often " inf " -> " 0.0 "
    # or just replace string "inf" if it appears as a value.
    
    new_content = content.replace(" -inf", " 0.0").replace(" inf", " 0.0").replace(" nan", " 0.0").replace(" -nan", " 0.0")
    
    # Also handle lowercase if any (OpenRadioss usually uses inf, but just in case)
    new_content = new_content.replace("\n-inf", "\n0.0").replace("\ninf", "\n0.0")
    
    if content != new_content:
        print(f"  -> Fixed numerical errors in {file_path}")
        with open(file_path, 'w') as f:
            f.write(new_content)
    else:
        print("  -> No issues found.")

vtk_files = glob.glob("*.vtk")
for vtk in vtk_files:
    clean_vtk(vtk)
