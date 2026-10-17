"""Tests that run the REAL system tools (Xvfb display, PulseAudio null sink, cron, dunst, gsettings).
They need the environment prepared by tests/run-real-tool-tests.sh; otherwise each test is skipped.
These virtual devices are NOT physical hardware: they prove the wrappers drive the real tools, not that real devices work."""
import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nxsys import sysfeatures_b as B, sysfeatures_c as C
from nxsys.common import tool

ENV = os.environ.get("NX_REAL_TOOLS") == "1"


@unittest.skipUnless(ENV, "run via tests/run-real-tool-tests.sh")
class R(unittest.TestCase):
    def test_screenshot_real_png(self):
        p = os.path.join(tempfile.mkdtemp(), "s.png"); r = C.screenshot(p)
        self.assertTrue(r["ok"], r); self.assertEqual(open(p, "rb").read(8), b"\x89PNG\r\n\x1a\n")

    def test_display_manager_lists_xvfb_output(self):
        r = C.displays(); self.assertTrue(r["available"], r); self.assertTrue(r["outputs"])

    def test_screen_recorder_real_video(self):
        p = os.path.join(tempfile.mkdtemp(), "r.mp4"); c = C.record_command(p, seconds=2)
        self.assertTrue(c["available"], c)
        r = subprocess.run(c["argv"], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-300:]); self.assertGreater(os.path.getsize(p), 1000)

    def test_audio_mixer_null_sink(self):
        s = C.audio_sinks(); self.assertTrue(s["available"], s); self.assertIn("nxtest", s["sinks"])
        r = C.set_volume("nxtest", 60); self.assertEqual(r["rc"], 0, r)
        out = subprocess.run(["pactl", "get-sink-volume", "nxtest"], capture_output=True, text=True).stdout
        self.assertIn("60%", out)
        with self.assertRaises(ValueError): C.set_volume("nxtest", 999)

    def test_task_scheduler_real_crontab(self):
        before = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        try:
            with self.assertRaises(PermissionError): C.add_task("5 4 * * *", "echo nx-test")
            self.assertEqual(C.add_task("5 4 * * *", "echo nx-test", confirm=True)["rc"], 0)
            self.assertIn("5 4 * * * echo nx-test", C.list_tasks()["tasks"])
        finally:
            if before.returncode == 0: subprocess.run(["crontab", "-"], input=before.stdout, text=True)
            else: subprocess.run(["crontab", "-r"], capture_output=True)

    def test_font_manager_real(self):
        self.assertIn("DejaVu Sans", B.list_fonts()["families"])
        d = tempfile.mkdtemp(); src = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        with self.assertRaises(PermissionError): B.install_font(src, d)
        self.assertEqual(B.install_font(src, d, confirm=True)["installed"], "DejaVuSans.ttf"); self.assertTrue(os.path.exists(os.path.join(d, "DejaVuSans.ttf")))

    def test_notification_really_delivered(self):
        n = C.Notifications(os.path.join(tempfile.mkdtemp(), "n.log")); e = n.send("NX test", "body")
        self.assertTrue(e["delivered"], e)

    def test_accessibility_gsettings(self):
        r = C.a11y_status(); self.assertTrue(r["available"]); self.assertIn(r["settings"]["high_contrast"], ("false", "true"))

    def test_usb_and_default_app_run(self):
        self.assertTrue(C.usb_devices()["available"]); self.assertTrue(B.default_app("text/plain")["available"])


if __name__ == "__main__":
    unittest.main()
