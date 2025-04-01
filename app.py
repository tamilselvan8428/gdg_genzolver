import os
import streamlit as st
import webbrowser
import requests
import time
import pyautogui
import pyperclip
import google.generativeai as genai
from bs4 import BeautifulSoup
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
# --- 🔐 Gemini API Setup ---
API_KEY = "AIzaSyDJcR1N1QoNrmNTIPl492ZsHhos2sWW-Vs"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- 🌐 Streamlit UI Setup ---
st.title("🤖 LeetCode Auto-Solver & App Launcher")
st.write("Type 'Solve LeetCode [problem number]' or 'Open [app name]'.")

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

def open_problem(pid):
    """Open the LeetCode problem only if it's not already open."""
    slug = get_slug(pid)
    if slug:
        url = f"https://leetcode.com/problems/{slug}/"
        webbrowser.open(url, new=2)  # Open in a new tab
        time.sleep(7)
        return url
    st.error("❌ Invalid problem number.")
    return None

# --- 📝 Fetch Problem Statement ---
def get_problem_statement(slug):
    """Fetch the problem statement from LeetCode using GraphQL API."""
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
    """Generate a solution using Gemini AI."""
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

# --- 🛠 Submit Solution ---    
def submit_solution(pid, lang, sol):
    """Automate pasting and submitting the solution on LeetCode using Selenium."""
    try:
        st.info("🔍 Opening LeetCode page...")
        url = open_problem(pid)

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        time.sleep(5)

        st.info("⌨ Locating code editor...")
        editor = driver.find_element(By.CLASS_NAME, "CodeMirror")
        editor.click()
        time.sleep(2)

        st.info("📋 Pasting solution...")
        editor.send_keys(Keys.CONTROL + "a")  # Select all
        editor.send_keys(Keys.CONTROL + "v")  # Paste solution
        time.sleep(2)

        st.info("🚀 Running the code...")
        run_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Run')]")
        run_button.click()
        time.sleep(10)

        st.success("✅ Code executed successfully! Now submitting...")

        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
        submit_button.click()
        time.sleep(10)

        st.success(f"✅ Problem {pid} submitted successfully!")
        driver.quit()

    except Exception as e:
        st.error(f"❌ Selenium Error: {e}")

# --- ✅ Open Any Application on Windows ---
def open_application(app_name):
    """Opens any application using Windows search (Win + S) and Enter."""
    try:
        st.info(f"🔍 Searching and opening '{app_name}'...")
        pyautogui.hotkey('win', 's')  # Open Windows Search
        time.sleep(1)
        pyautogui.write(app_name)  # Type app name
        time.sleep(1)
        pyautogui.press('enter')  # Open app
        st.success(f"✅ '{app_name}' opened successfully!")
    except Exception as e:
        st.error(f"❌ Error opening app: {e}")

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
                open_problem(pid)
                text = get_problem_statement(slug)
                solution = solve_with_gemini(pid, lang, text)
                st.code(solution, language=lang)
                submit_solution(pid, lang, solution)
        else:
            st.error("❌ Invalid problem number.")
    else:
        st.error("❌ Use format: Solve LeetCode [problem number]")

elif user_input.lower().startswith("open"):
    tokens = user_input.strip().split(maxsplit=1)
    if len(tokens) == 2:
        app_name = tokens[1]
        open_application(app_name)
    else:
        st.error("❌ Use format: Open [app name]")

elif user_input:
    try:
        res = model.generate_content(user_input)
        st.chat_message("assistant").write(res.text)
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")
