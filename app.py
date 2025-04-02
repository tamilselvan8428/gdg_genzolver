import streamlit as st
import webbrowser
import requests
import time
import os
import google.generativeai as genai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from google.cloud import secretmanager

# --- 🔐 Secure Gemini API Key from Google Cloud Secrets ---
def get_api_key():
    client = secretmanager.SecretManagerServiceClient()
    project_id = "genzolver-455514"  # ✅ Hardcoded project ID to avoid "None"
    name = f"projects/{project_id}/secrets/gemini-api-key/versions/latest"
    
    try:
        response = client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        st.error(f"❌ Failed to fetch API Key: {e}")
        return None


api_key = get_api_key()
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
else:
    model = None

# --- 🌐 Streamlit UI Setup ---
st.title("🤖 LeetCode Auto-Solver & Analytics Chatbot")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

@st.cache_data
def fetch_problems():
    """Fetch all LeetCode problems"""
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
    """Opens the LeetCode problem in a web browser"""
    slug = get_slug(pid)
    if slug:
        url = f"https://leetcode.com/problems/{slug}/"
        webbrowser.open(url)
        return url
    st.error("❌ Invalid problem number.")
    return None

def get_problem_statement(slug):
    """Fetch problem statement using LeetCode GraphQL API"""
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
    """Generates a LeetCode solution using Gemini AI"""
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
    
    if model:
        try:
            res = model.generate_content(prompt)
            return res.text.strip()
        except Exception as e:
            return f"❌ Gemini Error: {e}"
    return "❌ AI Model not initialized."

def setup_selenium():
    """Configures and initializes Selenium WebDriver"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    
    driver = webdriver.Chrome(options=options)
    return driver

def submit_solution_selenium(pid, lang, sol):
    """Automates solution submission on LeetCode"""
    try:
        driver = setup_selenium()
        slug = get_slug(pid)
        if not slug:
            st.error("❌ Invalid problem number.")
            return

        url = f"https://leetcode.com/problems/{slug}/"
        driver.get(url)
        time.sleep(5)

        # Find the textarea for code input
        editor = driver.find_element("css selector", "textarea")
        editor.clear()
        editor.send_keys(sol)
        editor.send_keys(Keys.CONTROL, "a")
        editor.send_keys(Keys.CONTROL, "v")

        # Click Run button
        run_button = driver.find_element("xpath", "//button[contains(text(), 'Run')]" )
        run_button.click()
        time.sleep(8)

        # Click Submit button
        submit_button = driver.find_element("xpath", "//button[contains(text(), 'Submit')]" )
        submit_button.click()
        time.sleep(10)

        st.success(f"✅ Problem {pid} submitted successfully!")
        driver.quit()
    except Exception as e:
        st.error(f"❌ Selenium Error: {e}")

def handle_input(user_input):
    """Handles user input for solving problems"""
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
                    submit_solution_selenium(pid, lang, solution)
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

# --- 🌍 Run Streamlit on Cloud Run Required Port ---
PORT = int(os.getenv("PORT", 8080))
if "user_input" not in st.session_state:
    st.session_state["user_input"] = ""

st.text_input("Your command or question:", key="user_input", on_change=handle_input, args=(st.session_state["user_input"],))

if __name__ == "__main__":
    st.run(port=PORT, server_headless=True)
