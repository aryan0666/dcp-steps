"""
load.py - Part 2 of "My Daily Steps" (DCP 2026, Human Made Data).

What this file does, in order:
  1. Reads data/steps.csv one row at a time.
  2. Checks and cleans every row. Bad values print a warning; the program
     never crashes on bad data.
  3. Creates a SQLite database (steps.db) with a table called "steps".
     The table is deleted and rebuilt every run, so rows are never duplicated.
  4. Inserts the rows that passed the checks.
  5. Runs SQL queries that help answer my three questions and prints them.

Run it from the terminal:
    python load.py                      (uses data/steps.csv)
    python load.py data/test_bad.csv    (any other CSV file)
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Settings and allowed values (kept in one place so they are easy to change)
# ---------------------------------------------------------------------------
CSV_PATH = "data/steps.csv"
DB_PATH = "steps.db"

COLUMNS = ["date", "time_recorded", "steps", "college_day",
           "transport", "minutes_outside", "energy", "weather"]

COLLEGE_DAY_VALUES = {"y", "n"}
# Note: "none" here is a real answer ("I didn't travel"), NOT a missing value.
TRANSPORT_VALUES = {"walk", "bus", "luas", "car", "none"}
WEATHER_VALUES = {"sunny", "cloudy", "rainy"}

STEPS_WARNING_LIMIT = 50_000   # above this is suspicious, but still possible


# ---------------------------------------------------------------------------
# Small helper functions
# ---------------------------------------------------------------------------
def warn(line_no: int, message: str) -> None:
    """Print a warning that says which CSV line has the problem."""
    print(f"  WARNING line {line_no}: {message}")


def clean_text(value: str | None) -> str:
    """Remove spaces around a value and make it lower case.

    A short row gives None for the missing columns, so None becomes "".
    Example: "  Y " -> "y"
    """
    if value is None:
        return ""
    return value.strip().lower()


def parse_int(text: str, low: int, high: int | None,
              name: str, line_no: int) -> int | None:
    """Turn text into a whole number between low and high.

    Returns the number, or None (with a warning) if the text is blank,
    not a whole number, or out of range. high=None means "no upper limit".
    """
    if text == "":
        warn(line_no, f"{name} is missing")
        return None
    try:
        number = int(text)          # "abc", "3.5" and "" all raise ValueError
    except ValueError:
        warn(line_no, f"{name} '{text}' is not a whole number")
        return None
    if number < low or (high is not None and number > high):
        limit = f"{low}-{high}" if high is not None else f">= {low}"
        warn(line_no, f"{name} {number} is out of range ({limit})")
        return None
    return number


def parse_choice(text: str, allowed: set[str],
                 name: str, line_no: int) -> str | None:
    """Check that text is one of the allowed words.

    Returns the word, or None (with a warning) if it is blank or not allowed.
    """
    if text == "":
        warn(line_no, f"{name} is missing")
        return None
    if text not in allowed:
        warn(line_no, f"{name} '{text}' is not one of {sorted(allowed)}")
        return None
    return text


# ---------------------------------------------------------------------------
# Job 1: read the CSV file
# ---------------------------------------------------------------------------
def read_csv(path: str) -> list[tuple[int, dict]]:
    """Read the CSV and return a list of (line number, row dictionary).

    Line numbers start at 2 because line 1 is the header.
    Returns an empty list (with a message) if the file can't be used.
    """
    try:
        # utf-8-sig removes the hidden "BOM" character Excel sometimes adds,
        # which would otherwise make the first column name "﻿date".
        with open(path, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            # Stop early if the header row doesn't have the columns we need.
            header = [clean_text(h) for h in (reader.fieldnames or [])]
            missing = [c for c in COLUMNS if c not in header]
            if missing:
                print(f"ERROR: {path} is missing columns: {missing}")
                return []
            reader.fieldnames = header   # use the cleaned column names

            return [(line_no, row) for line_no, row in enumerate(reader, start=2)]
    except FileNotFoundError:
        print(f"ERROR: could not find {path}")
        return []


# ---------------------------------------------------------------------------
# Job 2: check and clean one row
# ---------------------------------------------------------------------------
def validate_row(row: dict, line_no: int) -> dict | None:
    """Check every value in one row and return a cleaned version.

    Rules:
      - date and steps are REQUIRED. If either is missing or wrong, the
        whole row is skipped (returns None), because without them the row
        can't help answer any of my questions.
      - every other column is OPTIONAL. A bad value is stored as None
        (NULL in the database) and the rest of the row is kept.
    """
    # --- date (required): must be a real calendar date, not in the future
    date_text = clean_text(row.get("date"))
    try:
        day = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:      # catches bad format AND impossible dates like 2026-02-30
        warn(line_no, f"date '{date_text}' is not a real YYYY-MM-DD date - row skipped")
        return None
    if day > date.today():
        warn(line_no, f"date {day} is in the future - row skipped")
        return None

    # --- steps (required): whole number, 0 or more
    steps = parse_int(clean_text(row.get("steps")), 0, None, "steps", line_no)
    if steps is None:
        warn(line_no, "row skipped because steps is required")
        return None
    if steps > STEPS_WARNING_LIMIT:
        # Kept on purpose: a very long day is possible, so just flag it.
        warn(line_no, f"steps {steps} is unusually high - kept, please check")

    # --- time_recorded (optional): HH:MM in 24-hour time
    time_text = clean_text(row.get("time_recorded"))
    time_recorded = None
    if time_text == "":
        warn(line_no, "time_recorded is missing")
    else:
        try:
            time_recorded = datetime.strptime(time_text, "%H:%M").strftime("%H:%M")
        except ValueError:
            warn(line_no, f"time_recorded '{time_text}' is not HH:MM")

    # --- the remaining optional columns
    college_day = parse_choice(clean_text(row.get("college_day")),
                               COLLEGE_DAY_VALUES, "college_day", line_no)
    transport = parse_choice(clean_text(row.get("transport")),
                             TRANSPORT_VALUES, "transport", line_no)
    minutes_outside = parse_int(clean_text(row.get("minutes_outside")),
                                0, 1440, "minutes_outside", line_no)
    energy = parse_int(clean_text(row.get("energy")), 1, 5, "energy", line_no)
    weather = parse_choice(clean_text(row.get("weather")),
                           WEATHER_VALUES, "weather", line_no)

    return {
        "date": day.isoformat(),          # stored as text "YYYY-MM-DD"
        "time_recorded": time_recorded,
        "steps": steps,
        "college_day": college_day,
        "transport": transport,
        "minutes_outside": minutes_outside,
        "energy": energy,
        "weather": weather,
    }


def validate_all(rows: list[tuple[int, dict]]) -> list[dict]:
    """Validate every row and drop duplicate dates (the first one is kept)."""
    clean_rows = []
    seen_dates = set()
    for line_no, row in rows:
        cleaned = validate_row(row, line_no)
        if cleaned is None:
            continue
        if cleaned["date"] in seen_dates:
            warn(line_no, f"date {cleaned['date']} appears twice - row skipped")
            continue
        seen_dates.add(cleaned["date"])
        clean_rows.append(cleaned)
    return clean_rows


# ---------------------------------------------------------------------------
# Job 3: create the database table
# ---------------------------------------------------------------------------
def create_table(conn: sqlite3.Connection) -> None:
    """Delete the old steps table (if any) and create a fresh, empty one.

    Dates are stored as TEXT because SQLite has no date type. The
    YYYY-MM-DD format still sorts in the right order as text.
    """
    conn.execute("DROP TABLE IF EXISTS steps")
    conn.execute("""
        CREATE TABLE steps (
            date            TEXT PRIMARY KEY,
            time_recorded   TEXT,
            steps           INTEGER NOT NULL,
            college_day     TEXT,
            transport       TEXT,
            minutes_outside INTEGER,
            energy          INTEGER,
            weather         TEXT
        )
    """)


# ---------------------------------------------------------------------------
# Job 4: insert the good rows
# ---------------------------------------------------------------------------
def insert_rows(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """Insert all cleaned rows into the steps table.

    The ? placeholders let sqlite3 put the values in safely (and turn
    Python None into SQL NULL), instead of gluing strings together.
    """
    values = [tuple(row[col] for col in COLUMNS) for row in rows]
    conn.executemany(
        f"INSERT INTO steps ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
        values,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Job 5: SQL queries that help answer my questions
# ---------------------------------------------------------------------------
QUERIES = [
    ("Q1: Average steps - college days vs days off",
     """SELECT college_day, COUNT(*) AS days, CAST(ROUND(AVG(steps)) AS INTEGER) AS avg_steps
        FROM steps
        WHERE college_day IS NOT NULL
        GROUP BY college_day
        ORDER BY avg_steps DESC"""),

    ("Q2: Average steps for each energy level",
     """SELECT energy, COUNT(*) AS days, CAST(ROUND(AVG(steps)) AS INTEGER) AS avg_steps
        FROM steps
        WHERE energy IS NOT NULL
        GROUP BY energy
        ORDER BY energy"""),

    ("Q3: Average steps and minutes outside for each weather type",
     """SELECT weather, COUNT(*) AS days,
               CAST(ROUND(AVG(steps)) AS INTEGER) AS avg_steps,
               CAST(ROUND(AVG(minutes_outside)) AS INTEGER) AS avg_minutes_outside
        FROM steps
        WHERE weather IS NOT NULL
        GROUP BY weather
        ORDER BY avg_steps DESC"""),

    ("Number of days for each transport type",
     """SELECT transport, COUNT(*) AS days
        FROM steps
        WHERE transport IS NOT NULL
        GROUP BY transport
        ORDER BY days DESC"""),

    ("Top 5 step days",
     """SELECT date, steps, college_day, transport, weather
        FROM steps
        ORDER BY steps DESC
        LIMIT 5"""),

    ("Days with energy 4 or higher",
     """SELECT date, steps, energy, college_day
        FROM steps
        WHERE energy >= 4
        ORDER BY date"""),
]


def print_table(cursor: sqlite3.Cursor) -> None:
    """Print the result of a query as a simple lined-up table."""
    headers = [col[0] for col in cursor.description]
    # Show empty (NULL) values as "-" instead of "None".
    rows = [["-" if v is None else v for v in r] for r in cursor.fetchall()]
    if not rows:
        print("  (no matching rows)")
        return
    # Make each column as wide as its longest value (or its header).
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows))
              for i, h in enumerate(headers)]
    print("  " + "  ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        print("  " + "  ".join(str(v).ljust(w) for v, w in zip(r, widths)))


def run_queries(conn: sqlite3.Connection) -> None:
    """Run every query in QUERIES and print its results."""
    for title, sql in QUERIES:
        print(f"\n{title}")
        print_table(conn.execute(sql))


# ---------------------------------------------------------------------------
# Put it all together
# ---------------------------------------------------------------------------
def main() -> None:
    """Read, check, store and query the step data."""
    csv_path = sys.argv[1] if len(sys.argv) > 1 else CSV_PATH

    print(f"Reading {csv_path} ...")
    rows = read_csv(csv_path)
    clean_rows = validate_all(rows)
    skipped = len(rows) - len(clean_rows)
    print(f"\n{len(clean_rows)} rows loaded, {skipped} skipped.")

    # Stop here if nothing was usable, so a typo in the file name
    # doesn't wipe the existing database.
    if not clean_rows:
        print("No valid rows - database not changed.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        create_table(conn)
        insert_rows(conn, clean_rows)
        run_queries(conn)
    finally:
        conn.close()     # always close the database, even if something fails


if __name__ == "__main__":
    main()
