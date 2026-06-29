"""
Reproduce: secure key rate under drift, TrueLoop closed loop vs open loop.

This is the headline PQC-QKD result. It holds a (simulated) QKD modulator/interferometer
bias at its lock point under drift, using the TrueLoop runtime at one measurement per round,
and computes the BB84 secure key fraction r = 1 - 2 h(QBER).

  TIER: the PLANT here is simulated. The RUNTIME is the real hosted endpoint.
  To validate on hardware: replace `measure_plant()` with a real QBER/visibility readout
  from your QKD link, and apply the returned config to your real bias controls.

Run:
  1. put your eval key in trueloop_client.py
  2. python experiment_qkd_keyrate.py
"""

import math
import random
import trueloop_client as tl

N = 8                 # number of bias channels
T = 100               # rounds
SIGMA = 0.01          # readout noise


def h(q):
    q = min(max(q, 1e-9), 1 - 1e-9)
    return -(q * math.log2(q) + (1 - q) * math.log2(1 - q))


def key_fraction(qber):
    """BB84 asymptotic secure key fraction."""
    return max(0.0, 1 - 2 * h(qber))


# ---------------------------------------------------------------------------
# SIMULATED PLANT.  Replace this whole function with your hardware readout to
# validate on a real QKD link.  It must return, for the given control config
# `phi`, the per-channel error signal the runtime regulates toward zero.
# ---------------------------------------------------------------------------
def measure_plant(phi, theta, g, rng):
    # error signal at the (sensitive) quadrature lock point: g_i * sin(phi_i + drift_i)
    return [g[i] * math.sin(phi[i] + theta[i]) + rng.gauss(0, SIGMA)
            for i in range(N)]


def visibility(phi, theta):
    return sum(math.cos(phi[i] + theta[i]) for i in range(N)) / N


def qber(phi, theta):
    return 0.5 * (1 - max(min(visibility(phi, theta), 1), -1))


def run_one(seed, drift_severity=5.0):
    """One paired run: same drift realization for open loop and TrueLoop."""
    base_ramp, base_rw = 0.0011, 0.013
    ramp, rw = base_ramp * drift_severity, base_rw * drift_severity
    g = [(0.8 + 0.4 * random.Random(seed + i).random()) for i in range(N)]
    phi_star = [0.0] * N                       # locked at quadrature

    # --- open loop: bias frozen, drift accumulates ---
    rng = random.Random(seed); theta = [0.0] * N
    ol_key = []
    for _ in range(T):
        for i in range(N):
            theta[i] += ramp + rng.gauss(0, rw)
        ol_key.append(key_fraction(qber(phi_star, theta)))

    # --- TrueLoop: regulate bias toward lock, one measurement per round ---
    target = [0.0] * N
    s = tl.start(N, "regulation", target=target, x0=phi_star)
    phi = list(s["phi"]); rng = random.Random(seed); theta = [0.0] * N
    tl_key = []
    for _ in range(T):
        for i in range(N):
            theta[i] += ramp + rng.gauss(0, rw)
        m = measure_plant(phi, theta, g, rng)          # <-- hardware swap point
        tl_key.append(key_fraction(qber(phi, theta)))
        r = tl.step(s["token"], m, target=target)
        phi = r.get("phi") or r.get("config")
    tl.end(s["token"])

    w = 80
    mean = lambda x: sum(x[-w:]) / w
    alive = lambda x: sum(1 for v in x[-w:] if v > 0) / w
    return mean(ol_key), mean(tl_key), alive(ol_key), alive(tl_key)


if __name__ == "__main__":
    if tl.KEY == "YOUR_EVAL_KEY":
        raise SystemExit("Set your eval key in trueloop_client.py first.")
    seeds = 5
    print(f"Secure key rate under drift  (N={N}, T={T}, {seeds} seeds)")
    print(f"{'seed':>4} | {'open key':>8} | {'TL key':>7} | {'open alive':>10} | {'TL alive':>9}")
    ok = tk = oa = ta = 0.0
    for s in range(seeds):
        a, b, c, d = run_one(0xBEEF + s)
        ok += a; tk += b; oa += c; ta += d
        print(f"{s:>4} | {a:>8.3f} | {b:>7.3f} | {c*100:>9.0f}% | {d*100:>8.0f}%")
    n = seeds
    print("-" * 52)
    print(f"mean secure key fraction:  open {ok/n:.3f}   TrueLoop {tk/n:.3f}")
    print(f"link producing key:        open {oa/n*100:.0f}%    TrueLoop {ta/n*100:.0f}%")
