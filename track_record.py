#!/usr/bin/env python3
"""Public track record for the Dixon-Coles soccer Actor.

Called from build_predictions.py with rows the Actor already returned, so it
costs no extra Actor runs. Two jobs:

  freeze(): the first time a fixture falls inside the next FREEZE_HOURS, append
            the model's probabilities to data/ledger.csv. A row is never
            rewritten, so the git history (dated bot commits) is the proof the
            numbers existed before kickoff.
  settle(): for frozen fixtures that have finished, read the final score from
            ESPN and fill it in. Then data/summary.json is rebuilt.

Nothing here may break the demo build: build_predictions.py wraps every call.
"""
import csv
import datetime
import json
import math
import os
import urllib.error
import urllib.request

LEDGER = os.path.join("data", "ledger.csv")
SUMMARY = os.path.join("data", "summary.json")
FREEZE_HOURS = 36          # daily cron + delay margin: a fixture is frozen by the last run before kickoff
SETTLE_AFTER_HOURS = 3     # do not look for a result earlier than this after kickoff
VOID_AFTER_DAYS = 14       # postponed/cancelled fixtures are closed as void
LOW_DATA = ("partial-low-sample", "partial-new-team")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard"

FIELDS = [
    "frozen_at", "league", "espn_id", "kickoff", "home", "away",
    "p1", "pX", "p2", "pOver25", "pBtts",
    "data_quality", "home_matches", "away_matches", "history_matches",
    "home_goals", "away_goals", "status", "settled_at",
]


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _parse(ts):
    return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _iso(dt):
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_ledger():
    try:
        with open(LEDGER, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def write_ledger(rows):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["kickoff"], r["league"], r["espn_id"]))
    with open(LEDGER, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def freeze(slug, actor_rows, now=None):
    """Append fixtures kicking off within FREEZE_HOURS that are not yet frozen."""
    now = now or _now()
    horizon = now + datetime.timedelta(hours=FREEZE_HOURS)
    ledger = read_ledger()
    seen = {(r["league"], r["espn_id"]) for r in ledger}
    added = 0
    for r in actor_rows:
        eid = str(r.get("espnId") or "")
        if not eid or (slug, eid) in seen:
            continue
        try:
            ko = _parse(r["kickoff"])
        except (KeyError, ValueError):
            continue
        if not (now < ko <= horizon):
            continue
        ledger.append({
            "frozen_at": _iso(now), "league": slug, "espn_id": eid,
            "kickoff": _iso(ko), "home": r["homeTeam"], "away": r["awayTeam"],
            "p1": "%.6f" % r["prob1"], "pX": "%.6f" % r["probX"], "p2": "%.6f" % r["prob2"],
            "pOver25": "%.6f" % r["probOver25"], "pBtts": "%.6f" % r["probBttsYes"],
            "data_quality": r.get("dataQuality", ""),
            "home_matches": r.get("homeMatches", ""), "away_matches": r.get("awayMatches", ""),
            "history_matches": r.get("historyMatches", ""),
            "status": "open",
        })
        seen.add((slug, eid))
        added += 1
    if added:
        write_ledger(ledger)
    return added


def _scoreboard(slug, day):
    """Finished events of one league on one day (single-day queries work; ranges 400)."""
    url = (ESPN % slug) + "?dates=" + day.strftime("%Y%m%d") + "&limit=300"
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = json.load(resp)
    out = {}
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        status = (comp.get("status") or ev.get("status") or {}).get("type", {})
        if not (status.get("completed") and status.get("state") == "post"):
            continue
        score = {}
        for c in comp.get("competitors", []):
            try:
                score[c.get("homeAway")] = int(c.get("score"))
            except (TypeError, ValueError):
                pass
        if "home" in score and "away" in score:
            out[str(ev.get("id"))] = (score["home"], score["away"])
    return out


def settle(now=None):
    now = now or _now()
    ledger = read_ledger()
    cache, changed = {}, 0
    for r in ledger:
        if r["status"] != "open":
            continue
        ko = _parse(r["kickoff"])
        if now < ko + datetime.timedelta(hours=SETTLE_AFTER_HOURS):
            continue
        found = None
        # ESPN buckets days in US time, so also look at the day before the UTC date
        for day in (ko.date(), ko.date() - datetime.timedelta(days=1)):
            key = (r["league"], day)
            if key not in cache:
                try:
                    cache[key] = _scoreboard(r["league"], day)
                except (urllib.error.URLError, TimeoutError, ValueError):
                    cache[key] = None
            if cache[key] and r["espn_id"] in cache[key]:
                found = cache[key][r["espn_id"]]
                break
        if found:
            r["home_goals"], r["away_goals"] = found
            r["status"], r["settled_at"] = "final", _iso(now)
            changed += 1
        elif now > ko + datetime.timedelta(days=VOID_AFTER_DAYS):
            r["status"], r["settled_at"] = "void", _iso(now)
            changed += 1
    if changed:
        write_ledger(ledger)
    return changed


def _outcome(r):
    h, a = int(r["home_goals"]), int(r["away_goals"])
    return (0 if h > a else 1 if h == a else 2), h + a, h > 0 and a > 0


def _block(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    hit = base_home = o_hit = b_hit = 0
    brier = logloss = 0.0
    for r in rows:
        res, goals, btts = _outcome(r)
        p = [float(r["p1"]), float(r["pX"]), float(r["p2"])]
        hit += p.index(max(p)) == res
        base_home += res == 0
        brier += sum((p[i] - (i == res)) ** 2 for i in range(3))
        logloss += -math.log(max(p[res], 1e-9))
        o_hit += (float(r["pOver25"]) > 0.5) == (goals > 2)
        b_hit += (float(r["pBtts"]) > 0.5) == btts
    # naive reference for Brier/log loss: league-agnostic 45/27/28 prior
    ref = (0.45, 0.27, 0.28)
    ref_brier = ref_ll = 0.0
    for r in rows:
        res = _outcome(r)[0]
        ref_brier += sum((ref[i] - (i == res)) ** 2 for i in range(3))
        ref_ll += -math.log(ref[res])
    acc = hit / n
    return {
        "n": n,
        "accuracy_1x2": round(acc, 4),
        "margin_95": round(1.96 * math.sqrt(acc * (1 - acc) / n), 4),
        "baseline_always_home": round(base_home / n, 4),
        "brier_1x2": round(brier / n, 4),
        "brier_reference": round(ref_brier / n, 4),
        "log_loss_1x2": round(logloss / n, 4),
        "log_loss_reference": round(ref_ll / n, 4),
        "accuracy_over25": round(o_hit / n, 4),
        "accuracy_btts": round(b_hit / n, 4),
    }


def summarize(now=None):
    now = now or _now()
    ledger = read_ledger()
    final = [r for r in ledger if r["status"] == "final"]
    full = [r for r in final if r["data_quality"] not in LOW_DATA]
    low = [r for r in final if r["data_quality"] in LOW_DATA]
    leagues = {}
    for r in final:
        leagues.setdefault(r["league"], []).append(r)
    doc = {
        "updated": _iso(now),
        "first_frozen": min((r["frozen_at"] for r in ledger), default=None),
        "frozen_total": len(ledger),
        "open": sum(r["status"] == "open" for r in ledger),
        "all": _block(final),
        "full_data_only": _block(full),
        "low_data_only": _block(low),
        "by_league": {k: _block(v) for k, v in sorted(leagues.items())},
        "note": "Probabilities are frozen before kickoff; git history dates every row. "
                "Reference = fixed 45/27/28 home/draw/away prior. Simulation and data. Not tips.",
    }
    os.makedirs("data", exist_ok=True)
    with open(SUMMARY, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    return doc


if __name__ == "__main__":
    # `python track_record.py` alone = settle + resummarize (no Actor calls)
    print("settled", settle())
    print(json.dumps(summarize()["all"], indent=2))
