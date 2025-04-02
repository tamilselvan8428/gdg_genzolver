import streamlit as st
import requests
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- 🔐 Gemini API Setup ---
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- 🌐 Streamlit UI Setup ---
st.title("🤖 LeetCode Auto-Solver & Analytics Chatbot")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

@st.cache_data
def fetch_problems():
    """Fetch LeetCode problem list."""
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

def get_problem_statement(slug):
    """Fetch the problem statement from LeetCode."""
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

def solve_with_gemini(pid, lang, text):
    """Generate a solution using Gemini AI."""
    if text.startswith("❌"):
        return "❌ Problem fetch failed."
    
    prompt = f"""Solve the following LeetCode problem in {lang}:
Problem:  
{text}
Requirements:
- Follow the LeetCode function signature.
- Return only the full class definition with the method inside.
Solution:"""
    
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"❌ Gemini Error: {e}"

def setup_browser():
    """Setup Selenium Chrome WebDriver in headless mode."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    return driver

def submit_solution(pid, lang, sol):
    """Automate the process of opening LeetCode, pasting solution, running, and submitting."""
    slug = get_slug(pid)
    if not slug:
        st.error("❌ Invalid problem number.")
        return
    
    url = f"https://leetcode.com/problems/{slug}/"
    st.markdown(f"[Click here to open LeetCode problem {pid}]({url})", unsafe_allow_html=True)
    
    driver = setup_browser()
    driver.get(url)
    
    try:
        wait = WebDriverWait(driver, 10)
        
        st.write("✍ Pasting the solution...")
        editor = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "monaco-editor")))
        editor.click()
        editor.send_keys(Keys.CONTROL, 'a')  # Select all
        editor.send_keys(Keys.DELETE)  # Clear existing code
        editor.send_keys(sol)  # Paste solution
        
        st.write("🛠 Running the code...")
        run_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Run')]")))
        run_button.click()
        time.sleep(10)
        
        st.write("🚀 Submitting the solution...")
        submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Submit')]")))
        submit_button.click()
        time.sleep(10)
        
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
                submit_solution(pid, lang, solution)
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
