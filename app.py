import os, csv
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter

from flask import Flask, render_template, request, send_file
import pandas as pd
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors as rl_colors

Seat = Tuple[int, int]   # a seat is (row, col)

app = Flask(__name__)
UPLOADS = "uploads"
os.makedirs(UPLOADS, exist_ok=True)

# ----------------------------
# Multiple halls
# ----------------------------
HALLS = {
    "Hall-1": {"rows": 5, "cols": 6},   # 30 seats
    "Hall-2": {"rows": 6, "cols": 6},   # 36 seats
    "Hall-3": {"rows": 4, "cols": 10},  # 40 seats
    "Hall-4": {"rows": 6, "cols": 8},   # 48 seats
    "Hall-5": {"rows": 5, "cols": 8},   # 40 seats
    "Hall-6": {"rows": 5, "cols": 10},  # 50 seats
    "Hall-7": {"rows": 6, "cols": 10},  # 60 seats
    "Hall-8": {"rows": 4, "cols": 12},  # 48 seats
    "Hall-9": {"rows": 6, "cols": 12},  # 72 seats
    "Hall-10": {"rows": 5, "cols": 12}, # 60 seats
    "Hall-11": {"rows": 7, "cols": 10}, # 70 seats
    "Hall-12": {"rows": 8, "cols": 10}, # 80 seats
}

# memory store
last_plans: Dict[str, dict] = {}
last_colors: Dict[str, str] = {}
last_subjects: List[str] = []

# ----------------------------
# Helpers
# ----------------------------
def hex_to_rl(hex_color: str):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255
    return rl_colors.Color(r, g, b)

def read_students(path):
    students = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            students.append({"id": row["id"], "name": row["name"], "subject": row["subject"]})
    return students

# ----------------------------
# Seating Algorithm (Greedy)
# ----------------------------
def build_grid_graph(rows: int, cols: int) -> Dict[Seat, List[Seat]]:
    adj = {(r, c): [] for r in range(rows) for c in range(cols)}
    for r in range(rows):
        for c in range(cols):
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    adj[(r, c)].append((nr, nc))
    return adj

def greedy_assign(adj: Dict[Seat, List[Seat]], subject_counts: Dict[str, int]) -> Dict[Seat, Optional[str]]:
    order = sorted(adj.keys(), key=lambda n: len(adj[n]), reverse=True)
    assignment, remaining = {}, subject_counts.copy()

    for node in order:
        neighbor_subjects = {assignment[n] for n in adj[node] if n in assignment}
        candidates = [s for s, c in remaining.items() if c > 0 and s not in neighbor_subjects]
        if not candidates:
            continue  # leave empty if no option
        best = max(candidates, key=lambda s: remaining[s])
        assignment[node] = best
        remaining[best] -= 1

    return assignment

def generate_seating(rows: int, cols: int, students: List[Dict[str, str]]):
    capacity, n = rows*cols, len(students)
    if n > capacity:
        return {}

    counts = Counter([s["subject"] for s in students])
    adj = build_grid_graph(rows, cols)
    assign = greedy_assign(adj, counts)

    pools = defaultdict(list)
    for s in students:
        pools[s["subject"]].append(s)
    for k in pools:
        pools[k].sort(key=lambda x: x["id"])

    seat_map, filled = {}, 0
    for seat in adj.keys():
        subj = assign.get(seat)
        if subj and pools[subj]:
            seat_map[seat] = pools[subj].pop(0)
            filled += 1
        else:
            seat_map[seat] = None

    subj_counts = Counter([s["subject"] for s in seat_map.values() if s])
    return {"seating": seat_map, "filled": filled, "capacity": capacity, "subj_counts": dict(subj_counts)}

# ----------------------------
# Routes
# ----------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", stage="upload")

@app.route("/prepare", methods=["POST"])
def prepare():
    file = request.files.get("file")
    if not file:
        return "Please upload a CSV with id,name,subject"

    csv_path = os.path.join(UPLOADS, "students.csv")
    file.save(csv_path)
    students = read_students(csv_path)
    if not students:
        return "CSV is empty!"

    subjects = sorted({s["subject"] for s in students})
    palette = ["#fca5a5","#93c5fd","#86efac","#fde68a","#f5d0fe",
               "#99f6e4","#c4b5fd","#fcd34d","#f9a8d4","#a7f3d0"]
    colors = {s: palette[i % len(palette)] for i, s in enumerate(subjects)}

    return render_template("index.html", stage="colors", subjects=subjects, colors=colors)

