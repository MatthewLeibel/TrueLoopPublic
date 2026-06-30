"""
Reproduce: the headline result. Under an EQUAL shared measurement budget, the runtime keeps solving
a high-dimensional optimization problem where finite-difference, SPSA, and random search collapse.

  Fairness: every method gets the SAME total number of objective evaluations B. The runtime runs B
  rounds (one measurement each); the digital baselines spend B across their evaluations per step.
  No wall-clock budget. "usable" = within tau=0.05 of the optimum.

  TIER: the OBJECTIVE here is simulated. The RUNTIME is the real hosted endpoint.
  To validate on hardware: replace measure_signal() with the per-channel error signal read from
  your real device under the current configuration, and apply the returned configuration.

Run:  python experiment_starved.py [n] [B]      e.g.  python experiment_starved.py 1024 128
"""
import math, random, sys
import trueloop_client as tl

SIG = 0.01   # measurement noise


def make_instance(n, seed):
    rng = random.Random(seed ^ 0x99)
    x_star = [0.4 + 0.9 * rng.random() for _ in range(n)]
    g = [0.8 + 0.4 * random.Random(seed + i).random() for i in range(n)]
    return x_star, g


# ---------------------------------------------------------------------------
# SIMULATED OBJECTIVE.  Replace this with your hardware readout to validate.
# Returns the per-channel error signal that vanishes at the optimum.
# ---------------------------------------------------------------------------
def measure_signal(x, x_star, g, rng):
    return [g[i] * math.sin(x[i] - x_star[i]) + rng.gauss(0, SIG) for i in range(len(x))]


def err(x, x_star):
    n = len(x)
    return (sum((x[i] - x_star[i])**2 for i in range(n)) / n) ** 0.5


def scalar(x, x_star, g, rng):
    s = measure_signal(x, x_star, g, rng)
    return sum(v*v for v in s)


def run_runtime(n, B, x_star, g, seed):
    s = tl.start(n, "regulation", target=[0.0]*n, x0=[0.0]*n)
    x = list(s["phi"]); rng = random.Random(seed)
    for _ in range(B):
        m = measure_signal(x, x_star, g, rng)          # <-- hardware swap point
        r = tl.step(s["token"], m, target=[0.0]*n)
        x = r.get("phi") or r.get("config")
    tl.end(s["token"])
    return err(x, x_star)


def run_fd(n, B, x_star, g, seed):
    rng = random.Random(seed); x = [0.0]*n; eps = 0.05; lr = 0.4; ev = 0
    while ev + (n+1) <= B:
        base = measure_signal(x, x_star, g, rng); ev += 1
        grad = [0.0]*n
        for j in range(n):
            xp = list(x); xp[j] += eps
            mp = measure_signal(xp, x_star, g, rng); ev += 1
            grad[j] = ((mp[j]-base[j])/eps) * base[j]
        x = [x[j] - lr*grad[j] for j in range(n)]
    return err(x, x_star)


def run_spsa(n, B, x_star, g, seed):
    rng = random.Random(seed); x = [0.0]*n; ev = 0; k = 0
    a = 0.3; c = 0.1; A_ = 10; alpha = 0.602; gamma = 0.101
    while ev + 2 <= B:
        ak = a/((k+1+A_)**alpha); ck = c/((k+1)**gamma)
        d = [1 if rng.random() < 0.5 else -1 for _ in range(n)]
        yp = scalar([x[i]+ck*d[i] for i in range(n)], x_star, g, rng); ev += 1
        ym = scalar([x[i]-ck*d[i] for i in range(n)], x_star, g, rng); ev += 1
        gh = [(yp-ym)/(2*ck*d[i]) for i in range(n)]
        x = [x[i]-ak*gh[i] for i in range(n)]; k += 1
    return err(x, x_star)


def run_random(n, B, x_star, g, seed):
    rng = random.Random(seed); best = None; bx = [0.0]*n
    for _ in range(B):
        c = [2.0*rng.random() for _ in range(n)]; v = scalar(c, x_star, g, rng)
        if best is None or v < best: best = v; bx = c
    return err(bx, x_star)


if __name__ == "__main__":
    if tl.KEY == "YOUR_EVAL_KEY":
        raise SystemExit("Set your eval key in trueloop_client.py first.")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    B = int(sys.argv[2]) if len(sys.argv) > 2 else 128
    seed = 0xBEEF
    x_star, g = make_instance(n, seed)
    print(f"n={n}, shared budget B={B} (same for every method), tau=0.05\n")
    rt = run_runtime(n, B, x_star, g, seed)
    fd = run_fd(n, B, x_star, g, seed)
    sp = run_spsa(n, B, x_star, g, seed)
    rd = run_random(n, B, x_star, g, seed)
    usable = [nm for nm, v in [("runtime", rt), ("FD", fd), ("SPSA", sp), ("random", rd)] if v < 0.05]
    print(f"  runtime       : {rt:.4f}  {'(usable)' if rt<0.05 else ''}")
    print(f"  finite-diff   : {fd:.4f}  {'(usable)' if fd<0.05 else '(stalled)'}")
    print(f"  SPSA (tuned)  : {sp:.4f}  {'(usable)' if sp<0.05 else '(stalled)'}")
    print(f"  random search : {rd:.4f}  {'(usable)' if rd<0.05 else '(stalled)'}")
    print(f"\n  usable methods: {', '.join(usable) if usable else 'NONE'}")
