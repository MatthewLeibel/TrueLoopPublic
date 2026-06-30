"""
TrueLoop Compute - minimal client for the hosted runtime endpoint.

Calls the public TrueLoop endpoint. Does NOT contain or reveal the runtime's internal method:
you send a measurement each round and receive the next control configuration. The runtime computes
its response server-side; the method is not exposed.

Get a free evaluation key at https://compute.neophotonics.ca/ and paste it below.
"""
import json
import urllib.request

# ---------------------------------------------------------------------------
# CONFIG: paste your evaluation key (free at https://compute.neophotonics.ca/)
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
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def start(n, mode="regulation", target=None, x0=None):
    """Open a session over n control channels. For optimization toward a stationary point,
    use mode='regulation' with target = the per-channel signal value at the optimum (often 0)."""
    p = {"n": n, "mode": mode}
    if target is not None: p["target"] = list(target)
    if x0 is not None:     p["x0"] = list(x0)
    return _post("/api/session/start", p)


def step(token, measurement, target=None):
    """One round: send the measured per-channel signal under the current configuration, receive the
    next configuration. This is the single-measurement-per-round loop."""
    p = {"token": token, "session": token, "measurement": list(measurement)}
    if target is not None: p["target"] = list(target)
    return _post("/api/session/step", p)


def end(token):
    try:
        return _post("/api/session/end", {"token": token, "session": token})
    except Exception:
        return None


if __name__ == "__main__":
    if KEY == "YOUR_EVAL_KEY":
        print("Set your evaluation key in trueloop_client.py first "
              "(free at https://compute.neophotonics.ca/).")
    else:
        s = start(4, "regulation", target=[0.0]*4, x0=[0.0]*4)
        r = step(s["token"], [0.1, -0.1, 0.05, 0.0], target=[0.0]*4)
        end(s["token"])
        print("OK - endpoint reachable and key valid.")
