"""Validates compatibility/database/apps.json. A 'tested'/'verified' entry must name an NX version and a date."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def validate(apps=None):
    schema = json.load(open(os.path.join(HERE, "database", "schema.json")))
    apps = apps if apps is not None else json.load(open(os.path.join(HERE, "database", "apps.json")))
    errors = []
    for i, a in enumerate(apps):
        for k in schema["required"]:
            if k not in a:
                errors.append("%d: missing %s" % (i, k))
        if a.get("method") not in schema["methods"]:
            errors.append("%d: bad method" % i)
        if a.get("status") not in schema["statuses"]:
            errors.append("%d: bad status" % i)
        if a.get("status") in ("tested", "verified") and (a.get("tested_nx") in (None, "", "none") or a.get("last_verified") in (None, "", "never")):
            errors.append("%d: tested/verified needs tested_nx and last_verified" % i)
    return errors


if __name__ == "__main__":
    e = validate(); print("\n".join(e) or "OK"); sys.exit(1 if e else 0)
