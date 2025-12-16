# 🎓 Exam Seating Arrangement System

A dynamic, constraint-based exam seating arrangement system built using **Flask**, designed to generate fair, organized, and printable seating plans for universities and colleges.

---

## 🚀 Features

- CSV-based student input
- Dynamic exam hall addition (any rows × columns)
- Automatic roll number generation (if missing)
- Seat numbering in **R1C1 format**
- Subject-wise color mapping
- Hall-wise subject count summary
- Overflow student handling
- CSV & PDF export
- **One hall per PDF page**
- Greedy constraint-based seating (fast & scalable)
- Clean, user-friendly UI (Tailwind CSS)

---

## 🛠 Tech Stack

- **Backend:** Python, Flask  
- **Frontend:** HTML, Tailwind CSS  
- **PDF Generation:** ReportLab  
- **Input Format:** CSV  
- **Version Control:** Git & GitHub  

---

## 📂 Project Structure-
  ExamSeating/
│
├── app.py # Flask backend
├── algo.py # Seating algorithm
├── requirements.txt # Dependencies
├── README.md
├── uploads/
│ └── .gitkeep
├── templates/
│ └── index.html
└── static/
How to Run Locally
1️⃣ Install dependencies
pip install -r requirements.txt

2️⃣ Run the application
python app.py

3️⃣ Open in browser
http://127.0.0.1:5000

🧠 Algorithm Overview

The system uses a greedy constraint-based algorithm inspired by graph coloring principles:

Each subject behaves like a color

Adjacent seating attempts to avoid same-subject clustering

Time Complexity: O(N)

Space Complexity: O(N)

Efficient and scalable for large datasets

📄 Output Details
Web Interface
Seat number in R1C1 format
Roll number
Subject name
Hall-wise subject distribution summary
PDF Export
One exam hall per page
Seat number, roll number, and subject printed
Subject summary bar at the top
Print-ready professional layout

##⚠ Error Handling & Validation
Invalid or empty CSV files are blocked
Missing required columns are detected
Invalid hall dimensions are prevented
Empty hall names are sanitized
Insufficient seating capacity is clearly reported
User-friendly error messages (no crashes)

##🎓 Use Cases
  Universities
  Colleges
  School examination departments

##📌 Future Enhancements
  Strict adjacency constraints (no same-subject neighbors)
  Landscape PDF layout for large halls
  Admin dashboard




