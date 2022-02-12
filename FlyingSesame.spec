# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['FlyingSesame.py'],
             pathex=['.',
             '.\\lib',
             '.\\lib\\Automation'],
             binaries=[('lib\\tisgrabber_x64.dll', '.'),
                        ('lib\\TIS.Imaging.ICImagingControl35.dll', '.'),
                        ('lib\\TIS_UDSHL11_x64.dll', '.')],
             hiddenimports=['tensorpack.dataflow.imgaug',
                            'sklearn.neighbors.typedefs',
                            'sklearn.neighbors.quad_tree',
                            'sklearn.tree',
                            'sklearn.tree._utils',
                            'sklearn.utils._typedefs',
                            'sklearn.neighbors._partition_nodes'],
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

# coll = COLLECT(exe,
#               a.binaries,
#               a.zipfiles,
#               a.datas, 
#               strip=False,
#               upx=True,
#               upx_exclude=[],
#               name='FlyingSesame')

