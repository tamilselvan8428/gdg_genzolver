import os
import streamlit as st
import webbrowser
import requests
import time
import pyperclip
import google.generativeai as genai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# --- 🔐 Gemini API Setup ---
API_KEY = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- 🌐 Streamlit UI Setup ---
st.title("🤖 LeetCode Auto-Solver & App Launcher")
st.write("Type 'Solve LeetCode [problem number]'. You can also enter commands like 'Open [app name]'.")

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
    """Open the LeetCode problem using Selenium."""
    slug = get_slug(pid)
    if slug:
        url = f"https://leetcode.com/problems/{slug}/"
        return url
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

# --- 🛠 Submit Solution Using Selenium ---
def submit_solution(pid, lang, sol):
    """Automate the process of pasting and submitting a solution on LeetCode using Selenium."""
    url = open_problem(pid)
    if not url:
        st.error("❌ Invalid problem number.")
        return

    # Start Selenium WebDriver for Edge
    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service)
    driver.get(url)
    time.sleep(5)

    try:
        # Click "Sign In" (if needed)
        try:
            sign_in_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Sign in')]")
            sign_in_btn.click()
            st.info("🔑 Please log in manually.")
            time.sleep(20)  # Wait for manual login
        except:
            st.info("✅ Already logged in.")

        # Click on the code editor
        editor = driver.find_element(By.CLASS_NAME, "CodeMirror")
        editor.click()
        time.sleep(2)

        # Paste the solution
        pyperclip.copy(sol)
        editor.send_keys(Keys.CONTROL, 'a')
        editor.send_keys(Keys.CONTROL, 'v')
        time.sleep(2)

        # Run the solution
        run_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Run')]")
        run_btn.click()
        st.info("🚀 Running code...")
        time.sleep(10)

        # Submit the solution
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

elif user_input.lower().startswith("open"):
    tokens = user_input.strip().split(maxsplit=1)
    if len(tokens) == 2:
        app_name = tokens[1]
        open_application(app_name)  # Add this function if you need app launcher feature
    else:
        st.error("❌ Use format: Open [app name]")

elif user_input:
    try:
        res = model.generate_content(user_input)
        st.chat_message("assistant").write(res.text)
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")
