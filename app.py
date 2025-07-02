
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
CORS(app)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    content = file.read()
    ext = file.filename.split(".")[-1].lower()

    if ext == "html":
        soup = BeautifulSoup(content, "html.parser")
        # Example: Extract all answer rows from a div or table (customize as needed)
        table = soup.find("table")
        data = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 3:
                qid = cols[0].text.strip()
                correct = cols[1].text.strip()
                chosen = cols[2].text.strip()
                data.append({"qid": qid, "correct": correct, "chosen": chosen})
        return jsonify(data)

    elif ext == "pdf":
        doc = fitz.open(stream=content, filetype="pdf")
        text = "
".join([page.get_text() for page in doc])
        # Dummy parsing logic (improve for real format)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        data = []
        for line in lines:
            if "-" in line:
                parts = line.split("-")
                qid = parts[0].strip()
                correct = parts[1].strip().split()[0]
                chosen = parts[1].strip().split()[1] if len(parts[1].strip().split()) > 1 else "-"
                data.append({"qid": qid, "correct": correct, "chosen": chosen})
        return jsonify(data)

    else:
        return jsonify({"error": "Unsupported file type"}), 400

@app.route("/score", methods=["POST"])
def score():
    data = request.json
    name = data.get("name")
    answers = data.get("answers")
    correct_count = sum(1 for a in answers if a["correct"] == a["chosen"])
    wrong_count = sum(1 for a in answers if a["chosen"] and a["correct"] != a["chosen"])
    unattempted = sum(1 for a in answers if not a["chosen"] or a["chosen"] == "-")

    score = correct_count - wrong_count

    result = {
        "name": name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "score": score,
        "correct": correct_count,
        "wrong": wrong_count,
        "unattempted": unattempted
    }

    with open(f"/mnt/data/{name}_score.json", "w") as f:
        json.dump(result, f)

    return jsonify(result)

@app.route("/download_score", methods=["POST"])
def download_score():
    data = request.json
    name = data["name"]
    score_data = data["score_data"]

    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    c.drawString(100, 750, f"Name: {score_data['name']}")
    c.drawString(100, 730, f"Date: {score_data['date']}")
    c.drawString(100, 710, f"Score: {score_data['score']}")
    c.drawString(100, 690, f"Correct: {score_data['correct']}")
    c.drawString(100, 670, f"Wrong: {score_data['wrong']}")
    c.drawString(100, 650, f"Unattempted: {score_data['unattempted']}")
    c.save()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name=f"{name}_scorecard.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)
