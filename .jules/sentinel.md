
2025-05-15 - [Insecure Command Execution]
Replaced 'os.system' with 'subprocess.run' in 'main.py' to prevent shell injection vulnerabilities. Used 'sys.executable -m streamlit' to ensure the command runs within the correct Python environment and is not dependent on the system PATH.
