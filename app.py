import os
import streamlit as st
import requests
import time
import pyperclip
import google.generativeai as genai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- 🔐 Gemini API Setup ---
API_KEY = "AIzaSyDJcR1N1QoNrmNTIPl492ZsHhos2sWW-Vs"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- 🌐 Streamlit UI Setup ---
st.title("🤖 LeetCode Auto-Solver & App Launcher")
st.write("Type 'Solve LeetCode [problem number]'.")

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

# --- 🚀 Set Up Selenium ---
def setup_selenium():
    """Set up Selenium with headless Chrome for deployment."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# --- 📝 Fetch Problem Statement ---
def get_problem_statement(slug):
    """Fetch problem statement using LeetCode GraphQL API."""
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

# --- 🛠 Submit Solution Using Selenium ---
def submit_solution(pid, lang, sol):
    """Automate LeetCode submission using Selenium."""
    slug = get_slug(pid)
    if not slug:
        st.error("❌ Invalid problem number.")
        return
    
    url = f"https://leetcode.com/problems/{slug}/"
    driver = setup_selenium()
    driver.get(url)
    time.sleep(5)

    try:
        # Click on the code editor
        editor = driver.find_element(By.CLASS_NAME, "CodeMirror")
        editor.click()
        time.sleep(2)

        # Paste solution
        pyperclip.copy(sol)
        editor.send_keys(Keys.CONTROL, 'a')
        editor.send_keys(Keys.CONTROL, 'v')
        time.sleep(2)

        # Run solution
        run_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Run')]")
        run_btn.click()
        st.info("🚀 Running code...")
        time.sleep(10)

        # Submit solution
        submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
        submit_btn.click()
        st.success(f"✅ Problem {pid} submitted successfully!")

    except Exception as e:
        st.error(f"❌ Selenium Error: {e}")

    finally:
        driver.quit()

# --- 🎯 User Input Handling ---
user_input = st.text_input("Your command:")

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
                submit_solution(pid, lang, solution)
        else:
            st.error("❌ Invalid problem number.")
    else:
        st.error("❌ Use format: Solve LeetCode [problem number]")
