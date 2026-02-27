from flask import Flask, render_template, request
import sqlite3
import json
import google.generativeai as genai
import re

app = Flask(__name__)

from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# 🔑 Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")


# 🔥 SMART PROMPT (Highly Optimized)
PROMPT = """
You are an expert AI trained to extract structured data from complex restaurant menu images.

Your job:
Extract ALL food items with correct prices.

STRICT RULES:
- Ignore restaurant name, logos, addresses
- Ignore headings unless they define category
- Understand multi-column layouts
- Items may be:
    • left of price
    • above price
    • below price
    • diagonally placed
- ALWAYS pair item with nearest LOWER price (not above)
- Ignore decorative text (chef special, spicy, etc.)
- If price is "MRP", keep it as "MRP"
- If multiple prices exist, choose the most relevant one
- Remove duplicates
- Fix OCR mistakes (e.g. Biryam → Biryani)
- Group items into categories if possible
- If category missing → use "Unknown"

OUTPUT FORMAT (STRICT JSON ONLY):
[
  {
    "category": "string",
    "item": "string",
    "price": "string"
  }
]

DO NOT RETURN ANY TEXT EXCEPT JSON.
"""


# 🧠 Clean JSON extractor
def clean_json(text):
    try:
        text = re.sub(r"```json|```", "", text)
        start = text.find("[")
        end = text.rfind("]") + 1
        return json.loads(text[start:end])
    except:
        return []


# 💾 Save to DB
def get_db_connection():
    db_type = os.getenv("DB_TYPE")  # mysql / postgres

    if db_type == "mysql":
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )

    elif db_type == "postgres":
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME")
        )

    else:
        raise Exception("❌ DB_TYPE not set properly")

    return conn


# 🧠 Gemini Processing (MULTI IMAGE)
def process_images(files):
    all_items = []

    for file in files:
        print(f"Processing: {file.filename}")

        image_bytes = file.read()

        response = model.generate_content([
            PROMPT,
            {"mime_type": file.content_type, "data": image_bytes}
        ])

        data = clean_json(response.text)

        all_items.extend(data)

    return all_items


# 🌐 Flask Route
@app.route("/", methods=["GET", "POST"])
def index():
    data = []

    if request.method == "POST":
        files = request.files.getlist("images")

        if files:
            extracted = process_images(files)
            data = save_to_db(extracted)

    return render_template("index.html", data=data)


# 🚀 Run
if __name__ == "__main__":
    app.run(debug=True)
