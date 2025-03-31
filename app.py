import os
import time
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

app = Flask(__name__)

# --- 🔐 API Key Setup ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("❌ API key is missing. Set GEMINI_API_KEY as an environment variable.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# --- 🌐 Fetch Problems ---
def fetch_problems():
    res = requests.get("https://leetcode.com/api/problems/all/")
    if res.status_code == 200:
        data = res.json()
        return {str(p["stat"]["frontend_question_id"]): p["stat"]["question__title_slug"]
                for p in data["stat_status_pairs"]}
    return {}

problems_dict = fetch_problems()

def get_slug(pid):
    return problems_dict.get(pid)

def get_problem_statement(slug):
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
    if text.startswith("❌"):
        return "❌ Problem fetch failed."
    
    prompt = f"""Solve the following LeetCode problem in {lang}:
Problem:  
{text}
Requirements:
- Follow the LeetCode function signature.
- Return only the full function implementation.
- Do NOT use code fences.
Solution:"""
    
    res = model.generate_content(prompt)
    return res.text.strip()

# --- 🌍 Selenium Automation ---
def submit_solution(pid, lang, solution):
    slug = get_slug(pid)
    if not slug:
        return {"error": "Invalid problem number."}

    url = f"https://leetcode.com/problems/{slug}/"

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        time.sleep(5)

        # Locate the code editor & clear existing code
        editor = driver.find_element(By.CLASS_NAME, "monaco-editor")  # Adjust selector if needed
        editor.send_keys(Keys.CONTROL + "a")
        editor.send_keys(Keys.BACKSPACE)

        # Paste solution
        editor.send_keys(solution)
        time.sleep(2)

        # Click "Run"
        run_button = driver.find_element(By.XPATH, "//button[contains(text(),'Run')]")
        run_button.click()
        time.sleep(10)

        # Click "Submit"
        submit_button = driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]")
        submit_button.click()
        time.sleep(15)

        return {"status": "Success", "message": f"Problem {pid} submitted successfully!"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.quit()

# --- API Routes ---
@app.route("/solve", methods=["POST"])
def solve():
    data = request.json
    pid = data.get("problem_id")
    lang = data.get("language", "python")

    slug = get_slug(pid)
    if not slug:
        return jsonify({"error": "Invalid problem number."})

    text = get_problem_statement(slug)
    solution = solve_with_gemini(pid, lang, text)

    return jsonify({"problem_id": pid, "solution": solution})

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    pid = data.get("problem_id")
    lang = data.get("language", "python")
    solution = data.get("solution")

    result = submit_solution(pid, lang, solution)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
