import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB_PATH = DATA / "access.db"
VERIFIED_ON = "2026-08-11"

REAL_OPPORTUNITIES = [
    {
        "title": "The Gates Scholarship 2027",
        "org": "The Gates Scholarship",
        "type": "Scholarship",
        "interests": ["Leadership", "Community", "STEM", "Business"],
        "grades": ["12"],
        "location": "United States",
        "deadline": "2026-09-15",
        "value": 0,
        "description": "Open July 15–September 15, 2026. A highly selective, last-dollar scholarship for outstanding high school seniors from low-income households. Basic eligibility includes Pell eligibility, U.S. citizenship or permanent residency, a minimum 3.3 weighted GPA, and plans to enroll full-time in a four-year degree program at an accredited U.S. not-for-profit college or university. Award covers the full cost of attendance not already covered by other aid. Verified against the official source on August 11, 2026.",
        "url": "https://www.thegatesscholarship.org/scholarship/",
    },
    {
        "title": "NASA OSTEM Internship — Spring 2027",
        "org": "NASA Office of STEM Engagement",
        "type": "Internship",
        "interests": ["STEM", "Research", "Technology", "Engineering"],
        "grades": ["College"],
        "location": "United States / NASA centers",
        "deadline": "2026-09-14",
        "value": 0,
        "description": "Paid, project-based NASA internship for college-level students. NASA lists the Spring 2027 application deadline as September 14, 2026 at 11:59 p.m. ET. Applicants must be U.S. citizens, at least 16, have a 3.0 GPA, and be enrolled full- or part-time in an eligible U.S. college, university, or technical program. Verified against the official NASA source on August 11, 2026.",
        "url": "https://www.nasa.gov/learning-resources/internship-programs/",
    },
    {
        "title": "Coca-Cola Scholars Program 2027",
        "org": "Coca-Cola Scholars Foundation",
        "type": "Scholarship",
        "interests": ["Leadership", "Community", "Business"],
        "grades": ["12"],
        "location": "United States",
        "deadline": "2026-09-30",
        "value": 20000,
        "description": "For current high school seniors graduating during the 2026–2027 academic year who meet the program's U.S. eligibility rules, have at least a 3.0 GPA, and plan to pursue a degree at an accredited U.S. post-secondary institution. Phase 1 is open August 3–September 30, 2026 and requires no essays, transcript, or recommendations. Award: $20,000. Verified against the official source on August 11, 2026.",
        "url": "https://www.coca-colascholarsfoundation.org/apply/",
    },
    {
        "title": "QuestBridge National College Match 2026",
        "org": "QuestBridge",
        "type": "Scholarship",
        "interests": ["Leadership", "Community", "Writing"],
        "grades": ["12"],
        "location": "United States / eligible U.S. citizens and permanent residents abroad",
        "deadline": "2026-10-01",
        "value": 0,
        "description": "A free college and scholarship application for high-achieving high school seniors from low-income backgrounds. QuestBridge's 2026 timeline lists October 1 as the National College Match application deadline. Finalists can rank participating colleges for consideration for early admission with a full four-year scholarship. Review the official eligibility and residency rules before applying. Verified August 11, 2026.",
        "url": "https://www.questbridge.org/apply-to-college/programs/national-college-match/apply",
    },
    {
        "title": "YoungArts 2027 National Arts Competition",
        "org": "YoungArts",
        "type": "Competition",
        "interests": ["Arts", "Writing", "Design", "Music", "Film", "Photography"],
        "grades": ["10", "11", "12"],
        "location": "United States",
        "deadline": "2026-10-06",
        "value": 10000,
        "description": "Open to eligible artists ages 15–18 or in grades 10–12 across disciplines including classical music, dance, design, film, jazz, photography, theater, visual arts, voice, and writing. The 2027 application closes October 6, 2026 at 8 p.m. ET. All winners receive cash awards from $250 to $10,000 plus ongoing artistic support. Verified August 11, 2026.",
        "url": "https://youngarts.org/apply/",
    },
    {
        "title": "Lester B. Pearson International Student Scholarship 2027",
        "org": "University of Toronto",
        "type": "Scholarship",
        "interests": ["Leadership", "Community", "STEM", "Business", "Arts"],
        "grades": ["12"],
        "location": "Toronto, Canada / International students",
        "deadline": "2026-11-06",
        "value": 0,
        "description": "University of Toronto's major scholarship for international students, covering tuition, books, incidental fees, and full residence support for four years. Students must be nominated by their high school. For the 2027 cycle: school nomination deadline October 9, U of T admission application deadline October 16, and scholarship application/document deadline November 6, 2026. Verified August 11, 2026.",
        "url": "https://future.utoronto.ca/pearson-scholarships",
    },
    {
        "title": "2026 Congressional App Challenge",
        "org": "Congressional App Challenge",
        "type": "Competition",
        "interests": ["Technology", "STEM", "Design", "Entrepreneurship"],
        "grades": ["9", "10", "11", "12"],
        "location": "United States — participating congressional districts",
        "deadline": "2026-10-26",
        "value": 0,
        "description": "Middle and high school students can build and submit an original app using any programming language, platform, or theme. Students may enter individually or in teams of up to four and must meet district eligibility rules. The 2026 student registration and submission deadline is October 26, 2026 at 12 p.m. ET. Verified August 11, 2026.",
        "url": "https://www.congressionalappchallenge.us/students/student-registration/",
    },
    {
        "title": "BigFuture Scholarships — Strengthen Your College List",
        "org": "College Board BigFuture",
        "type": "Scholarship",
        "interests": ["Leadership", "College Planning"],
        "grades": ["12"],
        "location": "United States / U.S. territories / DoDEA schools",
        "deadline": "2026-10-31",
        "value": 40000,
        "description": "For the Class of 2027. Build or update a BigFuture college list with at least three reach, two match, and one safety school by October 31, 2026 to earn entries in monthly drawings for $500 and $40,000 scholarships. Review College Board's official rules for full eligibility. Verified August 11, 2026.",
        "url": "https://bigfuture.collegeboard.org/pay-for-college/bigfuture-scholarships-2027",
    },
    {
        "title": "VFW Voice of Democracy 2026–27",
        "org": "Veterans of Foreign Wars",
        "type": "Scholarship",
        "interests": ["Writing", "Leadership", "Community", "Public Policy"],
        "grades": ["9", "10", "11", "12"],
        "location": "United States",
        "deadline": "2026-10-31",
        "value": 35000,
        "description": "Audio-essay scholarship program for students in grades 9–12. The 2026–27 theme is “What a Veteran Taught Me About America.” Entries must be submitted through a participating local VFW Post by midnight October 31, 2026. National first prize is a $35,000 scholarship, with additional national awards. Verified August 11, 2026.",
        "url": "https://www.vfw.org/VOD",
    },
    {
        "title": "Regeneron Science Talent Search 2027",
        "org": "Society for Science",
        "type": "Competition",
        "interests": ["STEM", "Research", "Technology", "Health", "Environment"],
        "grades": ["12"],
        "location": "United States / qualifying U.S. citizens abroad",
        "deadline": "2026-11-05",
        "value": 250000,
        "description": "Research competition for students in their final year of secondary school who meet the official eligibility rules and submit original, independent research. The 2027 application is open through November 5, 2026 at 8 p.m. ET. Awards include a $250,000 first prize; the top 300 scholars receive awards and 40 finalists advance to Washington, D.C. Verified August 11, 2026.",
        "url": "https://www.societyforscience.org/regeneron-sts/",
    },
    {
        "title": "Jack Kent Cooke College Scholarship Program 2027",
        "org": "Jack Kent Cooke Foundation",
        "type": "Scholarship",
        "interests": ["Leadership", "Community", "College Planning"],
        "grades": ["12"],
        "location": "United States",
        "deadline": "2026-11-11",
        "value": 55000,
        "description": "For high-achieving high school seniors with financial need. The 2027 application opens August 19 and closes November 11, 2026 through the Common App. The last-dollar award can provide as much as $55,000 per year toward a bachelor's degree, plus advising and scholar support. Verified August 11, 2026.",
        "url": "https://www.jkcf.org/our-scholarships/college-scholarship-program/how-to-apply/",
    },
    {
        "title": "Elks Most Valuable Student Scholarship 2027",
        "org": "Elks National Foundation",
        "type": "Scholarship",
        "interests": ["Leadership", "Community"],
        "grades": ["12"],
        "location": "United States",
        "deadline": "2026-11-12",
        "value": 30000,
        "description": "For current U.S.-citizen high school seniors planning to enroll full-time in a four-year undergraduate degree program at an accredited U.S. college or university. The 2027 deadline is November 12, 2026 at 11:59 p.m. PT. The national program awards 500 scholarships; the Top 20 receive $30,000 and 480 runners-up receive $4,000. Verified August 11, 2026.",
        "url": "https://www.elks.org/scholars/scholarships/mvs.cfm",
    },
    {
        "title": "BigFuture Scholarships — Start Your Scholarship List",
        "org": "College Board BigFuture",
        "type": "Scholarship",
        "interests": ["College Planning", "Leadership"],
        "grades": ["12"],
        "location": "United States / U.S. territories / DoDEA schools",
        "deadline": "2026-11-30",
        "value": 40000,
        "description": "Open to eligible students in the Class of 2027 with a College Board account. Save three or more scholarships in BigFuture Scholarship Search by November 30, 2026 to earn entries in monthly drawings for $500 and $40,000 scholarships. Review the official rules for full eligibility. Verified August 11, 2026.",
        "url": "https://bigfuture.collegeboard.org/scholarships/bigfuture-scholarships-start-your-scholarship-list-class-of-2027",
    },
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def patch_public_copy():
    index_path = ROOT / "public" / "index.html"
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
        text = text.replace('<strong>240+</strong><span>demo listings</span>', f'<strong>{len(REAL_OPPORTUNITIES)}</strong><span>verified opportunities</span>')
        text = text.replace('Demo listings are clearly labeled. Replace them with verified opportunities through the admin dashboard.', 'Every featured listing is checked against an official source. Always confirm eligibility and requirements before submitting an application.')
        index_path.write_text(text, encoding="utf-8")
    app_path = ROOT / "public" / "app.js"
    if app_path.exists():
        text = app_path.read_text(encoding="utf-8")
        text = text.replace('return n ? `$${n.toLocaleString()}` : "Experience-based";', 'return n ? `$${n.toLocaleString()}` : "See award details";')
        app_path.write_text(text, encoding="utf-8")


def sync_real_opportunities():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opportunities(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, org TEXT NOT NULL, type TEXT NOT NULL,
          interests TEXT DEFAULT '[]', grades TEXT DEFAULT '[]', location TEXT DEFAULT 'Online', deadline TEXT NOT NULL,
          value INTEGER DEFAULT 0, description TEXT DEFAULT '', url TEXT DEFAULT '', verified INTEGER DEFAULT 0,
          is_demo INTEGER DEFAULT 0, created_at TEXT NOT NULL
        )
    """)

    # Remove only the fictional records shipped with the MVP. Admin-imported real records are preserved.
    conn.execute("DELETE FROM opportunities WHERE is_demo=1")

    for item in REAL_OPPORTUNITIES:
        row = conn.execute("SELECT id FROM opportunities WHERE url=?", (item["url"],)).fetchone()
        params = (
            item["title"], item["org"], item["type"], json.dumps(item["interests"]), json.dumps(item["grades"]),
            item["location"], item["deadline"], item["value"], item["description"], item["url"], 1, 0,
        )
        if row:
            conn.execute("""
                UPDATE opportunities
                SET title=?, org=?, type=?, interests=?, grades=?, location=?, deadline=?, value=?, description=?, url=?, verified=?, is_demo=?
                WHERE id=?
            """, params + (row[0],))
        else:
            conn.execute("""
                INSERT INTO opportunities(title,org,type,interests,grades,location,deadline,value,description,url,verified,is_demo,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, params + (now_iso(),))

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM opportunities WHERE is_demo=0 AND verified=1").fetchone()[0]
    conn.close()
    print(f"Access bootstrap: {count} verified opportunities available; demo records removed.")


if __name__ == "__main__":
    patch_public_copy()
    sync_real_opportunities()
