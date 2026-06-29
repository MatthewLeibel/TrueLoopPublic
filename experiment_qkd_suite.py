"""
Reproduce: the PQC-QKD control-layer suite under drift.
  A. QRNG entropy bias stabilization (hold source at p=0.5)
  B. QKD modulator/interferometer bias lock
  C. Polarization / state-alignment hold

All three drive the real TrueLoop endpoint at one measurement per round against a
SIMULATED plant. Replace each measure_* function with your hardware readout to validate.

Run:
  python experiment_qkd_suite.py A     # or B, or C
"""

import math, random, sys
import trueloop_client as tl

T = 100
SIGMA = 0.01


# ----- A. QRNG entropy bias --------------------------------------------------
def vn_yield(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))

def run_A(seed):
    ramp, rw, shots = 0.0014, 0.006, 120
    # open loop
    rng = random.Random(seed ^ 10); p = 0.5; ob = []; oy = []
    for _ in range(T):
        p += ramp + rng.gauss(0, rw); p = min(max(p, 0), 1)
        ob.append(abs(p - 0.5)); oy.append(vn_yield(p))
    # TrueLoop: regulate bias toward p=0.5
    s = tl.start(1, "regulation", target=[0.5], x0=[0.0])
    rng = random.Random(seed ^ 10); pd = 0.5; c = s["phi"][0]; tb = []; ty = []
    for _ in range(T):
        pd += ramp + rng.gauss(0, rw); pd = min(max(pd, 0), 1)
        pa = min(max(pd - c, 0), 1)
        # SIMULATED measurement (binomial shot estimate). Hardware swap point:
        k = sum(1 for _ in range(shots) if rng.random() < pa); meas = k / shots
        tb.append(abs(pa - 0.5)); ty.append(vn_yield(pa))
        r = tl.step(s["token"], [meas], target=[0.5]); c = (r.get("phi") or r.get("config"))[0]
    tl.end(s["token"])
    w = 80; mean = lambda x: sum(x[-w:]) / w
    return ("QRNG entropy bias", mean(ob), mean(tb), mean(oy), mean(ty))


# ----- B. QKD bias lock ------------------------------------------------------
def run_B(seed):
    n = 8; ramp, rw = 0.0011, 0.013
    g = [(0.8 + 0.4 * random.Random(seed + i).random()) for i in range(n)]
    rms = lambda v: (sum(x * x for x in v) / len(v)) ** 0.5
    phi_star = [0.0] * n
    rng = random.Random(seed); theta = [0.0] * n; oe = []
    for _ in range(T):
        for i in range(n): theta[i] += ramp + rng.gauss(0, rw)
        oe.append(rms([g[i] * math.sin(phi_star[i] + theta[i]) for i in range(n)]))
    target = [0.0] * n
    s = tl.start(n, "regulation", target=target, x0=phi_star)
    phi = list(s["phi"]); rng = random.Random(seed); theta = [0.0] * n; te = []
    for _ in range(T):
        for i in range(n): theta[i] += ramp + rng.gauss(0, rw)
        m = [g[i] * math.sin(phi[i] + theta[i]) + rng.gauss(0, SIGMA) for i in range(n)]
        te.append(rms([g[i] * math.sin(phi[i] + theta[i]) for i in range(n)]))
        r = tl.step(s["token"], m, target=target); phi = (r.get("phi") or r.get("config"))
    tl.end(s["token"])
    w = 80; mean = lambda x: sum(x[-w:]) / w
    return ("QKD bias lock (visibility error)", mean(oe), mean(te), None, None)


# ----- C. Polarization hold --------------------------------------------------
def run_C(seed):
    n = 8; ramp, rw = 0.0009, 0.011
    rng = random.Random(seed ^ 0x55)
    phi_star = [0.5 + 0.6 * rng.random() for _ in range(n)]
    g = [(0.8 + 0.4 * random.Random(seed + i + 7).random()) for i in range(n)]
    target = [g[i] * math.sin(phi_star[i]) for i in range(n)]
    rms = lambda v, t: (sum((v[i] - t[i]) ** 2 for i in range(n)) / n) ** 0.5
    fid = lambda phi, th: sum(max(0, math.cos(phi[i] + th[i] - phi_star[i])) for i in range(n)) / n
    rng = random.Random(seed); theta = [0.0] * n; oe = []; of = []
    for _ in range(T):
        for i in range(n): theta[i] += ramp + rng.gauss(0, rw)
        oe.append(rms([g[i] * math.sin(phi_star[i] + theta[i]) for i in range(n)], target))
        of.append(fid(phi_star, theta))
    s = tl.start(n, "regulation", target=target, x0=phi_star)
    phi = list(s["phi"]); rng = random.Random(seed); theta = [0.0] * n; te = []; tf = []
    for _ in range(T):
        for i in range(n): theta[i] += ramp + rng.gauss(0, rw)
        m = [g[i] * math.sin(phi[i] + theta[i]) + rng.gauss(0, SIGMA) for i in range(n)]
        te.append(rms([g[i] * math.sin(phi[i] + theta[i]) for i in range(n)], target))
        tf.append(fid(phi, theta))
        r = tl.step(s["token"], m, target=target); phi = (r.get("phi") or r.get("config"))
    tl.end(s["token"])
    w = 80; mean = lambda x: sum(x[-w:]) / w
    return ("Polarization hold (alignment error)", mean(oe), mean(te), mean(of), mean(tf))


if __name__ == "__main__":
    if tl.KEY == "YOUR_EVAL_KEY":
        raise SystemExit("Set your eval key in trueloop_client.py first.")
    which = (sys.argv[1].upper() if len(sys.argv) > 1 else "A")
    fn = {"A": run_A, "B": run_B, "C": run_C}[which]
    seeds = 5
    print(f"Experiment {which}, {seeds} seeds, live runtime / simulated plant\n")
    for s in range(seeds):
        name, oe, te, ox, tx = fn(0xBEEF + s)
        line = f"  seed {s}: {name}: open {oe:.4f} -> TrueLoop {te:.4f}  ({oe/max(te,1e-9):.1f}x)"
        if ox is not None:
            line += f"  | secondary open {ox:.3f} -> TL {tx:.3f}"
        print(line)
