"""
Reproduce: the runtime does NOT mask an attack's QBER signature.

A QKD security model requires that an eavesdropper's disturbance (which raises QBER) remains
visible so the protocol can detect it and abort. This checks that TrueLoop, while correcting
benign drift, does not suppress an injected intercept-resend attack signature.

  Good outcome: during the attack window the detected QBER spikes (>11% threshold) and stays
  visible, so the protocol would abort. The runtime corrects benign drift but cannot hide the
  attack, even when the attack is coupled into the control signal.

  TIER: simulated plant + attack, real runtime. On hardware, replace measure() with your
  readout and inject a real intercept-resend test.

Run: python experiment_attack_safety.py
"""

import math, random
import trueloop_client as tl

N = 8
SIGMA = 0.01
ATTACK_QBER = 0.25        # intercept-resend on BB84 adds ~25% QBER


def run(seed, T=120, coupling=1.0):
    g = [(0.8 + 0.4 * random.Random(seed + i).random()) for i in range(N)]
    a0, a1 = T // 2, T // 2 + 20            # attack window
    attack_bias = [(0.6 if i % 2 == 0 else -0.6) for i in range(N)]
    vis = lambda phi, th: sum(math.cos(phi[i] + th[i]) for i in range(N)) / N

    target = [0.0] * N
    s = tl.start(N, "regulation", target=target, x0=[0.0] * N)
    phi = list(s["phi"]); rng = random.Random(seed); theta = [0.0] * N
    detected = []
    for t in range(T):
        for i in range(N):
            theta[i] += 0.0012 + rng.gauss(0, 0.010)     # benign drift
        attacking = (a0 <= t < a1)
        # measured control signal; optionally the attack couples into it
        m = [g[i] * math.sin(phi[i] + theta[i])
             + (coupling * attack_bias[i] if attacking else 0.0)
             + rng.gauss(0, SIGMA) for i in range(N)]
        # detected QBER = benign residual + the true attack term during the window
        q = 0.5 * (1 - max(min(vis(phi, theta), 1), -1))
        detected.append(min(0.5, q + (ATTACK_QBER if attacking else 0.0)))
        r = tl.step(s["token"], m, target=target); phi = (r.get("phi") or r.get("config"))
    tl.end(s["token"])

    w = lambda x, a, b: sum(x[a:b]) / (b - a)
    return w(detected, 5, a0), w(detected, a0, a1), w(detected, a1, T)


if __name__ == "__main__":
    if tl.KEY == "YOUR_EVAL_KEY":
        raise SystemExit("Set your eval key in trueloop_client.py first.")
    print("Attack-safety: detected QBER before / during / after an injected attack\n")
    for s in range(3):
        pre, during, post = run(0xBEEF + s)
        visible = "VISIBLE -> protocol aborts" if during > 0.11 else "MASKED (bad!)"
        print(f"  seed {s}: pre {pre:.3f}  during {during:.3f}  post {post:.3f}   [{visible}]")
