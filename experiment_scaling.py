"""
Reproduce: the advantage compounds with dimension. The runtime solves high-dimensional problems
using a capped number of measurements while finite-difference, given a budget that GROWS with the
problem, still stalls.

  Setup: digital gets budget B = K*n (favorable to digital). The runtime is capped at a fixed,
  modest number of measurements regardless of n, showing it converges with far fewer.

  TIER: simulated objective, real runtime. Replace measure_signal() for hardware.

Run:  python experiment_scaling.py [n] [tl_rounds] [K]   e.g.  python experiment_scaling.py 1024 140 10
"""
import math, random, sys
import trueloop_client as tl
from experiment_starved import make_instance, measure_signal, err, scalar, run_fd, run_spsa


def run_runtime_capped(n, rounds, x_star, g, seed):
    s = tl.start(n, "regulation", target=[0.0]*n, x0=[0.0]*n)
    x = list(s["phi"]); rng = random.Random(seed)
    for _ in range(rounds):
        m = measure_signal(x, x_star, g, rng)          # <-- hardware swap point
        r = tl.step(s["token"], m, target=[0.0]*n)
        x = r.get("phi") or r.get("config")
    tl.end(s["token"])
    return err(x, x_star)


if __name__ == "__main__":
    if tl.KEY == "YOUR_EVAL_KEY":
        raise SystemExit("Set your eval key in trueloop_client.py first.")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    tl_rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 140
    K = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    seed = 0xBEEF
    B = K * n
    x_star, g = make_instance(n, seed)
    print(f"n={n}: runtime capped at {tl_rounds} measurements; digital given B=K*n={B}\n")
    rt = run_runtime_capped(n, tl_rounds, x_star, g, seed)
    fd = run_fd(n, B, x_star, g, seed)
    sp = run_spsa(n, B, x_star, g, seed)
    print(f"  runtime ({tl_rounds} reads) : {rt:.4f}  {'(usable)' if rt<0.05 else ''}")
    print(f"  finite-diff ({B} reads){'':3}: {fd:.4f}  {'(usable)' if fd<0.05 else '(stalled)'}")
    print(f"  SPSA tuned  ({B} reads){'':3}: {sp:.4f}  {'(usable)' if sp<0.05 else '(stalled)'}")
    if rt < 0.05 and fd >= 0.05:
        print(f"\n  runtime solved with ~{B//tl_rounds}x fewer measurements than finite-difference's budget.")
