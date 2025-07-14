# scraper/__init__.py
# Leave empty or use to import core functions later

# scraper/config.py
import logging
import sqlite3
from datetime import datetime

DB_PATH = "database/scholarships.db"
CSV_PATH = "database/scholarships.csv"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scholarship_scraper.log'),
        logging.StreamHandler()
    ]
)

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")


# scraper/models.py
from dataclasses import dataclass

@dataclass
class Scholarship:
    title: str
    description: str
    field_of_study: str
    category: str
    min_cgpa: str
    max_income: str
    minority_preference: str
    disability_preference: str
    army_preference: str
    application_url: str
    reference_website: str
    source: str
    scraped_date: str


# scraper/database.py
import sqlite3
import csv
from typing import List, Dict
from scraper.config import DB_PATH, CSV_PATH
from scraper.models import Scholarship
import logging


def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scholarships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            field_of_study TEXT,
            category TEXT,
            min_cgpa TEXT,
            max_income TEXT,
            minority_preference TEXT,
            disability_preference TEXT,
            army_preference TEXT,
            application_url TEXT,
            reference_website TEXT,
            source TEXT,
            scraped_date TEXT,
            UNIQUE(title, source)
        )
    ''')
    conn.commit()
    conn.close()


def save_to_database(scholarships: List[Scholarship]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for scholarship in scholarships:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO scholarships 
                (title, description, field_of_study, category, min_cgpa, max_income, 
                 minority_preference, disability_preference, army_preference, 
                 application_url, reference_website, source, scraped_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(vars(scholarship).values()))
        except sqlite3.IntegrityError:
            logging.warning(f"Duplicate entry: {scholarship.title}")
    conn.commit()
    conn.close()


def export_to_csv():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scholarships")
    scholarships = cursor.fetchall()
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'Description', 'Field of Study', 'Category', 'Min CGPA', 
                         'Max Income', 'Minority Preference', 'Disability Preference', 
                         'Army Preference'])
        for row in scholarships:
            writer.writerow(row[1:10])
    conn.close()
    logging.info(f"Exported {len(scholarships)} records to {CSV_PATH}")


def query_scholarships_by_criteria(field=None, category=None, min_cgpa=None,
                                    minority_preference=None, disability_preference=None, army_preference=None) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT * FROM scholarships WHERE 1=1"
    params = []
    if field:
        query += " AND field_of_study LIKE ?"
        params.append(f"%{field}%")
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    if min_cgpa:
        query += " AND CAST(min_cgpa AS REAL) <= ?"
        params.append(min_cgpa)
    if minority_preference:
        query += " AND minority_preference = ?"
        params.append(minority_preference)
    if disability_preference:
        query += " AND disability_preference = ?"
        params.append(disability_preference)
    if army_preference:
        query += " AND army_preference = ?"
        params.append(army_preference)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


# run_scraper.py
from scraper.database import setup_database, save_to_database, export_to_csv, query_scholarships_by_criteria
from scraper.scrapers import MasterScraper

if __name__ == "__main__":
    setup_database()
    master = MasterScraper()
    all_scholarships = master.run_all_scrapers(max_pages=2)
    save_to_database(all_scholarships)
    export_to_csv()
    print("Scraping and export completed.")
