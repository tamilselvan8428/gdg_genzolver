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
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager

API_KEY = "AIzaSyDJcR1N1QoNrmNTIPl492ZsHhos2sWW-Vs"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

st.title("🤖 Solve your problem with GenZolver")
st.write("Type 'Solve LeetCode [problem number]' or 'Open [app name]'.")

@st.cache_data
def fetch_problems():
    try:
        res = requests.get("https://leetcode.com/api/problems/all/")
        if res.status_code == 200:
            data = res.json()
            return {str(p["stat"]["frontend_question_id"]): p["stat"]["question__title_slug"] for p in data["stat_status_pairs"]}
    except Exception as e:
        st.error(f"❌ Error fetching problems: {e}")
    return {}

problems_dict = fetch_problems()

def get_slug(pid):
    return problems_dict.get(pid)

def open_problem(pid):
    slug = get_slug(pid)
    if slug:
        url = f"https://leetcode.com/problems/{slug}/"
        webbrowser.open(url, new=2)
        time.sleep(7)
        return url
    st.error("❌ Invalid problem number.")
    return None

def get_problem_statement(slug):
    try:
        query = {"query": """
        query getQuestionDetail($titleSlug: String!) {
          question(titleSlug: $titleSlug) { content title }
        }""",
        "variables": {"titleSlug": slug}}
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

def submit_solution(pid, lang, sol):
    try:
        st.info("🔍 Opening LeetCode page...")
        slug = get_slug(pid)
        url = f"https://leetcode.com/problems/{slug}/"
        
        options = webdriver.EdgeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)
        driver.get(url)
        
        time.sleep(7)
        pyperclip.copy(sol)
        
        st.info("⌨ Pasting solution...")
        editor = driver.find_element(By.CLASS_NAME, "monaco-editor")
        editor.click()
        time.sleep(1)
        editor.send_keys(Keys.CONTROL, 'a')
        editor.send_keys(Keys.CONTROL, 'v')
        time.sleep(1)
        
        run_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Run')]" )
        run_button.click()
        
        st.info("🚀 Running code...")
        time.sleep(10)
        
        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]" )
        submit_button.click()
        
        st.success(f"✅ Problem {pid} submitted successfully!")
        driver.quit()
    except Exception as e:
        st.error(f"❌ Selenium Error: {e}")

def open_application(app_name):
    st.error("❌ Application opening is not supported in cloud deployment.")

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
else:
    try:
        res = model.generate_content(user_input)
        st.chat_message("assistant").write(res.text)
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")
