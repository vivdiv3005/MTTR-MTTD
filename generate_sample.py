"""Generates sample_incidents.csv for the MTTR/MTTD Tracker demo."""
import csv, random
from datetime import datetime, timedelta

random.seed(42)

SEVERITIES  = ["P1","P2","P3","P4"]
SEV_WEIGHTS = [0.05, 0.20, 0.45, 0.30]
CATEGORIES  = ["Malware","Phishing","Data Exfil","Unauthorised Access",
                "DDoS","Insider Threat","Ransomware","Misconfiguration","Vulnerability Exploit"]
TEAMS       = ["SOC Tier 1","SOC Tier 2","IR Team","Cloud Security","Endpoint Security"]
ANALYSTS    = ["alice.chen","bob.martin","carol.white","dave.jones","eve.nguyen","frank.brown"]

SLA_DETECT  = {"P1":5,   "P2":15,  "P3":30,  "P4":120}
SLA_RESPOND = {"P1":30,  "P2":60,  "P3":240, "P4":480}
SLA_RESOLVE = {"P1":240, "P2":480, "P3":1440,"P4":4320}

BASE = datetime(2026, 1, 1, 0, 0, 0)
rows = []

for i in range(180):
    sev  = random.choices(SEVERITIES, SEV_WEIGHTS)[0]
    cat  = random.choice(CATEGORIES)
    team = random.choice(TEAMS)
    analyst = random.choice(ANALYSTS)
    # dates spread over 6 months with slight improvement trend
    day_offset = i * 1.0
    week = int(day_offset // 7)
    improvement = max(0.5, 1.0 - week * 0.008)  # gradual improvement

    alert_time = BASE + timedelta(days=day_offset + random.uniform(0, 1),
                                   hours=random.randint(0, 23),
                                   minutes=random.randint(0, 59))

    base_detect  = SLA_DETECT[sev]  * improvement * random.uniform(0.5, 2.5)
    base_respond = SLA_RESPOND[sev] * improvement * random.uniform(0.6, 2.2)
    base_resolve = SLA_RESOLVE[sev] * improvement * random.uniform(0.7, 1.8)

    detect_min  = max(1,  round(base_detect))
    respond_min = max(detect_min + 5, round(base_respond))
    resolve_min = max(respond_min + 10, round(base_resolve))

    detect_time  = alert_time  + timedelta(minutes=detect_min)
    respond_time = detect_time + timedelta(minutes=respond_min - detect_min)
    resolve_time = alert_time  + timedelta(minutes=resolve_min)

    sla_det_breach = detect_min  > SLA_DETECT[sev]
    sla_res_breach = respond_min > SLA_RESPOND[sev]
    sla_mttr_breach= resolve_min > SLA_RESOLVE[sev]

    rows.append({
        "incident_id":    f"INC-{5000+i}",
        "severity":       sev,
        "category":       cat,
        "team":           team,
        "analyst":        analyst,
        "alert_time":     alert_time.strftime("%Y-%m-%d %H:%M:%S"),
        "detect_time":    detect_time.strftime("%Y-%m-%d %H:%M:%S"),
        "respond_time":   respond_time.strftime("%Y-%m-%d %H:%M:%S"),
        "resolve_time":   resolve_time.strftime("%Y-%m-%d %H:%M:%S"),
        "mttd_min":       detect_min,
        "mttr_min":       resolve_min,
        "sla_detect_met": "false" if sla_det_breach else "true",
        "sla_respond_met":"false" if sla_res_breach else "true",
        "sla_resolve_met":"false" if sla_mttr_breach else "true",
    })

with open("/home/claude/mttr-mttd-tracker/sample_incidents.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
print(f"Generated {len(rows)} incidents over 6 months")
