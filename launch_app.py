import os
import subprocess
import sys

# Get the full path of your Streamlit app
app_path = os.path.join(os.path.dirname(__file__), "app.py")

# Launch Streamlit just like using terminal

subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
