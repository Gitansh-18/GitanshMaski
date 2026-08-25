import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


USERNAME = "Gitansh-18"
OUTPUT = Path("data/contributions.json")

URL = f"https://github.com/users/{USERNAME}/contributions"


def main():
    print(f"Fetching contributions for @{USERNAME}...")

    response = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30,
    )

    response.raise_for_status()

    print("GitHub response received.")

    soup = BeautifulSoup(response.text, "html.parser")

    days = []

    for cell in soup.select("td.ContributionCalendar-day"):
        date = cell.get("data-date")
        level = cell.get("data-level")

        if not date or level is None:
            continue

        # GitHub normally gives levels 0–4.
        try:
            level = int(level)
        except ValueError:
            level = 0

        count = 0

        # GitHub exposes the contribution count in the aria-label.
        label = cell.get("aria-label", "")

        match = re.search(r"([\d,]+)\s+contribution", label)

        if match:
            count = int(match.group(1).replace(",", ""))

        days.append(
            {
                "date": date,
                "count": count,
                "level": level,
            }
        )

    if not days:
        raise RuntimeError(
            "No contribution days were found. "
            "GitHub may have changed its HTML structure."
        )

    days.sort(key=lambda item: item["date"])

    # Current streak
    contribution_dates = {
        item["date"]
        for item in days
        if item["count"] > 0
    }

    current_streak = 0

    from datetime import timedelta

    today = datetime.utcnow().date()

    # Start from today, allowing yesterday as the first possible day.
    cursor = today

    if cursor.isoformat() not in contribution_dates:
        cursor -= timedelta(days=1)

    while cursor.isoformat() in contribution_dates:
        current_streak += 1
        cursor -= timedelta(days=1)

    # Longest streak
    longest_streak = 0
    running = 0
    previous_date = None

    for item in days:
        current_date = datetime.strptime(
            item["date"], "%Y-%m-%d"
        ).date()

        if item["count"] > 0:
            if (
                previous_date is not None
                and (current_date - previous_date).days == 1
            ):
                running += 1
            else:
                running = 1

            longest_streak = max(longest_streak, running)
            previous_date = current_date

    total = sum(item["count"] for item in days)

    best_day = max(
        days,
        key=lambda item: item["count"]
    )

    output = {
        "username": USERNAME,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_contributions": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "days": days,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print(f"Found {len(days)} contribution days.")
    print(f"Total contributions: {total}")
    print(f"Current streak: {current_streak}")
    print(f"Longest streak: {longest_streak}")
    print(f"Best day: {best_day['date']} ({best_day['count']})")
    print(f"Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()