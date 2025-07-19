# run.py
import subprocess
import os
import platform

os.chdir("backend")

if platform.system() == "Windows":
    venv_activate = os.path.join("venv", "Scripts", "activate.bat")
    subprocess.call(venv_activate, shell=True)
else:
    venv_activate = "source venv/bin/activate"
    subprocess.call(venv_activate, shell=True)

subprocess.call(["python", "app.py"])
