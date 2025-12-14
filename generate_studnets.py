# generate_students_univ.py
import csv, random
from itertools import cycle

subjects = [
    "E&C Engineering",
    "CSE",
    "Civil Engineering",
    "Cyber Security",
    "BBA – Airport & Airline Mgmt",
    "Commerce",
    "Fashion Design",
    "Animation & Gaming",
    "Visual Arts",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Management (MBA)",
    "Computer Applications (BCA/B.Sc IT)"
]

total_students = 640  # enough to fill all halls (total 634 seats plus buffer)

with open("uploads/students.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "name", "subject"])
    cycle_subj = cycle(subjects)
    for i in range(1, total_students + 1):
        subj = next(cycle_subj)
        writer.writerow([
            f"S{i:04d}",
            f"Student_{i}",
            subj
        ])

print(f"Generated 'students.csv' with {total_students} entries in uploads/")
