#!/usr/bin/env python3
"""Computes track-record statistics from data/ledger.csv and writes data/track_stats.json.
Pure stdlib, zero extra dependencies, meant to run as a daily step in refresh-predictions.yml
right after track_record.py (which freezes/settles matches). Idempotent: recomputes from
scratch every run from the full ledger, so it self-heals if a row changes.
"""
import csv
import json
import math
import os
from datetime import datetime, timezone

LEDGER_PATH = os.path.join("data", "ledger.csv")
OUT_PATH = os.path.join("data", "track_stats.json")


def clip(p, eps=1e-9):
    return min(max(p, eps), 1 - eps)


def main():
    rows = []
    with open(LEDGER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("status") != "final":
                continue
            if r.get("home_goals") in (None, "") or r.get("away_goals") in (None, ""):
                continue
            rows.append(r)

    n = len(rows)
    if n == 0:
        payload = {"generatedAt": datetime.now(timezone.utc).isoformat(), "n": 0}
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1)
        return

    correct = brier_sum = logloss_sum = 0.0
    home_wins = draws = away_wins = 0
    dq = {}
    over_n = over_correct = 0
    over_brier = over_logloss = over_actual = 0.0
    btts_n = btts_correct = 0
    btts_brier = btts_logloss = btts_actual = 0.0
    k_n = k_model_correct = k_mkt_correct = 0
    k_model_brier = k_model_logloss = k_mkt_brier = k_mkt_logloss = 0.0
    league_counts = {}
    min_kickoff = None
    max_settled = None

    for r in rows:
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        p1, pX, p2 = float(r["p1"]), float(r["pX"]), float(r["p2"])
        if hg > ag:
            y1, yX, y2, outcome = 1, 0, 0, "1"
            home_wins += 1
        elif hg == ag:
            y1, yX, y2, outcome = 0, 1, 0, "X"
            draws += 1
        else:
            y1, yX, y2, outcome = 0, 0, 1, "2"
            away_wins += 1

        predicted = "1" if (p1 >= pX and p1 >= p2) else ("X" if pX >= p2 else "2")
        if predicted == outcome:
            correct += 1

        brier_sum += (p1 - y1) ** 2 + (pX - yX) ** 2 + (p2 - y2) ** 2
        p_out = {"1": p1, "X": pX, "2": p2}[outcome]
        logloss_sum += -math.log(clip(p_out))

        q = r.get("data_quality", "unknown")
        dq.setdefault(q, {"n": 0, "correct": 0})
        dq[q]["n"] += 1
        if predicted == outcome:
            dq[q]["correct"] += 1

        league_counts[r["league"]] = league_counts.get(r["league"], 0) + 1

        k = r.get("kickoff", "")
        s = r.get("settled_at", "")
        if k and (min_kickoff is None or k < min_kickoff):
            min_kickoff = k
        if s and (max_settled is None or s > max_settled):
            max_settled = s

        if r.get("pOver25"):
            p_over = float(r["pOver25"])
            y_over = 1 if (hg + ag) > 2.5 else 0
            over_n += 1
            over_actual += y_over
            if (p_over > 0.5) == bool(y_over):
                over_correct += 1
            over_brier += (p_over - y_over) ** 2
            over_logloss += -(y_over * math.log(clip(p_over)) + (1 - y_over) * math.log(clip(1 - p_over)))

        if r.get("pBtts"):
            p_btts = float(r["pBtts"])
            y_btts = 1 if (hg > 0 and ag > 0) else 0
            btts_n += 1
            btts_actual += y_btts
            if (p_btts > 0.5) == bool(y_btts):
                btts_correct += 1
            btts_brier += (p_btts - y_btts) ** 2
            btts_logloss += -(y_btts * math.log(clip(p_btts)) + (1 - y_btts) * math.log(clip(1 - p_btts)))

        if r.get("k_home_bid") and r.get("k_draw_bid") and r.get("k_away_bid"):
            mh = (float(r["k_home_bid"]) + float(r["k_home_ask"])) / 2
            md = (float(r["k_draw_bid"]) + float(r["k_draw_ask"])) / 2
            ma = (float(r["k_away_bid"]) + float(r["k_away_ask"])) / 2
            total = mh + md + ma
            nmh, nmd, nma = mh / total, md / total, ma / total  # de-vig, normalize to sum 1
            k_n += 1
            mkt_pred = "1" if (nmh >= nmd and nmh >= nma) else ("X" if nmd >= nma else "2")
            if mkt_pred == outcome:
                k_mkt_correct += 1
            mkt_p_out = {"1": nmh, "X": nmd, "2": nma}[outcome]
            k_mkt_brier += (nmh - y1) ** 2 + (nmd - yX) ** 2 + (nma - y2) ** 2
            k_mkt_logloss += -math.log(clip(mkt_p_out))
            if predicted == outcome:
                k_model_correct += 1
            k_model_brier += (p1 - y1) ** 2 + (pX - yX) ** 2 + (p2 - y2) ** 2
            k_model_logloss += -math.log(clip(p_out))

    acc = correct / n
    se = math.sqrt(acc * (1 - acc) / n)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "n": n,
        "periodStart": min_kickoff,
        "periodEnd": max_settled,
        "leagueCounts": league_counts,
        "outcomes": {"home": home_wins, "draw": draws, "away": away_wins},
        "accuracy": acc,
        "accuracyMarginOfError95": 1.96 * se,
        "baselineHomeAccuracy": home_wins / n,
        "baselineUniformBrier": 2.0 / 3.0,
        "baselineUniformLogloss": math.log(3),
        "brier": brier_sum / n,
        "logloss": logloss_sum / n,
        "dataQuality": dq,
        "over25": {
            "n": over_n,
            "accuracy": over_correct / over_n if over_n else None,
            "brier": over_brier / over_n if over_n else None,
            "logloss": over_logloss / over_n if over_n else None,
            "actualRate": over_actual / over_n if over_n else None,
        },
        "btts": {
            "n": btts_n,
            "accuracy": btts_correct / btts_n if btts_n else None,
            "brier": btts_brier / btts_n if btts_n else None,
            "logloss": btts_logloss / btts_n if btts_n else None,
            "actualRate": btts_actual / btts_n if btts_n else None,
        },
        "kalshi": {
            "n": k_n,
            "model": {
                "accuracy": k_model_correct / k_n if k_n else None,
                "brier": k_model_brier / k_n if k_n else None,
                "logloss": k_model_logloss / k_n if k_n else None,
            },
            "market": {
                "accuracy": k_mkt_correct / k_n if k_n else None,
                "brier": k_mkt_brier / k_n if k_n else None,
                "logloss": k_mkt_logloss / k_n if k_n else None,
            },
        },
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    print(f"Wrote {OUT_PATH}: n={n} accuracy={acc:.3f} brier={payload['brier']:.3f}")


if __name__ == "__main__":
    main()
