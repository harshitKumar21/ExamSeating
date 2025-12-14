from collections import defaultdict, deque
from typing import Dict, List, Tuple

SeatKey = Tuple[int, int, int]  # (hall_id, row, col)

SUBJECT_ABBREVIATIONS = {
    "Biology": "B",
    "Chemistry": "C",
    "Civil Engineering": "CE",
    "Commerce": "CO",
    "Computer Science": "CS",
    "Electronics": "E",
    "Management": "M",
    "Mathematics": "MA",
    "Mechanical Engineering": "ME",
    "Physics": "P",
}

def abbr(subject: str) -> str:
    return SUBJECT_ABBREVIATIONS.get(subject, subject[:2].upper())

def make_roll(subject: str, year: int, idx: int) -> str:
    return f"{abbr(subject)}{year}{idx}"

def auto_colors(subjects):
    palette = [
        "#60a5fa", "#34d399", "#fbbf24", "#f472b6",
        "#a78bfa", "#fb7185", "#22d3ee", "#4ade80",
        "#e879f9", "#facc15"
    ]
    return {s: palette[i % len(palette)] for i, s in enumerate(subjects)}

def generate_seating(
    halls: List[Tuple[int, int]],
    students: List[Dict[str, str]],
):
    """
    Rules:
    - Fill halls sequentially
    - No same subject in adjacent rows
    - Columns fully usable
    """

    # Group students by subject
    groups = defaultdict(deque)
    for s in students:
        groups[s["subject"]].append(s)

    # Generate roll numbers
    for subj, q in groups.items():
        year = int(q[0].get("year", 1))
        for i, st in enumerate(q, 1):
            st.setdefault("roll_no", make_roll(subj, year, i))

    subjects = deque(sorted(groups.keys(), key=lambda s: len(groups[s]), reverse=True))

    seat_map: Dict[SeatKey, Dict] = {}
    hall_results = {}
    total_index = 0

    for hall_id, (rows, cols) in enumerate(halls, start=1):
        filled = 0
        prev_row_subjects = set()

        for r in range(rows):
            used_this_row = set()
            c = 0
            attempts = 0

            while c < cols and subjects:
                subj = subjects[0]

                if subj in prev_row_subjects or not groups[subj]:
                    subjects.rotate(-1)
                    attempts += 1
                    if attempts >= len(subjects):
                        break
                    continue

                student = groups[subj].popleft()
                seat_map[(hall_id, r, c)] = student
                filled += 1
                used_this_row.add(subj)
                c += 1
                attempts = 0

                if not groups[subj]:
                    subjects.popleft()
                else:
                    subjects.rotate(-1)

            prev_row_subjects = used_this_row

        hall_results[hall_id] = {
            "filled": filled,
            "capacity": rows * cols,
            "rows": rows,
            "cols": cols,
        }

        subjects = deque([s for s in subjects if groups[s]])

        if not subjects:
            break

    unseated = sum(len(v) for v in groups.values())

    return seat_map, hall_results, unseated
 