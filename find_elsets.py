import re

with open('ASSY_OpenRadioss_PM7T1C_20260102.inp', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if '*Element' in line and 'Elset=' in line:
            print(f"Line {i}: {line.strip()}")
