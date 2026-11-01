#!/usr/bin/env python3
"""Turn raw Play-Cricket extracts (from extract/*.js) into template data + post captions.

  python3 prepare.py fixtures raw/fixtures.json                       # Friday: next 7 days
  python3 prepare.py roundup  raw/results.json [--today YYYY-MM-DD]   # Monday: previous 7 days
  python3 prepare.py matches  raw/results.json raw/scorecard_*.json [--today YYYY-MM-DD]
                                                                      # Daily 7am: yesterday's matches

--today defaults to the real date (Europe/London). Writes data/*.json and prints a JSON
list of {file, caption} — an empty list means there is nothing to post. Junior teams get
first name + surname initial only (e.g. "Ben T.").
"""
import json, re, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CLUB = "Verwood CC"
JUNIOR = re.compile(r"\b(U\s?\d{1,2}[A-Z]?|Under\s?\d{1,2}|Girls|Boys|Daughters|Sons|All Stars|Dynamos|Juniors?)\b", re.I)
HASHTAGS = "#VerwoodCC #CricketDorset #ClubCricket"


def is_junior(team): return bool(JUNIOR.search(team or ""))


def short_name(name, junior):
    name = re.sub(r"\s+", " ", (name or "").replace("*", "")).strip()
    if not junior: return name
    parts = name.split(" ")
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."


def tidy_score(s):
    s = re.sub(r"\s*/\s*", "/", s or "").replace("/All out", " all out")
    return re.sub(r"\(\s*", "(", s).strip()


def split_score(s):
    m = re.match(r"(.+?)\s*\((.+)\)", tidy_score(s))
    return (m.group(1), f"{m.group(2)} overs") if m else (tidy_score(s), "")


def short_date(d):
    try: return datetime.strptime(d, "%A %d %B %Y").strftime("%a %-d %b")
    except Exception: return d or ""


def date_range(ds):
    parsed = sorted(datetime.strptime(d, "%A %d %B %Y") for d in ds if d)
    if not parsed: return ""
    a, b = parsed[0], parsed[-1]
    if a == b: return a.strftime("%-d %B %Y")
    if a.month == b.month: return f"{a.day} – {b.strftime('%-d %B %Y')}"
    return f"{a.strftime('%-d %b')} – {b.strftime('%-d %b %Y')}"


def opp_label(side): return f"{side['club']} {side['team']}".strip()


def outcome(status, us_club):
    st = status.upper()
    if "WON BY" in st or st.endswith(" WON"):
        return ("W" if st.startswith(us_club.upper()) else "L"), status.capitalize().replace(us_club.lower(), "Verwood")
    for key, code, text in [("TIED", "T", "Match tied"), ("DRAW", "D", "Match drawn"), ("ABANDON", "A", "Abandoned"),
                            ("CANCEL", "C", "Cancelled"), ("NO RESULT", "N", "No result"), ("CONCEDE", "N", "Conceded")]:
        if key in st: return code, text
    return "P", "Result to follow"


def parse_date(d):
    try: return datetime.strptime(d, "%A %d %B %Y").date()
    except Exception: return None


def results(raw, since=None, until=None):
    """Verwood results with since <= match date <= until (dates inclusive; None = no limit)."""
    rows, dates = [], []
    for m in raw["matches"]:
        us = next((i for i, s in enumerate(m["sides"]) if s["club"] == CLUB), None)
        if us is None: continue
        d = parse_date(m["date"])
        if (since and (not d or d < since)) or (until and (not d or d > until)): continue
        dates.append(m["date"])
        them = m["sides"][1 - us]
        code, text = outcome(m["status"], CLUB)
        if code == "W": text = re.sub(r"^.*?won", "Won", text, flags=re.I)
        if code == "L": text = re.sub(r"^.*?won", "Lost", text, flags=re.I)
        mine = m["sides"][us]
        row = {"id": m.get("id"), "date": short_date(m["date"]), "team": mine["team"],
               "opponent": opp_label(them), "home": us == 0,
               "verwood_score": tidy_score(mine["score"]) or "–",
               "opp_score": tidy_score(them["score"]) or "–", "outcome": code, "summary": text}
        if mine.get("net") is not None and them.get("net") is not None:
            # Pairs cricket: the result is decided on net score, so lead with it; keep runs/wickets as detail.
            row.update(pairs=True, verwood_raw=row["verwood_score"], opp_raw=row["opp_score"],
                       verwood_score=f"{mine['net']} net", opp_score=f"{them['net']} net")
        rows.append(row)
    return {"kind": "results", "title": "Last Week's Results",
            "date_range": date_range(dates), "matches": rows}


