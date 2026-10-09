#!/usr/bin/env python3
"""nx-ai: command line front end for the NX AI layer (Brok adapter). usage: nx-ai doctor | ask "text".
NX_AI_DISABLED=1 turns the AI layer off completely. Never runs as root; Brok lives in /opt/brok by default."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from ai.service.brok_adapter import BrokAdapter  # noqa: E402


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if not a or a[0] not in ("doctor", "ask") or (a[0] == "ask" and len(a) < 2):
        print('usage: nx-ai doctor | nx-ai ask "question"'); return 2
    ad = BrokAdapter(brok_dir=os.environ.get("NX_BROK_DIR", "/opt/brok"), enabled=os.environ.get("NX_AI_DISABLED") != "1")
    st, out = ad.call("doctor") if a[0] == "doctor" else ad.call("ask", " ".join(a[1:]))
    print(out if st == "ok" else "[%s] %s" % (st, out.strip()))
    return 0 if st == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
