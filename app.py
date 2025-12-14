import os, csv
from flask import Flask, render_template, request, send_file
from collections import Counter
from algo import generate_seating, auto_colors

app = Flask(__name__)
UPLOADS = "uploads"
os.makedirs(UPLOADS, exist_ok=True)

HALLS = {
    "Hall-1": (5, 6),
    "Hall-2": (6, 6),
    "Hall-3": (6, 8),
    "Hall-4": (6, 10),
    "Hall-5": (8, 10),
    "Hall-6": (10, 10),
}

last_result = {}

def read_students(path):
    students = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("id") and row.get("name") and row.get("subject"):
                students.append({
                    "id": row["id"].strip(),
                    "name": row["name"].strip(),
                    "subject": row["subject"].strip(),
                    "year": row.get("year", "1").strip(),
                    "roll_no": row.get("roll_no", "").strip()
                })
    return students

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", stage="upload")

@app.route("/prepare", methods=["POST"])
def prepare():
    file = request.files["file"]
    path = os.path.join(UPLOADS, "students.csv")
    file.save(path)

    students = read_students(path)
    subjects = sorted({s["subject"] for s in students})
    colors = auto_colors(subjects)

    return render_template("index.html",
        stage="colors",
        subjects=subjects,
        colors=colors
    )

@app.route("/generate", methods=["POST"])
def generate():
    global last_result

    students = read_students(os.path.join(UPLOADS, "students.csv"))
    halls_list = list(HALLS.values())

    seat_map, hall_data, unseated = generate_seating(halls_list, students)

    colors = {}
    for s in {st["subject"] for st in students}:
        colors[s] = request.form.get(f"color_{s}", "#e5e7eb")

    plans = {}
    subject_totals = Counter()

    for hid, cfg in enumerate(halls_list, start=1):
        rows, cols = cfg
        hall_name = f"Hall-{hid}"
        seating = {}
        filled = 0

        for r in range(rows):
            for c in range(cols):
                s = seat_map.get((hid, r, c))
                if s:
                    seating[(r, c)] = s
                    subject_totals[s["subject"]] += 1
                    filled += 1

        plans[hall_name] = {
            "seating": seating,
            "filled": filled,
            "capacity": rows * cols,
            "rows": rows,
            "cols": cols
        }

    last_result = plans

    return render_template(
        "index.html",
        stage="result",
        halls=HALLS,
        plans=plans,
        colors=colors,
        global_filled=sum(p["filled"] for p in plans.values()),
        global_capacity=sum(r*c for r,c in HALLS.values()),
        global_subjects=dict(subject_totals)
    )

@app.route("/download/csv")
def download_csv():
    path = os.path.join(UPLOADS, "seating.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Hall", "Row", "Col", "Roll", "Name", "Subject"])
        for hall, data in last_result.items():
            for (r,c), s in data["seating"].items():
                w.writerow([hall, r, c, s["roll_no"], s["name"], s["subject"]])
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