def fixtures(raw):
    rows = []
    for m in raw["matches"]:
        us = next((i for i, s in enumerate(m["sides"]) if s["club"] == CLUB), None)
        if us is None: continue
        rows.append({"date": short_date(m["date"]), "time": m["time"], "team": m["sides"][us]["team"],
                     "opponent": opp_label(m["sides"][1 - us]), "home": us == 0})
    return {"kind": "fixtures", "title": "This Week's Fixtures",
            "date_range": date_range([m["date"] for m in raw["matches"]]), "matches": rows}


def strip_dismissal(cell, how):
    """Play-Cricket sometimes appends the dismissal to the name cell ("Ben Tippingnot out").
    Remove it when the name cell ends with the dismissal columns' text (ignoring spaces)."""
    tail = re.sub(r"\s", "", how)
    if not tail or not re.sub(r"\s", "", cell).endswith(tail):
        return cell.strip()
    keep, n = len(cell), len(tail)
    while n and keep:  # walk back over the tail's non-space characters
        keep -= 1
        if not cell[keep].isspace(): n -= 1
    return cell[:keep].strip()


def num(x):
    try: return float(x)
    except Exception: return 0.0


def match_card(row, sc):
    """row: one normalised result; sc: raw scorecard extract for it."""
    junior = is_junior(row["team"])
    order = [o.strip() for o in sc.get("innings_order", [])]
    bat = [t for t in sc["tables"] if t["type"] == "batting"]
    bowl = [t for t in sc["tables"] if t["type"] == "bowling"]
    # Verwood batted in innings 1 if it is listed first; Verwood bowled in the other innings.
    ui = 0 if order and order[0].startswith(CLUB) else 1
    our_bat = bat[ui]["rows"] if len(bat) > ui else []
    our_bowl = bowl[1 - ui]["rows"] if len(bowl) > 1 - ui else []
    batting = []
    for r in our_bat:  # Name | How out | Bowler | R | B | 4s | 6s | SR  (how-out may be merged into name)
        nums = [c for c in r if re.fullmatch(r"-?\d+(\.\d+)?", c)]  # pairs cricket can give negative runs
        if len(nums) < 2: continue
        name = strip_dismissal(r[0], "".join(r[1:3]))
        notout = any("not out" in c for c in r[:3])
        batting.append({"name": short_name(name, junior), "runs": int(nums[0]), "balls": nums[1],
                        "figures": f"{nums[0]}{'*' if notout else ''}", "detail": f"{nums[1]} balls"})
    bowling = []
    for r in our_bowl:  # Bowler | O | M | R | W | Wd | NB | Econ
        if len(r) < 5: continue
        bowling.append({"name": short_name(r[0], junior), "w": int(num(r[4])), "r": int(num(r[3])),
                        "figures": f"{r[4]}-{r[3]}", "detail": f"{r[1].removesuffix('.0')} overs"})
    batting.sort(key=lambda p: (-p["runs"], num(p["balls"])))
    bowling.sort(key=lambda p: (-p["w"], p["r"]))
    pairs = row.get("pairs", False)
    us_score, us_ov = split_score(row["verwood_raw"] if pairs else row["verwood_score"])
    op_score, op_ov = split_score(row["opp_raw"] if pairs else row["opp_score"])
    if pairs:  # big number = net score; runs/wickets and overs underneath
        us_score, us_ov = row["verwood_score"].removesuffix(" net"), f"Net score · {us_score}, {us_ov}"
        op_score, op_ov = row["opp_score"].removesuffix(" net"), f"Net score · {op_score}, {op_ov}"
    opp_club, _, opp_team = row["opponent"].partition(" CC")
    toss = next((h for h in sc.get("header", []) if "toss" in h.lower()), "")
    return {"kind": "match", "id": row["id"], "date": row["date"], "team": row["team"],
            "opponent": (opp_club + " CC").strip() if _ else row["opponent"], "opponent_team": opp_team.strip(" ,"),
            "outcome": row["outcome"],
            "summary": ("Verwood " + row["summary"][0].lower() + row["summary"][1:]) if row["outcome"] in "WL" else row["summary"],
            "verwood_score": us_score, "verwood_overs": us_ov, "opp_score": op_score, "opp_overs": op_ov,
            "pairs": pairs, "toss": "", "points": "Pairs cricket – result decided on net score" if pairs else "",
            "top_batting": batting[:3], "top_bowling": [b for b in bowling if b["w"] > 0][:3] or bowling[:2],
            "_toss_raw": toss}


