import streamlit as st
import requests
import time
import os
import subprocess
import google.generativeai as genai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# --- Install Chrome & ChromeDriver on Render ---
def install_chrome():
    if not os.path.exists("/usr/bin/google-chrome"):
        print("🔽 Installing Google Chrome...")
        subprocess.run("wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb", shell=True)
        subprocess.run("dpkg -i google-chrome-stable_current_amd64.deb || apt-get -f install -y", shell=True)

def install_chromedriver():
    if not os.path.exists("/usr/bin/chromedriver"):
        print("🔽 Installing ChromeDriver...")
        subprocess.run("wget https://chromedriver.storage.googleapis.com/$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip", shell=True)
        subprocess.run("unzip chromedriver_linux64.zip", shell=True)
        subprocess.run("mv chromedriver /usr/bin/chromedriver", shell=True)
        subprocess.run("chmod +x /usr/bin/chromedriver", shell=True)

install_chrome()
install_chromedriver()

# --- 🔐 Gemini API Setup ---
API_KEY = os.getenv("GEMINI_API_KEY")  # Use environment variable
if not API_KEY:
    st.error("❌ Missing GEMINI_API_KEY. Set it in Render's environment variables.")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- 🌐 Streamlit UI Setup ---
st.title("🤖 LeetCode Auto-Solver & Analytics Chatbot")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

# --- 🗂 Cache LeetCode Problems ---
@st.cache_data
def fetch_problems():
    try:
        res = requests.get("https://leetcode.com/api/problems/all/")
        if res.status_code == 200:
            data = res.json()
            return {str(p["stat"]["frontend_question_id"]): p["stat"]["question__title_slug"]
                    for p in data["stat_status_pairs"]}
    except Exception as e:
        st.error(f"❌ Error fetching problems: {e}")
    return {}

problems_dict = fetch_problems()

def get_slug(pid): 
    return problems_dict.get(pid)

# --- 📝 Fetch Problem Statement ---
def get_problem_statement(slug):
    try:
        query = {
            "query": """
            query getQuestionDetail($titleSlug: String!) {
              question(titleSlug: $titleSlug) { content title }
            }""",
            "variables": {"titleSlug": slug}
        }
        res = requests.post("https://leetcode.com/graphql", json=query)
        if res.status_code == 200:
            html = res.json()["data"]["question"]["content"]
            return BeautifulSoup(html, "html.parser").get_text()
    except Exception as e:
        return f"❌ GraphQL error: {e}"
    return "❌ Failed to fetch problem."

# --- 🤖 Gemini AI Solver ---
def solve_with_gemini(pid, lang, text):
    if text.startswith("❌"):
        return "❌ Problem fetch failed."
    
    prompt = f"""Solve the following LeetCode problem in {lang}:
Problem:  
{text}
Requirements:
- Wrap the solution inside class Solution {{ public: ... }}.
- Follow the LeetCode function signature.
- Return only the full class definition with the method inside.
- Do NOT use code fences.
Solution:"""
    
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"❌ Gemini Error: {e}"

# --- 🔍 Selenium Automation (Modified for Render) ---
def open_problem_and_paste_solution(pid, solution):
    slug = get_slug(pid)
    if not slug:
        st.error("❌ Invalid problem number.")
        return
    
    url = f"https://leetcode.com/problems/{slug}/"
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode on Render
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service("/usr/bin/chromedriver")  # Use Chrome WebDriver
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        st.info("🔍 Opening LeetCode page...")
        driver.get(url)
        time.sleep(5)

        editor = driver.find_element(By.CLASS_NAME, "CodeMirror")
        editor.click()
        time.sleep(1)
        editor.send_keys(Keys.CONTROL, 'a')  # Select all
        editor.send_keys(Keys.DELETE)  # Clear editor
        editor.send_keys(solution)  # Type solution

        run_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Run')]")
        run_button.click()
        st.info("🚀 Running solution...")
        time.sleep(10)

        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
        submit_button.click()
        st.success(f"✅ Problem {pid} submitted successfully!")

    except Exception as e:
        st.error(f"❌ Selenium Error: {e}")
    
    finally:
        driver.quit()

# --- 🎯 User Input Handling ---
user_input = st.text_input("Your command or question:")

if user_input.lower().startswith("solve leetcode"):
    tokens = user_input.strip().split()
    if len(tokens) == 3 and tokens[2].isdigit():
        pid = tokens[2]
        slug = get_slug(pid)
        if slug:
            lang = st.selectbox("Language", ["cpp", "python", "java", "javascript", "csharp"], index=0)
            if st.button("Generate & Submit Solution"):
                text = get_problem_statement(slug)
                solution = solve_with_gemini(pid, lang, text)
                st.code(solution, language=lang)
                open_problem_and_paste_solution(pid, solution)
        else:
            st.error("❌ Invalid problem number.")
    else:
        st.error("❌ Use format: Solve LeetCode [problem number]")
elif user_input:
    try:
        res = model.generate_content(user_input)
        st.chat_message("assistant").write(res.text)
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")