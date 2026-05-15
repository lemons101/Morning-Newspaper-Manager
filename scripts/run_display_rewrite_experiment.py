# Backward-compatibility wrapper.
# Formal entrypoint: scripts/build_display_publish_input.py
import os
import sys

TARGET = '/root/projects/Morning-Newspaper-Manager/scripts/build_display_publish_input.py'
os.execv(sys.executable, [sys.executable, TARGET, *sys.argv[1:]])
