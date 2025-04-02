import os
import streamlit as st
import requests
import time
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- 🔐 Secure API Key Setup ---
API_KEY = os.getenv("GEMINI_API_KEY")  # Load from environment variable
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- 🌐 Streamlit UI ---
st.title("🤖 LeetCode Auto-Solver & Analytics Chatbot")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

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

def solve_with_gemini(pid, lang, text):
    if text.startswith("❌"):
        return "❌ Problem fetch failed."
    
    prompt = f"""Solve the following LeetCode problem in {lang}:
    Problem:  
    {text}
    Requirements:
    - Follow LeetCode function signature.
    - Return only the full class definition with the method inside.
    - Do NOT use code fences.
    Solution:"""
    
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"❌ Gemini Error: {e}"

# --- 🚀 Selenium Browser Automation (Headless Mode) ---
def setup_browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver

def submit_solution(pid, lang, sol):
    driver = setup_browser()
    slug = get_slug(pid)
    if not slug:
        st.error("❌ Invalid problem number.")
        return
    url = f"https://leetcode.com/problems/{slug}/"
    driver.get(url)
    time.sleep(5)  # Wait for the page to load
    
    try:
        # Select language dropdown
        lang_dropdown = driver.find_element(By.CLASS_NAME, "select-dropdown")
        lang_dropdown.click()
        time.sleep(1)
        driver.find_element(By.XPATH, f"//div[text()='{lang}']").click()
        time.sleep(1)

        # Paste the solution
        editor = driver.find_element(By.CLASS_NAME, "monaco-editor")
        editor.click()
        pyperclip.copy(sol)
        editor.send_keys(Keys.CONTROL, 'a')  # Select all
        editor.send_keys(Keys.CONTROL, 'v')  # Paste
        time.sleep(2)

        # Run the code
        run_button = driver.find_element(By.CLASS_NAME, "run-code")
        run_button.click()
        time.sleep(10)

        # Submit the solution
        submit_button = driver.find_element(By.CLASS_NAME, "submit-code")
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
