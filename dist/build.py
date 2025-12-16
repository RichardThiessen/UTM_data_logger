#!/usr/bin/env python
"""
UTM Data Logger - Build Script
Assembles the application into a distributable zip file.

Uses python32_base.zip as a starting point (contains portable Python 3.4.4)
and appends the application files plus everything in the package/ directory.
"""
from __future__ import print_function

import os
import sys
import shutil
import zipfile
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BUILD_NAME = "UTM_Data_Logger"
PYTHON_BASE_ZIP = "python32_base.zip"
PACKAGE_DIR = "package"


def build():
    app_dir = os.path.join(PROJECT_ROOT, 'app')
    base_zip_path = os.path.join(SCRIPT_DIR, PYTHON_BASE_ZIP)

    # Check for required directories
    if not os.path.isdir(app_dir):
        print("ERROR: app/ directory not found at", app_dir)
        return 1

    # Check for base Python zip
    if not os.path.isfile(base_zip_path):
        print("WARNING: {} not found.".format(PYTHON_BASE_ZIP))
        print("         Windows users will need a Python interpreter.")
        print()
        print("To create {}:".format(PYTHON_BASE_ZIP))
        print("  1. Install Python 3.4.4 (32-bit) on Windows")
        print("  2. Copy the install directory (e.g., C:\\Python34)")
        print("  3. Add python34.dll and msvcr100.dll to the directory")
        print("  4. Remove unnecessary dirs: Doc, include, libs, Tools, Scripts")
        print("  5. Create zip with structure: {}/python32/...".format(BUILD_NAME))
        print()
        include_python = False
    else:
        include_python = True

    # Create output filename
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_filename = "{}_{}.zip".format(BUILD_NAME, timestamp)
    zip_path = os.path.join(SCRIPT_DIR, zip_filename)

    print("Building {}...".format(zip_filename))

    # Start from base zip if available, otherwise create new
    if include_python:
        print("  Copying Python base archive...")
        shutil.copy2(base_zip_path, zip_path)
        mode = 'a'  # Append to existing zip
    else:
        mode = 'w'  # Create new zip

    with zipfile.ZipFile(zip_path, mode, zipfile.ZIP_DEFLATED) as zf:
        # Add app/ directory
        print("  Adding application files...")
        for root, dirs, files in os.walk(app_dir):
            # Skip __pycache__
            dirs[:] = [d for d in dirs if d != '__pycache__']

            for f in files:
                if f.endswith('.pyc') or f.endswith('~'):
                    continue
                src = os.path.join(root, f)
                rel = os.path.relpath(src, PROJECT_ROOT)
                arc = os.path.join(BUILD_NAME, rel)
                zf.write(src, arc)

        # Add everything from package/ directory
        package_dir = os.path.join(SCRIPT_DIR, PACKAGE_DIR)
        if os.path.isdir(package_dir):
            print("  Adding package files...")
            for root, dirs, files in os.walk(package_dir):
                for f in files:
                    if f.endswith('~'):
                        continue
                    src = os.path.join(root, f)
                    rel = os.path.relpath(src, package_dir)
                    arc = os.path.join(BUILD_NAME, rel)
                    zf.write(src, arc)

    print()
    print("Build complete: {}".format(zip_path))
    return 0


if __name__ == '__main__':
    sys.exit(build())
