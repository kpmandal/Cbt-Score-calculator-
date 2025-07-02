from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
CORS(app)  # You may restrict origin here: CORS(app, resources={r"/*": {"origins": "https://your-frontend.com"}})

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    content = file.read()
    ext = file.filename.split(".")[-1].lower()

    if ext == "html":
        try:
            soup = BeautifulSoup(content, "html.parser")
            table = soup.find("table")
            if not table:
                return jsonify({"error": "No table found in HTML"}), 400

            data = []
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    qid = cols[0].text.strip()
                    correct = cols[1].text.strip()
                    chosen = cols[2].text.strip()
                    data.append({"qid": qid, "correct": correct, "chosen": chosen})
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": f"Error processing HTML: {str(e)}"}), 500

    elif ext == "pdf":
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            text = "\n".join([page.get_text() for page in doc])
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            data = []
            for line in lines:
                if "-" in line:
                    parts = line.split("-")
                    qid = parts[0].strip()
                    rest = parts[1].strip().split()
                    correct = rest[0]
                    chosen = rest[1] if len(rest) > 1 else "-"
                    data.append({"qid": qid, "correct": correct, "chosen": chosen})
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500

    else:
        return jsonify({"error": "Unsupported file type. Upload .html or .pdf"}), 400


@app.route("/score", methods=["POST"])
def score():
    data = request.json
    name = data.get("name", "anonymous")
    answers = data.get("answers", [])

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

    # Save to file
    filename = f"/mnt/data/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_score.json"
    with open(filename, "w") as f:
        json.dump(result, f, indent=2)

    return jsonify(result)


@app.route("/download_score", methods=["POST"])
def download_score():
    data = request.json
    name = data.get("name", "anonymous")
    score_data = data.get("score_data", {})

    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=letter)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, 780, "CBT Scorecard")

    c.setFont("Helvetica", 12)
    y = 740
    for label in ["Name", "Date", "Score", "Correct", "Wrong", "Unattempted"]:
        value = str(score_data.get(label.lower(), "-"))
        c.drawString(100, y, f"{label}: {value}")
        y -= 20

    c.save()
    output.seek(0)

    return send_file(output, as_attachment=True,
                     download_name=f"{name}_scorecard.pdf",
                     mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)