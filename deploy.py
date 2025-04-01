import os
import time
import sys
import subprocess
from pyngrok import ngrok, conf

# 🔑 Set your actual ngrok token
NGROK_AUTH_TOKEN = "2v4ZMj9NMVkJrfgumerR4RiZK70_smuQ1yZuY8hFR6a5AqB4"  # Replace with your actual token

# ✅ Ensure ngrok authentication is set
if NGROK_AUTH_TOKEN:
    conf.get_default().auth_token = NGROK_AUTH_TOKEN

# 🚀 Start Streamlit App
def start_streamlit():
    print("🟢 Starting Streamlit...")
    subprocess.Popen(["streamlit", "run", "app.py", "--server.address", "0.0.0.0"])
# 🌍 Start ngrok (Fixed version)
def start_ngrok():
    try:
        port = 8501  # Streamlit default port
        tunnel = ngrok.connect(port)  # ✅ Removed 'region' to fix config error
        print(f"🌍 Public URL: {tunnel.public_url}")
        return tunnel.public_url
    except Exception as e:
        print(f"❌ ngrok Error: {e}")
        sys.exit(1)  # Exit if ngrok fails

if __name__ == "__main__":
    start_streamlit()
    time.sleep(5)  # Allow Streamlit to start
    public_url = start_ngrok()
    print(f"🔗 Access your chatbot here: {public_url}")
