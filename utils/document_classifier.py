#!/usr/bin/env python3
import os
import re
import logging
import tqdm
from typing import Dict, List, Tuple

# Import the centralized OCR logic
from .ocr_ects import ocr_text_from_pdf
from .ocr_engine import normalize_text

TRANSCRIPT_KEYWORDS = [
    "transcript of records", "transcript of academic record", "grade report",
    "leistungsübersicht", "notenübersicht", "notenspiegel", "leistungsnachweis",
    "official transcript", "academic transcript", "student transcript",
    "unofficial transcript", "university transcript", "course transcript",
    "academic record", "record of study", "record of academic work",
    "course history", "study history", "study record", "marksheet",
    "mark sheet", "marks sheet", "statement of marks", "statement of results",
    "grade history", "performance report", "performance transcript",
]
ECTS_KEYWORDS = ["ects", "leistungspunkte", "credits", "credit points", "cp "]
SEMESTER_RE = re.compile(r"(wise|sose|wintersemester|sommersemester|ws ?20|ss ?20)")
LINE_WITH_DIGIT_RE = re.compile(r"^.*\d.*$", re.MULTILINE)

def score_transcript(text_low: str) -> int:
    score = 0
    
    if any(kw in text_low for kw in TRANSCRIPT_KEYWORDS):
        score += 4

    if any(kw in text_low for kw in ECTS_KEYWORDS):
        score += 3

    if len(SEMESTER_RE.findall(text_low)) >= 2:
        score += 2

    # Heuristic: Transcripts usually have many lines with numbers (grades/credits)
    numeric_line_count = len(LINE_WITH_DIGIT_RE.findall(text_low))
    
    if numeric_line_count > 20:
        score += 1

    return score

GERMAN_CERT_KEYWORDS = [
    "dsh-2", "dsh-3", "testdaf", "goethe-zertifikat c2",
    "zentrale oberstufenpruefung", "zentrale oberstufenprüfung",
    "deutsches sprachdiplom", "telc deutsch c1 hochschule",
    "österreichisches sprachdiplom", "oesd c2",
    "österreichische sprachdiplom c2",
]

# Generic terms that indicate a language exam took place, but aren't specific certificates
GERMAN_GENERIC_KEYWORDS = ("sprachprüfung", "language exam")
ENGLISH_CERT_KEYWORDS = [
    "toefl", "test of english as a foreign language", "ielts",
    "cambridge english", "b2 first", "first certificate",
    "linguaskill", "language test report form", "english language test",
]
ENGLISH_GENERIC_KEYWORDS = ("overall band", "overall score")

def score_language_cert(text_low: str, program: str) -> int:
    score = 0
    prog = program.lower()

    if prog == "bwl":
        if any(kw in text_low for kw in GERMAN_CERT_KEYWORDS):
            score += 5
        if any(kw in text_low for kw in GERMAN_GENERIC_KEYWORDS):
            score += 2

    elif prog == "ai":
        if any(kw in text_low for kw in ENGLISH_CERT_KEYWORDS):
            score += 5
        if any(kw in text_low for kw in ENGLISH_GENERIC_KEYWORDS):
            score += 2

    return score


DEGREE_RE = re.compile(
    r"""
    bachelorzeugnis|zeugnis|urkunde|diploma|baccalaureate|
    bachelor\s+of|                 # Covers Arts, Science, Eng, etc.
    \bdegree(?:\s+certificate)?|   # Matches "degree" or "degree certificate"
    this\s+is\s+to\s+certify\s+that|
    has\s+been\s+awarded\s+the\s+degree
    """,
    re.IGNORECASE | re.VERBOSE
)
GRADE_RE = re.compile(
    r"gesamtnote|abschlussnote|overall\s+grade", 
    re.IGNORECASE
)
TRANSCRIPT_RE = re.compile(
    r"\b(?:transcript|ects|credits|cp)\b", 
    re.IGNORECASE
)

def score_degree_certificate(text: str) -> int:
    score = 0
    if DEGREE_RE.search(text):
        score += 4
    if GRADE_RE.search(text):
        score += 2
    if not TRANSCRIPT_RE.search(text):
        score += 1
    return score


VPD_KEYWORD_RE = re.compile(
    r"vorpr(?:ü|ue)fungsdokumentation|vpd|uni[- ]assist",
    re.IGNORECASE
)
VPD_CONTENT_RE = re.compile(
    r"(?=.*bewertung)(?=.*ausländischer\s+hochschulabschluss)",
    re.IGNORECASE | re.DOTALL
)

def score_vpd(text: str) -> int:
    score = 0
    # 1. Check strong VPD keywords (OR logic)
    if VPD_KEYWORD_RE.search(text):
        score += 6
    # 2. Check for specific phrase combination (AND logic)
    if VPD_CONTENT_RE.search(text):
        score += 2
    return score


def classify_document(pdf_path: str, program: str) -> Tuple[str, Dict[str, int]]:
    logging.debug(f"Classifying: {os.path.basename(pdf_path)}")
    
    # -------------------------------------------------------------
    # OPTIMIZATION: Only OCR the first page for classification
    # -------------------------------------------------------------
    text = ocr_text_from_pdf(pdf_path, max_pages=1)
    
    if not text.strip():
        return "other", {"transcript": 0, "language_certificate": 0, "degree_certificate": 0, "vpd": 0}

    text_low = text.lower()
    #text_norm = normalize_text(text) # unused!

    scores = {
        "transcript": score_transcript(text_low),
        "language_certificate": score_language_cert(text_low, program),
        "degree_certificate": score_degree_certificate(text),
        "vpd": score_vpd(text)
    }

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Threshold: If the best match is weak, call it 'other'
    doc_type = best_type if best_score >= 2 else "other"
    
    return doc_type, scores


def classify_many(pdf_paths: List[str], program: str):
    by_type = {
        "transcript": [],
        "language_certificate": [],
        "degree_certificate": [],
        "vpd": [],
        "other": [],
    }
    
    best_transcript = (None, None)
    best_transcript_score = -1

    for pdf_path in tqdm.tqdm(pdf_paths, desc="Classifying attached documents...", leave=False):
        doc_type, scores = classify_document(pdf_path, program)
        by_type.setdefault(doc_type, []).append(pdf_path)
        
        # Track the 'strongest' transcript candidate
        if doc_type == "transcript":
            sc = scores.get("transcript", 0)
            if sc > best_transcript_score:
                best_transcript_score = sc
                best_transcript = (pdf_path, scores)

    return {
        "by_type": by_type,
        "best_transcript": best_transcript,
    }
