# TrueLoop x PQC-QKD: reproduction code

Reproduce the PQC-QKD physical-layer stabilization results using the **live TrueLoop runtime
endpoint**. These scripts drive the real runtime (one measurement per round, model-free) against
a **simulated** QKD/QRNG plant. Swap the simulated plant for your hardware to validate on a real
entropy source or QKD link.

## What this is (and what it is not)

- **It is** the exact experiment code that produced our simulation results, calling the public
  runtime endpoint. You send a measurement each round and receive the next control configuration.
- **It is not** the runtime's internal method. That runs server-side and is not in this code.
  These scripts only use the runtime's measured input/output behaviour.

## Claim tier (please preserve this when sharing results)

All numbers these scripts produce are **SIMULATED PLANT + LIVE RUNTIME**. They demonstrate the
control law's behaviour, not validation on real QKD hardware. Hardware validation is the open
question this code is meant to help answer.

## Setup

1. Get a **free evaluation key** at https://compute.neophotonics.ca/
2. Open `trueloop_client.py` and replace `YOUR_EVAL_KEY` with your key.
3. Check connectivity:
   ```
   python trueloop_client.py
   ```
   You should see `OK - endpoint reachable and key valid.`

Requires only Python 3 standard library (no dependencies).

## Run the experiments

```
python experiment_qkd_keyrate.py        # headline: secure key rate + link uptime under drift
python experiment_qkd_suite.py A        # QRNG entropy bias stabilization
python experiment_qkd_suite.py B        # QKD modulator/interferometer bias lock
python experiment_qkd_suite.py C        # polarization / state-alignment hold
python experiment_attack_safety.py      # runtime does not mask an attack's QBER signature
```

## Validate on YOUR hardware

Each experiment isolates the simulated plant in one place, marked `hardware swap point` /
`measure_plant()` / `measure()`. To validate on real hardware:

1. Replace that function so it returns the **per-channel error signal** read from your real
   device under the current control configuration `phi`.
2. Apply the configuration the runtime returns (`r["phi"]`) to your real control variables
   (modulator bias, phase shifter, polarization controller, etc.).
3. Keep the loop structure identical: measure once, send, apply the returned config, repeat.

The runtime never needs a model of your device; it discovers the control directions from your
measurements.

## Known envelope (where this is expected to work)

- **Works:** slow-to-moderate drift on a single link where each measurement is costly.
- **Does not scale** with channel count (the per-link QKD objective is forgiving).
- **Bandwidth / capture-range limited:** degrades under fast structured drift or large sudden
  excursions; pair with coarse re-acquisition for big jumps.

## Contact

https://trueloopcompute.com  ·  https://compute.neophotonics.ca/
