import os
import streamlit as st
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup

# ✅ Load API Key safely
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ API Key not found. Set GEMINI_API_KEY as an environment variable and restart.")
    st.stop()

# ✅ Configure Gemini AI
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# ✅ Set Streamlit Page Configuration
st.set_page_config(page_title="GenZolver - LeetCode AI Solver", layout="centered")
st.title("🤖 Solve Problems with GenZolver")
st.write("Type 'Solve LeetCode [problem number]' or ask me anything!")

@st.cache_data
def fetch_problems():
    """Fetch all available LeetCode problems."""
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
st.write(f"📌 **Loaded LeetCode Problems:** {len(problems_dict)}")

def get_slug(pid): 
    """Get the problem slug from problem ID."""
    return problems_dict.get(pid)

def get_problem_statement(slug):
    """Fetch problem statement from LeetCode GraphQL API."""
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
        st.error(f"❌ GraphQL error: {e}")
    return None

def solve_with_gemini(lang, text):
    """Generate a solution using Gemini AI."""
    if not text:
        st.error("❌ Problem fetch failed. Cannot generate solution.")
        return None

    prompt = f"""Solve the following LeetCode problem in {lang}:
Problem:  
{text}
Requirements:
- Wrap the solution inside class Solution.
- Follow the LeetCode function signature.
- Return only the full class definition with the method inside.
- Do NOT use code fences.
Solution:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")
        return None

# ✅ User Input Handling
user_input = st.text_input("Your command or question:")

if user_input.lower().startswith("solve leetcode"):
    tokens = user_input.strip().split()
    if len(tokens) == 3 and tokens[2].isdigit():
        pid = tokens[2]
        slug = get_slug(pid)

        if slug:
            lang = st.selectbox("Choose Language", ["python", "cpp", "java", "javascript", "csharp"])
            if st.button("Generate Solution"):
                text = get_problem_statement(slug)
                if text:
                    solution = solve_with_gemini(lang, text)
                    if solution:
                        st.code(solution, language=lang)
                    else:
                        st.error("❌ Failed to generate solution.")
                else:
                    st.error("❌ Failed to fetch problem statement.")
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