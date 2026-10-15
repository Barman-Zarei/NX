"""nxcs command line: analyze | search | git-status | test | pipeline | ask"""
import argparse, json, sys
from . import intel, workspace, testintel, pipeline, gitcc, claude


def main(argv=None):
    ap = argparse.ArgumentParser(prog="nxcs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("analyze", "git-status", "test"):
        sub.add_parser(n).add_argument("root", nargs="?", default=".")
    s = sub.add_parser("search"); s.add_argument("pattern"); s.add_argument("root", nargs="?", default=".")
    p = sub.add_parser("pipeline"); p.add_argument("workflow")
    a = sub.add_parser("ask"); a.add_argument("prompt")
    args = ap.parse_args(argv)
    if args.cmd == "analyze":
        print(json.dumps(intel.analyze(args.root), indent=2, ensure_ascii=False))
    elif args.cmd == "search":
        for f, n, l in workspace.search(args.root, args.pattern):
            print("%s:%d:%s" % (f, n, l))
    elif args.cmd == "git-status":
        print(json.dumps(gitcc.Repo(args.root).status(), indent=2))
    elif args.cmd == "test":
        r = testintel.run_unittest(args.root); print(r["output"]); return 0 if r["ok"] else 1
    elif args.cmd == "pipeline":
        print(json.dumps(pipeline.inspect(args.workflow), indent=2))
    elif args.cmd == "ask":
        try:
            r = claude.Client().ask(args.prompt); print("[source=%s]\n%s" % (r["source"], r["text"]))
        except claude.ClaudeError as e:
            print("error (%s): %s" % (e.kind, e)); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
