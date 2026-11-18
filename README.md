# gta6-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Yanu403/gta6-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Yanu403/gta6-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

An hourly quantile forecast of Grand Theft Auto VI's launch-day Twitch concurrent viewers,
entered in make.fun's "Forecast GTA VI's launch-day Twitch viewers hour by hour" bounty.

## What it does

Twitch's category page for a game shows one number: how many people are watching its live
streams at once. This program forecasts that number for each hour of GTA VI's release day.

At the checkpoint — midnight UTC, the end of the day's first hour — the only observation is
hour 1's viewer count. Everything after it has to come from a model. The program turns that
one number into 23 hourly distributions:

    q_tau(h) = p1 * r_h * exp(z_tau * s_h)

`r_h` is the median ratio of hour *h* to hour 1 across comparable AAA console launches, and
`s_h` is the spread of that ratio, fitted separately for the lower and upper tail. Reporting
five quantiles rather than a point estimate is what the contest scores: the pinball loss is
a proper scoring rule, so the honest answer is the spread you actually believe.

## Why this shape

GTA VI unlocks at midnight local time, rolling around the world: New Zealand at 11:00Z,
central Europe at 23:00Z, the UK at 00:00Z, the US east coast at 05:00Z and the west coast at
08:00Z. By the end of hour 1 the European and UK unlocks have already happened, so hour 1 is
a large share of the day's peak rather than a cold start. The US unlocks arrive inside hours
6 and 9, and the peak lands in the US evening, around hour 21.

So the curve dips through the North American small hours, climbs through the afternoon and
peaks near twice hour 1's count in the evening. Launches that unlock in the middle of the UTC
day ramp far more steeply from a near-zero base; their shape would badly mispredict a launch
that is already running at midnight, and they are excluded from the fit.

## Results

Fitted and validated by leave-one-out over the comparable launches: hold one launch out, fit
the shape on the others that share its profile, score the held-out one exactly as the
contest scores. On those folds:

| model | pinball loss | 90% coverage |
|---|---|---|
| house baseline (persistence) | 0.387 | 0.78 |
| this model | **0.129** | 0.89 |

An honest forecast should cover about nine hours in ten, which is where this lands. The
optimum is flat — moving the bandwidth or the spread scale by 10% moves the loss by under
0.003 — so the numbers are not tuned to a single split. A forecast made on past launches
need not hold on GTA VI's own release day, which will be unlike any of them.

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` reads every `<id>.in` in the input directory and writes `<id>.out`: JSON with one
key, `hours`, listing hours 2 to 24, each with its five quantiles at the 5%, 25%, 50%, 75%
and 95% levels. Standard library only, no network, no randomness, well under a second.

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
