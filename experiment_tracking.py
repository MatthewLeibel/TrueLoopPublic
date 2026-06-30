"""
Reproduce: tracking a MOVING optimum. The objective's optimum drifts over time; the runtime must
continuously re-converge to it (it only sees the measured signal, not the optimum location).
Compared to periodic digital re-optimization and to open-loop (frozen).

  TIER: simulated objective, real runtime. Replace measure_signal() for hardware.

Run:  python experiment_tracking.py [drift_speed]   e.g.  python experiment_tracking.py 0.008
"""
import math, random, sys
import trueloop_client as tl

SIG = 0.01; T = 140


def run(drift_speed, seed=0xBEEF):
    n = 16
    g = [0.8 + 0.4*random.Random(seed+i).random() for i in range(n)]
    rng = random.Random(seed ^ 0x5); cur = [0.5 + 0.5*rng.random() for _ in range(n)]
    rw = random.Random(seed ^ 0x9); path = []
    for _ in range(T):
        for i in range(n): cur[i] += drift_speed + rw.gauss(0, drift_speed*0.5)
        path.append(cur[:])

    def dist(x, xs): return (sum((x[i]-xs[i])**2 for i in range(n))/n) ** 0.5

    # runtime: one measurement per round
    s = tl.start(n, "regulation", target=[0.0]*n, x0=[0.0]*n)
    x = list(s["phi"]); rngm = random.Random(seed); ds = []
    for t in range(T):
        xs = path[t]
        m = [g[i]*math.sin(x[i]-xs[i]) + rngm.gauss(0, SIG) for i in range(n)]   # hardware swap point
        ds.append(dist(x, xs))
        r = tl.step(s["token"], m, target=[0.0]*n); x = r.get("phi") or r.get("config")
    tl.end(s["token"]); tl_d = sum(ds[-80:])/80

    # open loop: perfectly placed at t=0 then frozen
    x0 = list(path[0]); op_d = sum(dist(x0, path[t]) for t in range(T-80, T))/80

    # periodic digital re-optimization (same measurement currency, expensive bursts)
    rngd = random.Random(seed); xd = [0.0]*n; eps = 0.05; lr = 0.4; dd = []
    for t in range(T):
        xs = path[t]
        if t % 20 == 0:
            for _ in range(15):
                base = [g[i]*math.sin(xd[i]-xs[i]) for i in range(n)]
                for j in range(n):
                    xp = list(xd); xp[j] += eps
                    mp = g[j]*math.sin(xp[j]-xs[j])
                    xd[j] -= lr*((mp-base[j])/eps)*base[j]
        dd.append(dist(xd, xs))
    dg_d = sum(dd[-80:])/80
    return tl_d, dg_d, op_d


if __name__ == "__main__":
    if tl.KEY == "YOUR_EVAL_KEY":
        raise SystemExit("Set your eval key in trueloop_client.py first.")
    v = float(sys.argv[1]) if len(sys.argv) > 1 else 0.008
    tl_d, dg_d, op_d = run(v)
    print(f"optimum drift speed = {v}\n")
    print(f"  runtime (1 read/round)       : {tl_d:.4f}")
    print(f"  periodic digital re-opt      : {dg_d:.4f}")
    print(f"  open loop (frozen)           : {op_d:.4f}")
    if tl_d < dg_d:
        print(f"\n  runtime tracks the moving optimum better, using fewer measurements.")
    else:
        print(f"\n  at this drift speed the optimum moves too fast for the runtime (bandwidth limit).")
