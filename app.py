import streamlit as st
import webbrowser
import requests
import time
import google.generativeai as genai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- 🔐 Gemini API Setup ---
API_KEY = "YOUR_GEMINI_API_KEY"
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

# --- 🌍 Selenium Setup (Headless Mode) ---
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

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

# --- 🔍 Open & Automate LeetCode ---
def submit_solution(pid, lang, sol):
    """Automate the process of opening LeetCode, pasting solution, running, and submitting."""
    slug = get_slug(pid)
    if not slug:
        st.error("❌ Invalid problem number.")
        return
    
    url = f"https://leetcode.com/problems/{slug}/"
    st.info(f"🔍 Opening LeetCode problem: {url}")

    # Start Selenium driver
    driver = setup_driver()
    driver.get(url)
    time.sleep(5)

    # --- Log in (if required) ---
    try:
        login_button = driver.find_element(By.XPATH, "//a[text()='Sign in']")
        login_button.click()
        time.sleep(3)

        # Enter credentials (Ensure to replace with your credentials or use environment variables)
        username_input = driver.find_element(By.ID, "id_login")
        password_input = driver.find_element(By.ID, "id_password")

        username_input.send_keys("YOUR_LEETCODE_EMAIL")
        password_input.send_keys("YOUR_LEETCODE_PASSWORD")
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)
    except:
        st.info("✅ Already logged in.")

    # --- Select Language ---
    try:
        lang_dropdown = driver.find_element(By.CLASS_NAME, "Select__control")
        lang_dropdown.click()
        time.sleep(2)

        lang_option = driver.find_element(By.XPATH, f"//div[text()='{lang.capitalize()}']")
        lang_option.click()
        time.sleep(2)
    except:
        st.info("⚠ Language selection skipped (default used).")

    # --- Select Editor and Paste Solution ---
    try:
        code_editor = driver.find_element(By.CLASS_NAME, "view-line")
        code_editor.click()
        time.sleep(1)

        # Clear existing code
        code_editor.send_keys(Keys.CONTROL + "a")
        code_editor.send_keys(Keys.BACKSPACE)

        # Paste new solution
        for line in sol.split("\n"):
            code_editor.send_keys(line)
            code_editor.send_keys(Keys.SHIFT + Keys.ENTER)

        st.info("⌨ Solution pasted successfully!")
    except:
        st.error("❌ Error pasting solution.")

    # --- Run the solution ---
    try:
        run_button = driver.find_element(By.XPATH, "//button[text()='Run']")
        run_button.click()
        st.info("🚀 Running the solution...")
        time.sleep(10)
    except:
        st.error("❌ Run button not found.")

    # --- Submit the solution ---
    try:
        submit_button = driver.find_element(By.XPATH, "//button[text()='Submit']")
        submit_button.click()
        st.info("🏆 Submitting the solution...")
        time.sleep(10)
        st.success(f"✅ Problem {pid} submitted successfully!")
    except:
        st.error("❌ Submission failed.")

    # Close the browser
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
