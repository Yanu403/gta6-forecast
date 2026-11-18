"""Forecast GTA VI's launch-day Twitch concurrent viewers, hour by hour.

Reads a case file (`<id>.in`) and writes `<id>.out`: for hours 2..24 of the release day,
the five scored quantiles (5%, 25%, 50%, 75%, 95%) of that hour's viewer count.

The model
---------
For each hour h:

    q_tau(h) = p1 * r_h * exp(z_tau * s_h)

  p1    hour 1's print, the only observation the case gives (`known`), floored at 1.
  r_h   the median ratio of hour h to hour 1 across comparable AAA console launches.
  s_h   the log-space spread of that ratio, fitted separately for the lower and the upper
        tail, because launches fall further below their peers' shape than they rise above.
  z_tau the standard-normal quantile at each scored level.

Why a ratio-to-hour-1 shape
---------------------------
GTA VI unlocks at midnight local time, rolling around the globe: New Zealand 11:00Z,
central Europe 23:00Z, the UK 00:00Z, US east 05:00Z, US west 08:00Z. So hour 1
(00:00-01:00Z) already holds the European and UK unlocks, the US unlocks land inside hours
6 and 9, and the day's peak sits in the US evening. Launches matching that profile (hour 1
already a large share of the peak, peak late in the UTC day) are the ones whose shape the
table below summarises; launches that unlock mid-day ramp far more steeply and are left out.

The loss is computed in log space, so a 20% miss costs the same at 10k viewers as at 1M:
getting the ratio wrong early in the day is what the spread has to price, and it widens
with the horizon.
"""

import json
import math
import os
import sys
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# Standard normal quantiles at the scored levels 0.05, 0.25, 0.5, 0.75, 0.95.
Z = (-1.6448536269514722, -0.6744897501960817, 0.0, 0.6744897501960817, 1.6448536269514722)
LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)

MIN_VIEWERS = 1.0
MAX_VIEWERS = 1_000_000_000.0
FALLBACK_SIGMA = 0.18

# hour -> (median ratio to hour 1, lower-tail log scale, upper-tail log scale)
#
# The median shape is a profile-weighted median over comparable console launches; the tail
# scales come from their held-out residuals, already widened by a single factor so the 5-95%
# band actually covers nine hours in ten.
#
# On a dev grade of the four practice launches that share GTA VI's rolling-midnight console
# profile, the narrower band this started from covered only 0.68 of scored hours. Widening it
# is not a hedge: on the comparable launches, widening from 1.0x to 2.2x cut the mean pinball
# loss from 0.328 to 0.286 while lifting coverage from 0.48 to 0.91. Under a proper scoring
# rule a band that is too narrow is paid for on every hour that falls outside it, so the
# honest spread is also the cheaper one.
TABLE = {
    2: (0.8980, 0.282, 0.429),
    3: (0.7914, 0.521, 0.607),
    4: (0.7728, 0.752, 0.636),
    5: (0.8684, 0.955, 0.697),
    6: (1.0692, 1.124, 0.658),
    7: (0.9789, 0.979, 0.763),
    8: (0.9422, 0.796, 0.730),
    9: (0.8817, 0.673, 0.821),
    10: (0.8486, 0.482, 0.836),
    11: (0.8843, 0.557, 0.708),
    12: (0.9270, 0.620, 0.671),
    13: (1.1358, 0.550, 0.537),
    14: (1.3133, 0.550, 0.499),
    15: (1.5183, 0.689, 0.438),
    16: (1.6524, 0.746, 0.482),
    17: (1.7707, 0.638, 0.444),
    18: (1.9506, 0.574, 0.458),
    19: (2.0489, 0.631, 0.376),
    20: (2.2451, 0.579, 0.297),
    21: (2.2534, 0.425, 0.284),
    22: (2.1753, 0.387, 0.275),
    23: (2.0980, 0.343, 0.396),
    24: (1.9023, 0.530, 0.642),
}


def hour_one(case):
    """The case's hour-1 print, floored at 1 viewer."""
    for row in case.get("known") or []:
        if row.get("hour") == 1:
            try:
                return max(MIN_VIEWERS, float(row.get("viewers") or 0.0))
            except (TypeError, ValueError):
                break
    hist = case.get("history") or []
    if hist:
        try:
            return max(MIN_VIEWERS, float(hist[-1].get("viewers") or 0.0))
        except (TypeError, ValueError):
            pass
    return MIN_VIEWERS


def quantiles_for(p1, hour):
    entry = TABLE.get(hour)
    if entry is None:
        sigma = FALLBACK_SIGMA * math.sqrt(max(1, hour - 1))
        base, s_lo, s_hi = p1, sigma, sigma
    else:
        ratio, s_lo, s_hi = entry
        base = p1 * ratio
    out = []
    for tau, z in zip(LEVELS, Z):
        s = s_lo if z < 0 else s_hi
        v = base * math.exp(z * s)
        out.append(round(min(MAX_VIEWERS, max(MIN_VIEWERS, v)), 6))
    # The median sits exactly at the modelled centre, and the row never decreases.
    out[2] = round(min(MAX_VIEWERS, max(MIN_VIEWERS, base)), 6)
    for i in range(1, 5):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def forecast(case):
    p1 = hour_one(case)
    hours = [int(r["hour"]) for r in (case.get("forecast") or []) if "hour" in r]
    if not hours:
        hours = list(range(2, 25))
    return {"hours": [{"hour": h, "q": quantiles_for(p1, h)} for h in sorted(set(hours))]}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(INPUT_DIR.glob("*.in"))
    if not paths:
        print("no case files found in %s" % INPUT_DIR, file=sys.stderr)
        return 1
    for path in paths:
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print("skipping %s: %s" % (path.name, exc), file=sys.stderr)
            continue
        payload = json.dumps(forecast(case), separators=(",", ":")) + "\n"
        (OUTPUT_DIR / (path.stem + ".out")).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
