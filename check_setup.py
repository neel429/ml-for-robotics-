# check_setup.py  --  click the Run (play) button in VS Code to run me.
#
# This one file confirms all three things you were asked to install:
#   1. VS Code works        (it opened this file and ran it)
#   2. Python is installed   (the version prints below)
#   3. The Python extension  (the Run button that started this only
#                             appears when the extension is active)
#
# If it prints "Setup looks good", you are ready to create a virtual
# environment and install the course packages.

import sys
import platform

print("=" * 44)
print("Python version :", platform.python_version())
print("Executable     :", sys.executable)
print("Platform       :", platform.platform())
print("=" * 44)

ok = True

major, minor = sys.version_info[:2]
if (major, minor) == (3, 14):
    print("[ok] Python 3.14.x is running.")
else:
    ok = False
    print(f"[!!] Expected Python 3.14.x but found {major}.{minor}.")
    print("     Reinstall Python 3.14.6 from python.org and tick")
    print("     'Add python.exe to PATH' on the first installer screen.")

try:
    import pip  # noqa: F401
    print("[ok] pip is available.")
except ImportError:
    ok = False
    print("[!!] pip is missing -- reinstall Python with pip included.")

print("=" * 44)
if ok:
    print("Setup looks good. You can create your virtual environment next.")
else:
    print("Fix the [!!] items above, then run this file again.")
print("=" * 44)
