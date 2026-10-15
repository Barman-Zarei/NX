"""Feature 23 NX Network Diagnostics: real checks; distinguishes 'tool missing' from 'check failed'."""
import shutil, socket, subprocess


def dns(host="archive.ubuntu.com"):
    try:
        return {"check": "dns", "status": "pass", "detail": socket.gethostbyname(host)}
    except OSError as e:
        return {"check": "dns", "status": "fail", "detail": str(e)}


def tcp(host, port, timeout=3):
    try:
        socket.create_connection((host, port), timeout=timeout).close(); return {"check": "tcp %s:%d" % (host, port), "status": "pass"}
    except OSError as e:
        return {"check": "tcp %s:%d" % (host, port), "status": "fail", "detail": str(e)}


def interfaces():
    ip = shutil.which("ip")
    if not ip:
        return {"check": "interfaces", "status": "tool_unavailable", "detail": "`ip` not installed"}
    r = subprocess.run([ip, "-brief", "address"], capture_output=True, text=True)
    return {"check": "interfaces", "status": "pass" if r.returncode == 0 else "fail", "detail": r.stdout.strip() or r.stderr.strip()}


def routes():
    ip = shutil.which("ip")
    if not ip: return {"check": "routes", "status": "tool_unavailable"}
    r = subprocess.run([ip, "route"], capture_output=True, text=True)
    return {"check": "routes", "status": "pass" if "default" in r.stdout else "fail", "detail": r.stdout.strip() or "no default route"}


def run_all():
    return [interfaces(), routes(), dns(), tcp("archive.ubuntu.com", 80)]
