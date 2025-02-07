from flask import Flask, render_template, request
import sqlite3
import google.generativeai as genai
import os
from datetime import datetime

app = Flask(__name__)

api = os.getenv('makersuite')
genai.configure(api_key = api)
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize the SQLite database
def init_db():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_history (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            weight REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_data (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            heart_rate INTEGER, 
            steps INTEGER, 
            calories INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_data (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            food_list TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Home - Health management main interface
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# ========= Weight Update & BMI Calculation =========

# Display the weight update form page
@app.route("/update_weight_form", methods=["GET"])
def update_weight_form():
    return render_template("update_weight.html")

# Handle weight update submission
@app.route("/update_weight", methods=["POST"])
def update_weight():
    weight = request.form.get("weight")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO weight_history (date, weight) VALUES (?, ?)", (date, weight))
    conn.commit()
    conn.close()

    return render_template("dashboard.html", message="Weight data updated!")

# ========= Sports data submission =========

# Display the sports data form page
@app.route("/submit_exercise_form", methods=["GET"])
def submit_exercise_form():
    return render_template("submit_exercise.html")

# Processing motion data submission
@app.route("/submit_exercise", methods=["POST"])
def submit_exercise():
    heart_rate = request.form.get("heart_rate")
    steps = request.form.get("steps")
    calories = request.form.get("calories")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exercise_data (date, heart_rate, steps, calories) VALUES (?, ?, ?, ?)", 
                   (date, heart_rate, steps, calories))
    conn.commit()
    conn.close()

    return render_template("dashboard.html", message="Sports data recorded!")

# ========= Diet data submission =========

# Display the diet data form page
@app.route("/submit_food_form", methods=["GET"])
def submit_food_form():
    return render_template("submit_food.html")

# Process dietary data submission & call genAI to calculate calories
@app.route("/submit_food", methods=["POST"])
def submit_food():
    food_list = request.form.get("food_list")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save to database
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO food_data (date, food_list) VALUES (?, ?)", (date, food_list))
    conn.commit()
    conn.close()

    # Call Gemini to calculate 
    prompt = f"Calculate the total calories and nutritional ratio (carbohydrate/protein/fat) of the following foods: {food_list}"
    
    response = model.generate_content(prompt)
    
    nutrition_result = response.text if response and response.text else "Unable to obtain nutritional analysis results"

    return render_template("dashboard.html", message="Diet data recorded!", nutrition_analysis=nutrition_result)

# ========= Generate health report ==========
@app.route("/generate_report", methods=["GET"])
def generate_report():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()

    cursor.execute("SELECT date, weight FROM weight_history ORDER BY date DESC LIMIT 7")
    weight_history = cursor.fetchall()

    cursor.execute("SELECT date, heart_rate, steps, calories FROM exercise_data ORDER BY date DESC LIMIT 7")
    exercise_data = cursor.fetchall()

    conn.close()


    prompt = (
        "Based on the user's last 7 days of weight and exercise data, provide a concise health summary with 3 key points:\n\n"
        "- **Weight Trend:** (one-sentence summary)\n"
        "- **Exercise Effect:** (one-sentence insight)\n"
        "- **Improvement Suggestion:** (one practical tip)\n"
        "Do NOT include general health advice—only insights derived from the data."
        f"\n\nWeight Data: {weight_history}\nExercise Data: {exercise_data}"
    )

    response = model.generate_content(prompt, generation_config={"max_tokens": 200})
    health_advice = response.text if response and response.text else "Unable to obtain health analysis."

    return render_template("health_report.html", 
                           weight_history=weight_history, 
                           exercise_data=exercise_data,
                           health_advice=health_advice)

    
if __name__ == "__main__":
    app.run(debug=True)