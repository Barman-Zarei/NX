mytool.py uses `match`, str.removeprefix and `int | None` (Python 3.10+). Build the test input once (Windows Python 3.11 + PyInstaller, e.g. under Wine):
  python.exe -m PyInstaller --onefile --name mytool mytool.py      # then: NXAT_SLOW=1 NXAT_PYSAMPLE=dist/mytool.exe NXAT_WINPY38=.../python.exe NXAT_WINE=1 python3 -m unittest tests.test_nxat.FrozenPython
mytool_py38.py is the Python-3.8 version the fake Brok returns.
