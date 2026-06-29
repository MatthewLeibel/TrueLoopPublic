"""
TrueLoop Compute - minimal client for the hosted runtime endpoint.

This calls the public TrueLoop endpoint. It does NOT contain or reveal the runtime's
internal method: you send a measurement each round and receive the next control
configuration. The runtime computes its response server-side; the method is not exposed.

Get a free evaluation key at https://compute.neophotonics.ca/ and paste it below.
"""

import json
import urllib.request

# ---------------------------------------------------------------------------
# CONFIG: paste your evaluation key here (free at https://compute.neophotonics.ca/)
# ---------------------------------------------------------------------------
KEY  = "YOUR_EVAL_KEY"                       # <-- replace with your key
BASE = "https://trueloopcompute.com"          # hosted runtime endpoint
# ---------------------------------------------------------------------------


def _post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + KEY},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def start(n, mode="regulation", target=None, x0=None, cfg=None):
    """Open a session. n = number of control channels. For drift-holding use
    mode='regulation' with a target setpoint vector and initial config x0."""
    p = {"n": n, "mode": mode}
    if target is not None: p["target"] = list(target)
    if x0 is not None:     p["x0"] = list(x0)
    if cfg:                p.update(cfg)
    return _post("/api/session/start", p)


def step(token, measurement, target=None):
    """One round: send the measurement of your plant under the current config,
    receive the next config. This is the single-measurement-per-round loop."""
    p = {"token": token, "session": token, "measurement": list(measurement)}
    if target is not None: p["target"] = list(target)
    return _post("/api/session/step", p)


def end(token):
    """Close the session."""
    try:
        return _post("/api/session/end", {"token": token, "session": token})
    except Exception:
        return None


if __name__ == "__main__":
    # smoke test: confirm your key works and the endpoint responds
    if KEY == "YOUR_EVAL_KEY":
        print("Set your evaluation key in trueloop_client.py first "
              "(free at https://compute.neophotonics.ca/).")
    else:
        s = start(2, "regulation", target=[0.5, 0.5], x0=[0.0, 0.0])
        print("session open:", s["token"][:12], "phi:", s.get("phi"))
        r = step(s["token"], [0.4, 0.6], target=[0.5, 0.5])
        print("next config:", r.get("phi") or r.get("config"))
        end(s["token"])
        print("OK - endpoint reachable and key valid.")
