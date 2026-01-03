
import sys
import collections

def analyze_inp(filename):
    print(f"Analyzing {filename}...")
    keywords = collections.defaultdict(list)
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith('*'):
                    # Get the keyword (up to the first comma)
                    keyword = stripped.split(',')[0]
                    if len(keywords[keyword]) < 3: # Store first 3 locations
                        keywords[keyword].append(i)
                    
                    if keyword.lower() == '*element':
                        # Try to extract type
                        if 'type=' in stripped.lower():
                            parts = stripped.split(',')
                            for p in parts:
                                if 'type=' in p.lower():
                                    print(f"Found Element Type at {i}: {p.strip()}")
                                    break

    except Exception as e:
        print(f"Error: {e}")

    print("\nSubject Keywords found:")
    for k, v in keywords.items():
        print(f"{k}: found at lines {v}...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_inp(sys.argv[1])
