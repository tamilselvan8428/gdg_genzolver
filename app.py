import streamlit as st
import requests
import webbrowser
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- Fetch API Key ---
def get_api_key():
    return "YOUR_GEMINI_API_KEY"  # Replace this with actual API key fetching from Google Cloud

api_key = get_api_key()
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
else:
    model = None

# --- Streamlit UI ---
st.title("🤖 Solve your problem with Genzolver")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

@st.cache_data
def fetch_problems():
    """Fetch all LeetCode problems"""
    try:
        res = requests.get("https://leetcode.com/api/problems/all/")
        if res.status_code == 200:
            data = res.json()
            problems = {str(p["stat"]["frontend_question_id"]): p["stat"]["question__title_slug"]
                        for p in data["stat_status_pairs"]}
            return problems
        else:
            st.error(f"❌ LeetCode API error. Status: {res.status_code}")
    except Exception as e:
        st.error(f"❌ Error fetching problems: {e}")
    return {}

# Load problem dictionary
problems_dict = fetch_problems()
st.write("📌 Loaded LeetCode Problems:", len(problems_dict))  # Debugging output

def get_slug(pid):
    """Returns problem slug for a given problem ID"""
    slug = problems_dict.get(pid)
    if not slug:
        st.error(f"❌ Problem {pid} not found.")
    return slug

def open_problem(pid):
    """Opens the problem in a browser"""
    slug = get_slug(pid)
    if slug:
        url = f"https://leetcode.com/problems/{slug}/"
        webbrowser.open(url)
        return url
    return None

def get_problem_statement(slug):
    """Fetches problem statement using LeetCode GraphQL API"""
    if not slug:
        return "❌ Invalid problem slug."

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
    """Generates a solution using Gemini AI"""
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
            return f"❌ Gemini AI Error: {e}"
    
    return "❌ AI Model not initialized."

# --- User Input Handling ---
def handle_input():
    user_input = st.session_state["user_input"].strip()

    if user_input.lower().startswith("solve leetcode"):
        tokens = user_input.split()
        if len(tokens) == 3 and tokens[2].isdigit():
            pid = tokens[2]
            slug = get_slug(pid)
            if slug:
                lang = st.selectbox("Choose Language", ["cpp", "python", "java", "javascript"], index=1)
                if st.button("Generate Solution"):
                    open_problem(pid)
                    text = get_problem_statement(slug)
                    st.write("🔍 Fetching Problem Statement...")
                    st.text(text)  # Debugging output
                    solution = solve_with_gemini(pid, lang, text)
                    st.code(solution, language=lang)
            else:
                st.error("❌ Invalid problem number.")
        else:
            st.error("❌ Use format: Solve LeetCode [problem number]")
    
    else:
        if model:
            try:
                response = model.generate_content(user_input)
                st.write(response.text.strip())
            except Exception as e:
                st.error(f"❌ Gemini AI Error: {e}")
        else:
            st.error("❌ AI Model not initialized.")

# --- UI Setup ---
if "user_input" not in st.session_state:
    st.session_state["user_input"] = ""

st.text_input("Your command or question:", key="user_input", on_change=handle_input)
