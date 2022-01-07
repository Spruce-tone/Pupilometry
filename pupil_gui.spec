# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['pupil_gui.py'],
             pathex=['E:\\Spruce Dropbox\\Jo Yongjae\\Notebook\\programming\\python\\pupil',
             'E:\\Spruce Dropbox\\Jo Yongjae\\Notebook\\programming\\python\\pupil\\lib',
             'E:\\Spruce Dropbox\\Jo Yongjae\\Notebook\\programming\\python\\pupil\\lib\\Automation'],
             binaries=[('lib\\tisgrabber_x64.dll', '.'),
                        ('lib\\TIS.Imaging.ICImagingControl35.dll', '.'),
                        ('lib\\TIS_UDSHL11_x64.dll', '.')],
             datas=[],
             hiddenimports=[],
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
          name='pupil_gui',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

