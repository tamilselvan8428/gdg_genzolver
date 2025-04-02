FROM python:3.10

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["streamlit", "run", "leetcode_auto_solver.py", "--server.port=8080", "--server.address=0.0.0.0"]
