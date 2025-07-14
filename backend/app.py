from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import csv
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
import os
from typing import List, Dict, Any

# --- CONFIG ---
SENDER_EMAIL = "iammdnaumanatharhasan@gmail.com"
SENDER_PASSWORD = "jfnf pgtt glpx wuqr"

app = FastAPI(title="ScholarSphere API", version="1.1.0")

# --- STUDENT CLASS ---
class Student:
    def __init__(self, data: dict):
        self.name = data.get("name", "")
        self.dob = data.get("dob", "")
        self.gender = data.get("gender", "")
        self.email = data.get("email", "")
        self.phone = data.get("phone", "")
        self.category = data.get("category", "").lower()
        self.field_of_study = data.get("field_of_study", "").lower()

        self.year_of_graduation = int(data.get("year_of_graduation", 0))
        self.current_semester = int(data.get("current_semester", 0))
        self.college_name = data.get("college_name", "")
        self.cgpa = float(data.get("cgpa", 0))
        self.family_income = int(data.get("family_income", 0))
        self.last_year_cgpa = float(data.get("last_year_cgpa", 0))

        self.army_background = self._convert_to_bool(data.get("army_background", False))
        self.disability_status = self._convert_to_bool(data.get("disability_status", False))
        self.minority_status = self._convert_to_bool(data.get("minority_status", False))

    def _convert_to_bool(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes']
        return bool(value)

    def match_score(self, scholarship: dict) -> int:
        score = 0
        try:
            min_gpa = float(scholarship.get("Minimum GPA", 0))
            if self.cgpa >= min_gpa:
                score += 3
        except:
            pass

        try:
            max_income = int(scholarship.get("Maximum Family Income", 1e9))
            if self.family_income <= max_income:
                score += 3
        except:
            pass

        field = scholarship.get("Field of Study", "").lower()
        if self.field_of_study == field or field == "any":
            score += 2

        category = scholarship.get("Special Categories", "").lower()
        if self.category in category:
            score += 1

        if self.minority_status and scholarship.get("Special Categories", "").lower().find("minority") != -1:
            score += 1
        if self.disability_status and scholarship.get("Special Categories", "").lower().find("disability") != -1:
            score += 1
        if self.army_background and scholarship.get("Special Categories", "").lower().find("army") != -1:
            score += 1

        return score

# --- UTILITY FUNCTIONS ---
def save_student(data: dict) -> None:
    file_exists = os.path.isfile("/Users/cix9ine/Python/Projects/scholarsphere/database/students.csv")
    with open("/Users/cix9ine/Python/Projects/scholarsphere/database/students.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

def load_scholarships() -> List[Dict[str, Any]]:
    if not os.path.exists("/Users/cix9ine/Python/Projects/scholarsphere/database/scholarships.csv"):
        return []
    with open("/Users/cix9ine/Python/Projects/scholarsphere/database/scholarships.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def generate_pdf(student_name: str, scholarships: List[Dict[str, Any]], output_path: str = "student_scholarships.pdf") -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, f"Top Scholarships for {student_name}", ln=True, align="C")
    pdf.ln(10)

    if not scholarships:
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, "No matching scholarships found.", ln=True, align="C")
    else:
        for i, sch in enumerate(scholarships, 1):
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(200, 10, f"{i}. {sch.get('Title', 'N/A')}", ln=True)

            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 6, f"Description: {sch.get('Description', '')}")
            pdf.cell(0, 6, f"Amount: {sch.get('Amount', 'N/A')}", ln=True)
            pdf.cell(0, 6, f"Deadline: {sch.get('Deadline', 'N/A')}", ln=True)
            pdf.cell(0, 6, f"Application URL: {sch.get('Application URL', 'N/A')}", ln=True)
            pdf.ln(5)

    pdf.output(output_path)

def send_email_with_pdf(recipient_email: str, student_name: str, pdf_path: str) -> None:
    subject = "Your Top Scholarship Matches"
    body = f"""Hi {student_name},\n\nAttached is your personalized list of scholarship recommendations.\n\nBest,\nScholarSphere Team"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg.set_content(body)

    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=f"{student_name}_scholarships.pdf"
            )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
        smtp.send_message(msg)

# --- API ROUTES ---
@app.post("/submit")
async def submit(request: Request):
    user_data = await request.json()
    if not user_data.get("name") or not user_data.get("email"):
        raise HTTPException(status_code=400, detail="Missing required fields")

    save_student(user_data)
    student = Student(user_data)
    scholarships = load_scholarships()

    scored = []
    for sch in scholarships:
        score = student.match_score(sch)
        if score > 0:
            sch["match_score"] = score
            scored.append(sch)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    top5 = scored[:5]

    return JSONResponse({
        "message": "Top 5 scholarships found",
        "student_name": student.name,
        "recommendations": top5
    })

@app.post("/send-pdf")
async def send_pdf(request: Request):
    data = await request.json()
    email = data.get("email")
    name = data.get("name") or "Student"
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    scholarships = load_scholarships()
    student = Student(data)
    matched = [s for s in scholarships if student.match_score(s) > 0]
    matched.sort(key=lambda x: student.match_score(x), reverse=True)
    top10 = matched[:10]

    generate_pdf(student.name, top10)
    send_email_with_pdf(email, student.name, "student_scholarships.pdf")
    return {"message": f"PDF sent to {email}"}