import sys


def get_running_applications() -> list[str]:
    """Get list of currently running application names."""
    apps = set()
    
    try:
        if sys.platform.startswith("win"):
            import subprocess
            try:
                # Windows: tasklist command
                result = subprocess.run(
                    ["tasklist"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    parts = line.split()
                    if parts:
                        name = parts[0].replace('.exe', '').strip()
                        if name and len(name) > 2 and not name.startswith('System'):
                            apps.add(name)
            except Exception as e:
                print(f"[ProcessHelper] Error with tasklist: {e}", flush=True)
        else:
            # Linux/Mac fallback
            import subprocess
            try:
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n')[1:]:
                    parts = line.split()
                    if len(parts) > 10:
                        name = parts[10].split('/')[-1]
                        if name and len(name) > 2:
                            apps.add(name)
            except Exception as e:
                print(f"[ProcessHelper] Error with ps: {e}", flush=True)
    except Exception as e:
        print(f"[ProcessHelper] Error getting running apps: {e}", flush=True)
    
    return sorted(list(apps))[:20]
