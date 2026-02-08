#!/usr/bin/env python3
"""
Test script for the Olympics scraper using mock data
"""

from olympics_scraper import OlympicsScraper
import json

# Mock Olympics API response for Feb 6, 2026
MOCK_UNITS = [
    {
        "disciplineCode": "CUR",
        "disciplineName": "Curling",
        "eventCode": "CURXD",
        "eventName": "Mixed Doubles",
        "eventType": "TEAM",
        "phaseName": "Round Robin",
        "phaseType": "RR",
        "eventUnitName": "Session 1",
        "unitNum": 1,
        "startDate": "2026-02-06T09:00:00+01:00",
        "endDate": "2026-02-06T11:00:00+01:00",
        "olympicDay": 1,
        "venue": "CCP",
        "venueDescription": "Cortina Curling Centre",
        "venueLongDescription": "Cortina Curling Centre",
        "location": "COR",
        "locationDescription": "Cortina d'Ampezzo",
        "medalFlag": 0,
        "status": "SCHEDULED",
        "statusDescription": "Scheduled",
        "competitors": [
            {
                "noc": "GBR",
                "code": "CURXD-GBR",
                "name": "Great Britain",
                "order": 1,
                "competitorType": "TEAM"
            },
            {
                "noc": "NOR",
                "code": "CURXD-NOR",
                "name": "Norway",
                "order": 2,
                "competitorType": "TEAM"
            }
        ]
    },
    {
        "disciplineCode": "SKI",
        "disciplineName": "Alpine Skiing",
        "eventCode": "SKIALM",
        "eventName": "Alpine Men's Slalom",
        "eventType": "INDV",
        "phaseName": "Qualification",
        "phaseType": "QUAL",
        "eventUnitName": "Run 1",
        "unitNum": 1,
        "startDate": "2026-02-06T10:00:00+01:00",
        "endDate": "2026-02-06T12:00:00+01:00",
        "olympicDay": 1,
        "venue": "SCI",
        "venueDescription": "Sciaves",
        "venueLongDescription": "Sciaves Slalom Course",
        "location": "VAL",
        "locationDescription": "Val d'Aosta",
        "medalFlag": 0,
        "status": "SCHEDULED",
        "statusDescription": "Scheduled",
        "competitors": [
            {
                "noc": "USA",
                "code": "SKI-1001",
                "name": "Mikaela Shiffrin",
                "order": 1,
                "competitorType": "ATHLETE"
            },
            {
                "noc": "AUT",
                "code": "SKI-2001",
                "name": "Katharina Liensberger",
                "order": 2,
                "competitorType": "ATHLETE"
            }
        ]
    }
]


def test_scraper():
    scraper = OlympicsScraper()

    # Log sync
    print("Logging sync...")
    scraper.log_sync('olympics', 'incremental')

    # Process units
    print("Processing mock units...")
    processed, inserted = scraper.process_units(MOCK_UNITS)

    # Update sync log
    scraper.update_sync_log(
        'success',
        records_processed=processed,
        records_inserted=inserted
    )

    print(f"✓ Test complete: {processed} processed, {inserted} inserted")

    # Verify data was inserted
    print("\nVerifying inserted data...")
    disciplines = scraper.execute_sql("SELECT * FROM disciplines ORDER BY created_at DESC LIMIT 2")
    print(f"Disciplines:\n{disciplines}\n")

    events = scraper.execute_sql("SELECT * FROM events ORDER BY created_at DESC LIMIT 2")
    print(f"Events:\n{events}\n")

    venues = scraper.execute_sql("SELECT * FROM venues ORDER BY created_at DESC LIMIT 2")
    print(f"Venues:\n{venues}\n")

    units = scraper.execute_sql("SELECT id, unit_code, unit_name FROM schedule_units ORDER BY created_at DESC LIMIT 2")
    print(f"Schedule Units:\n{units}\n")

    competitors = scraper.execute_sql("SELECT * FROM competitors ORDER BY created_at DESC LIMIT 4")
    print(f"Competitors:\n{competitors}\n")

    matchups = scraper.execute_sql("SELECT * FROM unit_competitors ORDER BY id DESC LIMIT 4")
    print(f"Matchups:\n{matchups}\n")


if __name__ == '__main__':
    test_scraper()
