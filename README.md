# TrueLoop: measurement-efficient optimization - reproduction code

> Repository: `[github.com/MatthewLeibel/TrueLoopPublic](https://github.com/MatthewLeibel/TrueLoopPublic/tree/Optimization)` 

Reproduce the measurement-efficient optimization results using the **live TrueLoop runtime endpoint**.
These scripts drive the real runtime (one measurement per round, model-free) against a **simulated**
objective. Swap the simulated objective for your hardware to validate on a real measurement-limited
optimization or control problem.

## What this is (and is not)

- **It is** the experiment code behind the results: the runtime calls the public endpoint, you send a
  measurement each round and receive the next configuration.
- **It is not** the runtime's internal method. That runs server-side and is not in this code. These
  scripts use only the runtime's measured input/output behaviour.

## Claim tier (please preserve when sharing results)

All numbers these scripts produce are **SIMULATED OBJECTIVE + LIVE RUNTIME**. They demonstrate the
method's behaviour, not validation on hardware. Hardware validation is the open question this code
helps answer.

## Setup

1. Get a **free evaluation key** at https://compute.neophotonics.ca/
2. Open `trueloop_client.py`, replace `YOUR_EVAL_KEY` with your key.
3. Check connectivity: `python trueloop_client.py` -> `OK - endpoint reachable and key valid.`

Pure Python 3 standard library; no dependencies.

## Run the experiments

```
# Headline: equal shared budget, runtime solves where digital collapses
python experiment_starved.py 1024 128      # n=1024, 128 measurements for every method
python experiment_starved.py 256 16        # push starvation harder
python experiment_starved.py 64 8          # near the runtime's own floor

# Advantage compounds with dimension (digital gets B=K*n, runtime capped)
python experiment_scaling.py 1024 140 10

# Tracking a moving optimum
python experiment_tracking.py 0.008        # slow drift: runtime tracks
python experiment_tracking.py 0.05         # fast drift: runtime's bandwidth limit
```

## Validate on YOUR hardware

Each experiment isolates the simulated objective in one function marked `hardware swap point`
(`measure_signal(...)`). To validate on real hardware:

1. Replace that function so it returns the **per-channel error signal** read from your device under
   the current configuration `x` (the signal that vanishes at your optimum / operating point).
2. Apply the configuration the runtime returns (`r["phi"]`) to your real control variables.
3. Keep the loop identical: measure once, send, apply the returned configuration, repeat.

The runtime needs no model of your device; it discovers the control directions from your measurements.

## Known envelope (where this is expected to work)

- **Works:** high-dimensional optimization/control where each measurement is costly (the
  measurement-starved regime); tracking slow-to-moderate moving optima.
- **Local, continuous, anytime:** a fast local optimizer toward a stationary point, not a global or
  combinatorial (NP-hard) solver. A sampling-based attempt at direct combinatorial optimization did
  not beat local search; the honest combinatorial role is operating-point control of a physical solver.
- **Bandwidth / capture / floor:** degrades under very fast target motion or large excursions, and has
  a measurement floor (order ten measurements) below which it too fails.

## Contact

https://trueloopcompute.com  ·  https://compute.neophotonics.ca/
