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
    project_id = "genzolver-455514"
    name = f"projects/{project_id}/secrets/gemini-api-key/versions/latest"
    
    try:
        response = client.access_secret_version(name=name)
        key = response.payload.data.decode("UTF-8")
        st.write(f"✅ API Key Loaded Successfully: {key[:5]}****")  # Debug log
        return key
    except Exception as e:
        st.error(f"❌ Failed to fetch API Key: {e}")
        return None


api_key = get_api_key()
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    st.write("✅ AI Model Initialized")  # Debugging log
else:
    model = None

# --- 🌐 Streamlit UI Setup ---
st.title("🤖 LeetCode Auto-Solver & Analytics Chatbot")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

@st.cache_data
def fetch_problems():
    """Fetch all LeetCode problems"""
    try:
        st.write("Fetching LeetCode problems...")  # Debug log
        res = requests.get("https://leetcode.com/api/problems/all/")
        if res.status_code == 200:
            data = res.json()
            problems = {str(p["stat"]["frontend_question_id"]): p["stat"]["question__title_slug"]
                        for p in data["stat_status_pairs"]}
            st.write(f"✅ Problems Loaded: {len(problems)}")  # Debug log
            return problems
        else:
            st.error(f"❌ Failed to fetch problems. Status Code: {res.status_code}")
    except Exception as e:
        st.error(f"❌ Error fetching problems: {e}")
    return {}


problems_dict = fetch_problems()

def handle_input():
    """Handles user input for solving problems or asking questions"""
    user_input = st.session_state["user_input"].strip()
    
    if user_input.lower().startswith("solve leetcode"):
        tokens = user_input.split()
        if len(tokens) == 3 and tokens[2].isdigit():
            pid = tokens[2]
            slug = problems_dict.get(pid)
            if slug:
                lang = st.selectbox("Language", ["cpp", "python", "java", "javascript", "csharp"], index=0)
                if st.button("Generate & Submit Solution"):
                    url = f"https://leetcode.com/problems/{slug}/"
                    webbrowser.open(url)
                    st.write(f"🔗 Opening problem: [{slug}]({url})")

                    # Fetch and solve problem
                    text = get_problem_statement(slug)
                    solution = solve_with_gemini(pid, lang, text)
                    
                    # Display the solution
                    st.code(solution, language=lang)
                    
                    # Submit via Selenium
                    submit_solution_selenium(pid, lang, solution)
            else:
                st.error("❌ Invalid problem number.")
        else:
            st.error("❌ Use format: Solve LeetCode [problem number]")
    
    elif user_input:
        if model:
            try:
                st.write(f"🤔 **Generating answer for:** {user_input}")  # Debug log
                res = model.generate_content(user_input)
                if res and res.text:
                    st.write(res.text)
                else:
                    st.error("❌ No response generated. Check API limits.")
            except Exception as e:
                st.error(f"❌ Gemini Error: {e}")
        else:
            st.error("❌ AI Model not initialized.")

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
            return res.text.strip() if res.text else "❌ No solution generated."
        except Exception as e:
            return f"❌ Gemini Error: {e}"
    return "❌ AI Model not initialized."

# ✅ Ensure session state is initialized
if "user_input" not in st.session_state:
    st.session_state["user_input"] = ""

st.text_input(
    "Your command or question:",
    key="user_input",
    on_change=handle_input
)