@app.route("/generate", methods=["POST"])
def generate():
    global last_plans, last_colors, last_subjects
    csv_path = os.path.join(UPLOADS, "students.csv")
    students = read_students(csv_path)
    subjects = sorted({s["subject"] for s in students})
    colors = {s: request.form.get(f"color_{s}", "#e5e7eb") for s in subjects}

    last_plans = {}
    start = 0
    for hall, cfg in HALLS.items():
        cap = cfg["rows"] * cfg["cols"]
        chunk = students[start:start+cap]
        if not chunk:
            break
        seating = generate_seating(cfg["rows"], cfg["cols"], chunk)
        last_plans[hall] = seating
        start += cap

    last_colors, last_subjects = colors, subjects
    return render_template(
        "index.html",
        stage="result",
        halls=HALLS,
        plans=last_plans,
        colors=colors,
        subjects=subjects,
        # global summary for the header chips
        global_filled=sum(d["filled"] for d in last_plans.values()),
        global_capacity=sum(cfg["rows"]*cfg["cols"] for h, cfg in HALLS.items() if h in last_plans),
        global_subjects=aggregate_subjects(last_plans)
    )

def aggregate_subjects(plans: Dict[str, dict]) -> Dict[str, int]:
    total = Counter()
    for data in plans.values():
        total.update(data.get("subj_counts", {}))
    return dict(total)

# ----------------------------
# Downloads
# ----------------------------
@app.route("/download/<fmt>")
def download(fmt):
    if not last_plans:
        return "No seating plan generated yet."

    if fmt == "csv":
        out = os.path.join(UPLOADS, "multi_seating.csv")
        rows = []
        for hall, data in last_plans.items():
            seating = data["seating"]
            for (r, c), stu in seating.items():
                rows.append({
                    "hall": hall, "row": r, "col": c,
                    "id": stu["id"] if stu else "",
                    "name": stu["name"] if stu else "",
                    "subject": stu["subject"] if stu else ""
                })
            # summary row
            rows.append({
                "hall": hall, "row": "", "col": "",
                "id": "", "name": f"Filled {data['filled']} / {data['capacity']}",
                "subject": ", ".join(f"{k}:{v}" for k, v in data["subj_counts"].items())
            })
        pd.DataFrame(rows).to_csv(out, index=False)
        return send_file(out, as_attachment=True)

    if fmt == "excel":
        out = os.path.join(UPLOADS, "multi_seating.xlsx")
        with pd.ExcelWriter(out) as writer:
            for hall, data in last_plans.items():
                seating = data["seating"]
                rows = [{
                    "row": r, "col": c,
                    "id": s["id"] if s else "",
                    "name": s["name"] if s else "",
                    "subject": s["subject"] if s else ""
                } for (r, c), s in seating.items()]
                df = pd.DataFrame(rows)
                df.loc[len(df)] = {
                    "row": "", "col": "", "id": "",
                    "name": f"Filled {data['filled']} / {data['capacity']}",
                    "subject": ", ".join(f"{k}:{v}" for k, v in data["subj_counts"].items())
                }
                df.to_excel(writer, sheet_name=hall, index=False)
        return send_file(out, as_attachment=True)

    from reportlab.lib.pagesizes import landscape, letter



    if fmt == "pdf":
        pdf_path = os.path.join(UPLOADS, "multi_seating.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter))
        story = []
        styles = getSampleStyleSheet()

        for hall, cfg in HALLS.items():
            data = last_plans.get(hall)
            if not data:
                continue
            seating = data["seating"]

            # Heading
            story.append(Paragraph(
                f"<b>{hall} ({cfg['rows']} × {cfg['cols']}) — "
                f"Filled {data['filled']} / {data['capacity']}</b>",
                styles["Heading2"]))
            story.append(Paragraph(
                ", ".join(f"{k}: {v}" for k, v in data["subj_counts"].items()),
                styles["Normal"]))
            story.append(Spacer(1, 12))

            # Table data
            table_data = []
            for r in range(cfg["rows"]):
                row = []
                for c in range(cfg["cols"]):
                    s = seating.get((r, c))
                    if s:
                        row.append(f"{s['id']}\n{s['name']}\n{s['subject']}")
                    else:
                        row.append("Empty")
                table_data.append(row)

            # 👉 Fit table to page width
            page_width, _ = landscape(letter)
            col_width = page_width / cfg["cols"]
            table = Table(table_data, colWidths=[col_width] * cfg["cols"])

            styles_tbl = [
                ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]

            for r in range(cfg["rows"]):
                for c in range(cfg["cols"]):
                    s = seating.get((r, c))
                    if s:
                        col = hex_to_rl(last_colors.get(s["subject"], "#e5e7eb"))
                        styles_tbl.append(("BACKGROUND", (c, r), (c, r), col))

            table.setStyle(TableStyle(styles_tbl))

            story.append(table)
            story.append(Spacer(1, 24))

        doc.build(story)
        return send_file(pdf_path, as_attachment=True)

    return "Invalid format"



if __name__ == "__main__":
    app.run(debug=True)
