import sys, os
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
# "packages": ["os"] is used as example only
include_files = ['./lib', 
                (os.path.join(os.environ["CONDA_PREFIX"], 'DLLs', 'tcl86t.dll'), os.path.join('lib', 'tcl86t.dll')),
                (os.path.join(os.environ["CONDA_PREFIX"], 'DLLs', 'tk86t.dll'), os.path.join('lib', 'tk86t.dll'))]
build_exe_options = {'packages': ['numpy', 'pip', 'keras'], 'excludes': [], 'include_files' : include_files}


# base="Win32GUI" should be used only for Windows GUI app
base = None
if sys.platform == "win32":
    base = "Win32GUI"

exe = [Executable('FlyingSesame.py')]

setup(
    name = "FlyingSesame",
    version = "0.0",
    description = "Pupilometry",
    options = {"build_exe": build_exe_options},
    # executables = [Executable("guifoo.py", base=base)]
    executables = exe
)

