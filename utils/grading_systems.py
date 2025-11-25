#!/usr/bin/env python3
import math
from dataclasses import dataclass
from typing import Optional, Dict, Tuple


@dataclass
class GradeScale:

    direction: str
    best_grade: float
    pass_grade: float


_COUNTRY_ALIASES: Dict[str, str] = {

    "germany": "germany",
    "bundesrepublik deutschland": "germany",
    "deutschland": "germany",


    "austria": "austria",
    "österreich": "austria",
    "oesterreich": "austria",


    "switzerland": "switzerland",
    "schweiz": "switzerland",
    "suisse": "switzerland",


    "united kingdom": "united kingdom",
    "uk": "united kingdom",
    "vereinigtes königreich": "united kingdom",
    "vereinigtes koenigreich": "united kingdom",
    "england": "united kingdom",
    "scotland": "united kingdom",
    "wales": "united kingdom",
    "northern ireland": "united kingdom",


    "united states": "united states",
    "united states of america": "united states",
    "usa": "united states",
    "u.s.a.": "united states",
    "canada": "canada",


    "turkey": "turkey",
    "türkei": "turkey",
    "tuerkei": "turkey",


    "india": "india",


    "italy": "italy",
    "italien": "italy",


    "france": "france",
    "frankreich": "france",


    "spain": "spain",
    "spanien": "spain",

    "netherlands": "netherlands",
    "niederlande": "netherlands",
    "the netherlands": "netherlands",

    "belgium": "belgium",
    "belgien": "belgium",


    "china": "china",
    "pr china": "china",
    "people's republic of china": "china",
    "peoples republic of china": "china",

}


def normalize_country_name(raw: str) -> Optional[str]:
    if not raw:
        return None
    key = raw.strip().lower()
    return _COUNTRY_ALIASES.get(key, None)


_COUNTRY_SCALES: Dict[str, GradeScale] = {

    "germany": GradeScale(direction="descending", best_grade=1.0, pass_grade=4.0),


    "austria": GradeScale(direction="descending", best_grade=1.0, pass_grade=4.0),
    "switzerland": GradeScale(direction="ascending", best_grade=6.0, pass_grade=4.0),

    "united kingdom": GradeScale(direction="ascending", best_grade=100.0, pass_grade=40.0),


    "united states": GradeScale(direction="ascending", best_grade=4.0, pass_grade=2.0),
    "canada": GradeScale(direction="ascending", best_grade=4.0, pass_grade=2.0),


    "turkey": GradeScale(direction="ascending", best_grade=4.0, pass_grade=2.0),

    "india": GradeScale(direction="ascending", best_grade=100.0, pass_grade=40.0),
    "italy": GradeScale(direction="ascending", best_grade=30.0, pass_grade=18.0),

    "france": GradeScale(direction="ascending", best_grade=20.0, pass_grade=10.0),

    "spain": GradeScale(direction="ascending", best_grade=10.0, pass_grade=5.0),


    "netherlands": GradeScale(direction="ascending", best_grade=10.0, pass_grade=5.5),

    "belgium": GradeScale(direction="ascending", best_grade=20.0, pass_grade=10.0),

    "china": GradeScale(direction="ascending", best_grade=100.0, pass_grade=60.0),

    "poland": GradeScale(direction="ascending", best_grade=5.0, pass_grade=3.0),
    "portugal": GradeScale(direction="ascending", best_grade=20.0, pass_grade=10.0),
    "brazil": GradeScale(direction="ascending", best_grade=10.0, pass_grade=5.0),
    "russia": GradeScale(direction="ascending", best_grade=5.0, pass_grade=3.0),
}


def get_country_scale(country_name: str) -> Optional[GradeScale]:

    if not country_name:
        return None
    norm = normalize_country_name(country_name)
    if norm is None:
        return None
    return _COUNTRY_SCALES.get(norm)


def convert_to_german(country_name: str, foreign_grade: float) -> Optional[float]:

    scale = get_country_scale(country_name)
    if scale is None:
        return None

    g = float(foreign_grade)
    best = scale.best_grade
    pass_grade = scale.pass_grade

    low = min(best, pass_grade) - 5.0
    high = max(best, pass_grade) + 5.0
    if g < low or g > high:
        return None

    try:
        if scale.direction == "descending":

            denom = (pass_grade - best)
            if abs(denom) < 1e-6:
                return None
            raw_german = 1.0 + 3.0 * (g - best) / denom
        else:

            denom = (best - pass_grade)
            if abs(denom) < 1e-6:
                return None
            raw_german = 1.0 + 3.0 * (best - g) / denom
    except Exception:
        return None

    if math.isnan(raw_german) or math.isinf(raw_german):
        return None
    if raw_german < 1.0 - 1e-6 or raw_german > 4.0 + 1e-6:
        return None

    german = max(1.0, min(4.0, raw_german))
    return round(german, 2)


def verify_grade(
    country_name: str,
    foreign_grade: float,
    claimed_german_grade: float,
    tolerance: float = 0.2,
) -> Tuple[Optional[bool], Optional[float], str]:

    if claimed_german_grade is None:
        return None, None, "NoClaimedGrade"

    converted = convert_to_german(country_name, foreign_grade)
    if converted is None:
        return None, None, "NoScaleOrInvalidForeign"

    converted = max(1.0, min(4.0, float(converted)))

    diff = abs(converted - float(claimed_german_grade))
    if diff <= tolerance:
        return True, converted, "OK"
    else:

        return False, converted, "BavarianMismatch"
