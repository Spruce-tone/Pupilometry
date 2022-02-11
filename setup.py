import sys, os
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
# "packages": ["os"] is used as example only
include_files = ['./lib', 
                (os.path.join(os.environ["CONDA_PREFIX"], 'DLLs', 'tcl86t.dll'), os.path.join('lib', 'tcl86t.dll')),
                (os.path.join(os.environ["CONDA_PREFIX"], 'DLLs', 'tk86t.dll'), os.path.join('lib', 'tk86t.dll')),
                (os.path.join(os.environ["CONDA_PREFIX"], 'Library', 'bin', 'mkl_intel_thread.1.dll'), os.path.join('lib', 'mkl_intel_thread.1.dll'))]
build_exe_options = {'packages': ['numpy'], 'excludes': [], 'include_files' : include_files}


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

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import os

block_cipher = None


a = Analysis(['FlyingSesame.py'],
             pathex=['.',
             '.\\lib',
             '.\\lib\\Automation'],
             binaries=[('lib\\tisgrabber_x64.dll', '.'),
                        ('lib\\TIS.Imaging.ICImagingControl35.dll', '.'),
                        ('lib\\TIS_UDSHL11_x64.dll', '.')],
             datas=[('C:\\Users\\spruce\\anaconda3\\envs\\livepupil2\\Lib\\site-packages\\tensorflow\\python\\tensorflow.python._pywrap_tensorflow_internal.pyd', '.')],
             hiddenimports=['tensorflow',
                            'tensorflow.python._pywrap_tensorflow_internal',
                            'sklearn.neighbors.typedefs',
                            'sklearn.neighbors.quad_tree',
                            'sklearn.tree',
                            'sklearn.tree._utils',
                            'tensorflow._api.v2.compat.v1.compat.v1.keras.datasets.fashion_mnist'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='FlyingSesame',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