def caption_results(d):
    lines = [f"🏏 Results round-up · {d['date_range']}", ""]
    icon = {"W": "✅", "L": "❌", "D": "🤝", "T": "🤝"}
    for m in d["matches"]:
        lines.append(f"{icon.get(m['outcome'], '⏳')} {m['team']} v {m['opponent']}: {m['verwood_score']} v {m['opp_score']} – {m['summary']}")
    return "\n".join(lines + ["", "Full scorecards on verwood.play-cricket.com", HASHTAGS])


def caption_fixtures(d):
    lines = [f"📅 Fixtures this week · {d['date_range']}", ""]
    for m in d["matches"]:
        lines.append(f"{m['date']} {m['time']} – {m['team']} v {m['opponent']} ({'H' if m['home'] else 'A'})")
    return "\n".join(lines + ["", "Come down and support! 💙", HASHTAGS])


def caption_match(m):
    head = {"W": "🏆 Win for", "L": "Result for", "D": "Draw for", "T": "Tie for"}.get(m["outcome"], "Update from")
    perf = []
    if m["top_batting"]: perf.append(f"{m['top_batting'][0]['name']} top-scored with {m['top_batting'][0]['figures']}")
    if m["top_bowling"] and m["top_bowling"][0]["w"] > 0: perf.append(f"{m['top_bowling'][0]['name']} took {m['top_bowling'][0]['figures']}")
    return "\n".join([f"{head} our {m['team']}! {m['summary']} v {m['opponent']} {m['opponent_team']}.".replace("  ", " "),
                      (f"Pairs cricket, net scores: Verwood {m['verwood_score']} · {m['opponent']} {m['opp_score']}"
                       if m.get("pairs") else
                       f"Verwood {m['verwood_score']} ({m['verwood_overs']}) · {m['opponent']} {m['opp_score']} ({m['opp_overs']})"),
                      (" · ".join(perf) + ".") if perf else "", "", HASHTAGS]).replace("\n\n\n", "\n\n")


def main(argv):
    today = datetime.now(ZoneInfo("Europe/London")).date()
    if "--today" in argv:
        k = argv.index("--today"); today = date.fromisoformat(argv[k + 1]); argv = argv[:k] + argv[k + 2:]
    mode, raw_path, *scorecards = argv
    raw = json.loads(Path(raw_path).read_text())
    out_dir = ROOT / "data"; out_dir.mkdir(exist_ok=True)
    stamp = today.isoformat()
    summary = []
    if mode == "fixtures":
        d = fixtures(raw)
        if d["matches"]:
            f = out_dir / f"fixtures_{stamp}.json"; f.write_text(json.dumps(d, indent=2))
            summary.append({"file": str(f), "caption": caption_fixtures(d), "count": len(d["matches"])})
    elif mode == "roundup":
        # Monday run: the previous 7 days, i.e. last Monday to yesterday (Sunday)
        d = results(raw, since=today - timedelta(days=7), until=today - timedelta(days=1))
        if d["matches"]:
            f = out_dir / f"roundup_{stamp}.json"; f.write_text(json.dumps(d, indent=2))
            summary.append({"file": str(f), "caption": caption_results(d), "count": len(d["matches"])})
    elif mode == "matches":
        # Daily 7am run: matches played yesterday that have a result and a scorecard
        yday = today - timedelta(days=1)
        d = results(raw, since=yday, until=yday)
        by_id = {str(m["id"]): m for m in d["matches"]}
        for sp in scorecards:
            sc = json.loads(Path(sp).read_text()); row = by_id.get(str(sc["id"]))
            if not row or row["outcome"] == "P" or not sc.get("tables"): continue
            m = match_card(row, sc); m.pop("_toss_raw", None)
            mf = out_dir / f"match_{m['id']}.json"; mf.write_text(json.dumps(m, indent=2))
            summary.append({"file": str(mf), "caption": caption_match(m), "junior": is_junior(m["team"])})
        # ids of yesterday's matches, so the run knows which scorecards to open
        print(json.dumps({"yesterday": yday.isoformat(), "match_ids": list(by_id)}), file=sys.stderr)
    else:
        sys.exit(f"unknown mode {mode!r}: use fixtures, roundup or matches")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
