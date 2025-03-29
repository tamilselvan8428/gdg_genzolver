import os
import streamlit as st
import webbrowser
import requests
import time
import pyperclip
import google.generativeai as genai
from bs4 import BeautifulSoup
import platform
import subprocess

# --- 🔐 Gemini API Setup ---
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- ✅ Ensure Windows, macOS & Linux Support ---
system_os = platform.system()
if system_os not in ["Windows", "Darwin", "Linux"]:
    st.error(f"❌ Unsupported OS: {system_os}. Only Windows, macOS, and Linux are supported.")
    st.stop()

st.success(f"✅ OS Detected: {system_os}")  # Show detected OS

# --- 🌐 Streamlit UI Setup ---
st.title("🤖 LeetCode Auto-Solver & Analytics Chatbot")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

# --- 🗂 Cache LeetCode Problems ---
@st.cache_data
def fetch_problems():
    """Fetches all LeetCode problems and caches them."""
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
    """Gets the problem slug for the given problem ID."""
    return problems_dict.get(pid, None)

def open_problem(pid):
    """Opens the LeetCode problem in a new tab."""
    slug = get_slug(pid)
    if slug:
        url = f"https://leetcode.com/problems/{slug}/"
        webbrowser.open(url, new=2)  
        time.sleep(2)  # Optimized wait time
        return url
    st.error("❌ Invalid problem number.")
    return None

# --- 📝 Fetch Problem Statement ---
def get_problem_statement(slug):
    """Fetches the problem statement using LeetCode's GraphQL API."""
    try:
        query = {
            "query": """
            query getQuestionDetail($titleSlug: String!) {
              question(titleSlug: $titleSlug) { content title }
            }""",
            "variables": {"titleSlug": slug}
        }
        res = requests.post("https://leetcode.com/graphql", json=query)
        if res.status_code == 200 and res.json().get("data"):
            html = res.json()["data"]["question"]["content"]
            return BeautifulSoup(html, "html.parser").get_text()
    except Exception as e:
        return f"❌ GraphQL error: {e}"
    return "❌ Failed to fetch problem."

# --- 🤖 Gemini AI Solver ---
def solve_with_gemini(pid, lang, text):
    """Generates a solution using Gemini AI."""
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
        return res.text.strip() if res.text else "❌ No solution generated."
    except Exception as e:
        return f"❌ Gemini Error: {e}"

# --- 🛠 Clipboard Copy (Fully Fixed) ---
def copy_to_clipboard(text):
    """Copies text to clipboard based on the OS, ensuring compatibility."""
    try:
        if system_os == "Linux":
            process = subprocess.Popen('xclip -selection clipboard', stdin=subprocess.PIPE, shell=True)
            process.communicate(input=text.encode())
        elif system_os == "Darwin":  # macOS
            process = subprocess.Popen('pbcopy', stdin=subprocess.PIPE)
            process.communicate(input=text.encode())
        elif system_os == "Windows":
            pyperclip.copy(text)
        else:
            return "⚠ Unsupported OS for clipboard copying."
        return "✅ Solution copied to clipboard!"
    except Exception as e:
        return f"⚠ Clipboard copy failed: {e}"

# --- 🛠 Submit Solution ---
def submit_solution(pid, lang, sol):
    """Opens LeetCode problem and copies the solution."""
    st.info("🔍 Opening LeetCode page...")
    open_problem(pid)
    copy_result = copy_to_clipboard(sol)
    st.success(copy_result)

# --- 🎯 User Input Handling ---
user_input = st.text_input("Your command or question:")

if user_input.lower().startswith("solve leetcode"):
    tokens = user_input.strip().split()
    if len(tokens) == 3 and tokens[2].isdigit():
        pid = tokens[2]
        slug = get_slug(pid)
        if slug:
            lang = st.selectbox("Language", ["cpp", "python", "java", "javascript", "csharp"], index=0)
            if st.button("Generate & Copy Solution"):
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
