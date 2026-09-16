import subprocess
import os
os.chdir("c:/Users/Pravin/Desktop/main/AT_Trading")

result = subprocess.run(
    ["python", "tests/test_entry_verify.py"],
    capture_output=True, text=True,
    cwd="c:/Users/Pravin/Desktop/main/AT_Trading/live_stuff"
)

print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
print(f"Return code: {result.returncode}")