import os, csv
from flask import Flask, render_template, request, send_file, redirect
from collections import Counter
from algo import generate_seating, auto_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

app = Flask(__name__)

UPLOADS = "uploads"
os.makedirs(UPLOADS, exist_ok=True)

last_result = {}
last_colors = {}
last_overflow = 0


# ------------------ READ STUDENTS ------------------
def read_students(path):
    students = []
    auto_counter = 1

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if not {"id", "name", "subject"}.issubset(reader.fieldnames):
            raise ValueError("CSV must contain id, name, and subject columns")

        for row in reader:
            if not row.get("id") or not row.get("name") or not row.get("subject"):
                continue

            roll = row.get("roll_no", "").strip()
            if not roll:
                roll = f"Roll_No{auto_counter:03d}"
                auto_counter += 1

            students.append({
                "id": row["id"].strip(),
                "name": row["name"].strip(),
                "subject": row["subject"].strip(),
                "roll_no": roll
            })

    if not students:
        raise ValueError("No valid student records found in CSV")

    return students

# ------------------ ROUTES ------------------
@app.route("/")
def home():
    return render_template("index.html", stage="upload")

@app.route("/prepare", methods=["POST"])
def prepare():
    try:
        if "file" in request.files:
            file = request.files["file"]
            path = os.path.join(UPLOADS, "students.csv")
            file.save(path)

        students = read_students(os.path.join(UPLOADS, "students.csv"))

    except Exception as e:
        return render_template(
            "index.html",
            stage="upload",
            error=str(e)
        )

    subjects = sorted({s["subject"] for s in students})
    colors = auto_colors(subjects)

    return render_template(
        "index.html",
        stage="colors",
        subjects=subjects,
        colors=colors,
        student_count=len(students)
    )



@app.route("/generate", methods=["POST"])
@app.route("/generate", methods=["POST"])
def generate():
    global last_result, last_colors, last_overflow

    try:
        # ---------------- READ STUDENTS ----------------
        students = read_students(os.path.join(UPLOADS, "students.csv"))

        # ---------------- READ HALL DATA ----------------
        hall_names = request.form.getlist("hall_name[]")
        rows_list = request.form.getlist("rows[]")
        cols_list = request.form.getlist("cols[]")

        if not hall_names:
            raise ValueError("Please add at least one examination hall.")

        HALLS = {}
        halls_list = []

        for name, r, c in zip(hall_names, rows_list, cols_list):
            r, c = int(r), int(c)
            if r <= 0 or c <= 0:
                raise ValueError("Hall rows and columns must be positive numbers.")

            HALLS[name] = (r, c)
            halls_list.append((r, c))

        # ---------------- SEATING ALGORITHM ----------------
        # generate_seating returns:
        # seat_map -> dict[(hall_id, row, col)] = student
        # hall_data -> unused
        # unseated -> INT (remaining students)
        seat_map, _, unseated = generate_seating(halls_list, students)

        last_overflow = unseated  # IMPORTANT: already an int

        # ---------------- SUBJECT COLORS ----------------
        colors_map = {}
        for s in students:
            colors_map[s["subject"]] = request.form.get(
                f"color_{s['subject']}", "#e5e7eb"
            )
        last_colors = colors_map

        # ---------------- BUILD HALL PLANS ----------------
        plans = {}
        subject_totals = Counter()

        for hid, (hall, (rows, cols)) in enumerate(HALLS.items(), start=1):
            seating = {}
            filled = 0
            hall_subjects = Counter()

            for r in range(rows):
                for c in range(cols):
                    s = seat_map.get((hid, r, c))
                    if s:
                        seat_label = f"R{r+1}C{c+1}"

                        seating[(r, c)] = {
                            **s,
                            "seat": seat_label
                        }

                        filled += 1
                        hall_subjects[s["subject"]] += 1
                        subject_totals[s["subject"]] += 1

            plans[hall] = {
                "rows": rows,
                "cols": cols,
                "seating": seating,
                "filled": filled,
                "capacity": rows * cols,
                "subjects": dict(hall_subjects)
            }

        last_result = plans

        # ---------------- RENDER RESULT ----------------
        return render_template(
            "index.html",
            stage="result",
            halls=HALLS,
            plans=plans,
            colors=colors_map,
            global_filled=sum(p["filled"] for p in plans.values()),
            global_capacity=sum(r * c for r, c in HALLS.values()),
            overflow=last_overflow,
            has_overflow=last_overflow > 0
        )

    except Exception as e:
        # ---------------- USER-FRIENDLY ERROR ----------------
        return render_template(
            "index.html",
            stage="colors",
            error=str(e)
        )



# ------------------ DOWNLOAD CSV ------------------
@app.route("/download/csv")
def download_csv():
    path = os.path.join(UPLOADS, "seating.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Hall", "Row", "Col", "Roll No", "Name", "Subject"])
        for hall, data in last_result.items():
            for (r, c), s in data["seating"].items():
                w.writerow([hall, r, c, s["roll_no"], s["name"], s["subject"]])
    return send_file(path, as_attachment=True)


# ------------------ DOWNLOAD PDF ------------------
@app.route("/download/pdf")
def download_pdf():
    path = os.path.join(UPLOADS, "seating_layout.pdf")
    c = canvas.Canvas(path, pagesize=A4)

    width, height = A4
    margin_x = 40
    margin_y = height - 40

    seat_w = 70
    seat_h = 40
    gap = 6

    for hall, data in last_result.items():
        y = margin_y

        # -------- HALL TITLE --------
        c.setFont("Helvetica-Bold", 16)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(
            margin_x,
            y,
            f"{hall} ({data['filled']} / {data['capacity']})"
        )
        y -= 25

        # -------- SUBJECT SUMMARY --------
        c.setFont("Helvetica", 9)
        x = margin_x
        for subj, cnt in data["subjects"].items():
            c.setFillColor(HexColor(last_colors.get(subj, "#999999")))
            c.rect(x, y - 12, 90, 14, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            c.drawCentredString(x + 45, y - 10, f"{subj}: {cnt}")
            x += 95
            if x + 90 > width:
                x = margin_x
                y -= 16

        y -= 25

        # -------- SEATING GRID --------
        for r in range(data["rows"]):
            x = margin_x
            for c_idx in range(data["cols"]):
                seat = data["seating"].get((r, c_idx))

                if seat:
                    color_hex = last_colors.get(seat["subject"], "#E5E7EB")
                else:
                    color_hex = "#F3F4F6"

                c.setFillColor(HexColor(color_hex))
                c.rect(x, y - seat_h, seat_w, seat_h, fill=1, stroke=1)

                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica", 7)

                if seat:
                    c.drawCentredString(
                        x + seat_w / 2, y - 12, seat["seat"]
                    )
                    c.drawCentredString(
                        x + seat_w / 2, y - 22, seat["roll_no"]
                    )
                    c.drawCentredString(
                        x + seat_w / 2, y - 32, seat["subject"]
                    )
                else:
                    c.drawCentredString(
                        x + seat_w / 2, y - 20, f"R{r+1}C{c_idx+1}"
                    )

                x += seat_w + gap

            y -= seat_h + gap

            if y < 80:
                c.showPage()
                y = margin_y

        # -------- NEW PAGE PER HALL --------
        c.showPage()

    c.save()
    return send_file(path, as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True)
