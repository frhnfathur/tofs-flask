from app import app, db, TOFSReport  # pastikan kamu import app juga
from datetime import date, timedelta
import random

clsr_options = [
    "1. Tools & Equipment", "2. Line of Fire", "3. Hot Work", "4. Confined Space",
    "5. Powered System", "6. Lifting Operation", "7. Working at Height",
    "8. Ground-Disturbance Work", "9. Water-Based Work Activities", "10. Land Transportation"
]

def random_date(start_year=2024, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 6, 1)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

with app.app_context():  # ⬅️ inilah solusi kuncinya
    for _ in range(100):
        site = random.choice(["ZULU F/S", "BRAVO", "ALFA"])
        dt = random_date()
        month = dt.strftime('%m')
        year = dt.strftime('%y')

        existing_count = TOFSReport.query.filter(
            TOFSReport.site == site,
            db.extract('month', TOFSReport.date) == int(month),
            db.extract('year', TOFSReport.date) == 2000 + int(year)
        ).count()

        count = existing_count + 1
        card_number = f'TOFS/{site}/{month}/{year}/{count:04d}'

        report = TOFSReport(
            card_number=card_number,
            name=f"Tester {random.randint(1, 100)}",
            division=random.choice(["Projects", "Operations", "HSE"]),
            site=site,
            sub_location=f"Sub-{random.randint(1, 10)}",
            date=dt,
            issue_description="Ini adalah deskripsi isu uji coba.",
            follow_up="Ini adalah tindak lanjut uji coba.",
            clsr_terkait=random.choice(clsr_options),
            status=random.choice(["Open", "Closed"])
        )

        db.session.add(report)

    db.session.commit()
    print("✅ 100 data dummy TOFS berhasil ditambahkan!")
