import streamlit as st
import requests
import time
import pyperclip
import google.generativeai as genai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# --- 🌐 Setup Selenium WebDriver ---
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# --- 🔐 Gemini API Setup ---
API_KEY = "AIzaSyDJcR1N1QoNrmNTIPl492ZsHhos2sWW-Vs"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- 🌐 Streamlit UI ---
st.title("🤖 LeetCode Auto-Solver & Analytics Chatbot")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

@st.cache_data
def fetch_problems():
    """Fetch all LeetCode problems."""
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
    """Open the LeetCode problem in Selenium."""
    slug = get_slug(pid)
    if slug:
        url = f"https://leetcode.com/problems/{slug}/"
        driver.get(url)
        time.sleep(7)  # Wait for page load
        return url
    st.error("❌ Invalid problem number.")
    return None

def get_problem_statement(slug):
    """Fetch problem statement using GraphQL API."""
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
    return "❌ Failed to fetch problem."

def solve_with_gemini(pid, lang, text):
    """Generate solution using Gemini AI."""
    if text.startswith("❌"):
        return "❌ Problem fetch failed."
    
    prompt = f"""Solve the following LeetCode problem in {lang}:
Problem:  
{text}
Requirements:
- Wrap the solution inside class Solution {{ public: ... }}.
- Follow the LeetCode function signature.
- Return only the full class definition with the method inside.
Solution:"""
    
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"❌ Gemini Error: {e}"

def submit_solution(pid, lang, sol):
    """Paste & submit solution using Selenium (no PyAutoGUI)."""
    try:
        st.info("🔍 Opening LeetCode page...")
        open_problem(pid)
        time.sleep(3)

        st.info("⌨ Finding editor & pasting solution...")
        
        # Locate the code editor
        editor = driver.find_element("xpath", "//textarea[@class='CodeMirror']")  
        editor.click()
        
        # Copy & paste solution
        pyperclip.copy(sol)
        editor.send_keys(Keys.CONTROL, 'v')  # Paste with CTRL+V

        st.info("🚀 Running code...")
        run_button = driver.find_element("xpath", "//button[contains(text(),'Run')]")
        run_button.click()
        time.sleep(8)

        # Verify run success
        if is_run_successful():
            st.success("✅ Code executed successfully! Now submitting...")

            submit_button = driver.find_element("xpath", "//button[contains(text(),'Submit')]")
            submit_button.click()
            st.info("🏆 Submitting solution...")
            time.sleep(10)

            if is_submission_successful():
                st.success(f"✅ Problem {pid} submitted successfully!")
            else:
                st.error("❌ Submission failed. Retrying...")
                submit_solution(pid, lang, sol)  # Retry if needed
        else:
            st.error("❌ Run failed. Check the solution or retry.")
    except Exception as e:
        st.error(f"❌ Selenium Error: {e}")

def is_run_successful():
    """Check if code execution was successful (Mocked)."""
    time.sleep(5)
    return True  # Replace with actual verification

def is_submission_successful():
    """Check if submission was successful (Mocked)."""
    time.sleep(5)
    return True  # Replace with actual verification

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
elif user_input:
    try:
        res = model.generate_content(user_input)
        st.chat_message("assistant").write(res.text)
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")
