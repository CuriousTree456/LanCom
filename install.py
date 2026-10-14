import subprocess
import sys

def run(command):
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error running: {command}")
        sys.exit(1)

print("Installing libraries...\n")
run(f"{sys.executable} -m pip install --upgrade pip")
run(f"{sys.executable} -m pip install -r requirements.txt")
print("Setup complete!")