
from flask import Flask, request, jsonify
import requests, io
from bs4 import BeautifulSoup
import pdfplumber

app = Flask(__name__)

def parse_pdf(file_stream):
    answer_key = {}
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split("\n")
            for line in lines:
                if '-' in line:
                    parts = line.strip().split('-')
                    if len(parts) == 2:
                        q, a = parts
                        answer_key[q.strip()] = a.strip().upper()
    return answer_key

def parse_html_from_link(url):
    answer_key = {}
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    all_divs = soup.find_all('div')
    for div in all_divs:
        if div.text.strip().startswith("Q."):
            lines = div.text.split("\n")
            q_line = lines[0]
            q_no = q_line.split(".")[0].replace("Q", "").strip()
            for l in lines:
                if "✔" in l or "✓" in l:
                    correct_option = l.strip()[-1]  # last char is A/B/C/D
                    answer_key[q_no] = correct_option.upper()
    return answer_key

@app.route('/calculate', methods=['POST'])
def calculate():
    user_input = request.form.get("user_answers")
    key_link = request.form.get("key_link")
    file = request.files.get("pdf_file")

    if file:
        answer_key = parse_pdf(file.stream)
    elif key_link:
        answer_key = parse_html_from_link(key_link)
    else:
        return jsonify({'error': 'No input key provided'}), 400

    correct_answers = {str(k): v.upper() for k, v in answer_key.items()}
    score = 0
    details = []
    user_answers = {}

    for pair in user_input.replace('\n', ',').split(','):
        if '-' in pair:
            q, a = pair.strip().split('-')
            user_answers[q.strip()] = a.strip().upper()

    for q_no, correct in correct_answers.items():
        your = user_answers.get(q_no, '')
        if your == correct:
            status = 'Correct'
            score += 1
        elif your == '':
            status = 'Unattempted'
        else:
            status = 'Wrong'
            score -= 0.33
        details.append({'q': q_no, 'your': your, 'correct': correct, 'status': status})

    return jsonify({'score': round(score, 2), 'details': details})
