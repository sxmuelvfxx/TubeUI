import os
import PyInstaller.__main__
import sv_ttk

# Build arguments
args = [
    'tube_ui.py',
    '--onefile',
    '--windowed',
    '--name=TubeUI',
    '--distpath=build_output',
    '--clean',
    '--noconfirm',
    '--hidden-import=sv_ttk',
    '--collect-data=sv_ttk',
    '--collect-submodules=sv_ttk',
    '--hidden-import=yt_dlp.utils.deprecation_warning',
    '--hidden-import=yt_dlp.utils.remove_end',
    '--hidden-import=yt_dlp.utils.Popen',
    '--hidden-import=yt_dlp.utils.system_identifier',
    '--hidden-import=yt_dlp.utils.version_tuple',
    '--hidden-import=yt_dlp.utils.shell_quote',
    '--hidden-import=yt_dlp.utils.format_field',
    '--hidden-import=yt_dlp.utils.NO_DEFAULT',
    '--hidden-import=websockets.uri',
    '--hidden-import=websockets.sync',
    '--hidden-import=websockets.version',
    '--hidden-import=mutagen.oggvorbis',
    '--hidden-import=mutagen.oggopus',
    '--hidden-import=mutagen.mp4',
    '--hidden-import=mutagen.flac',
    '--collect-all=yt_dlp',
    '--collect-all=mutagen'
]

# Add icon only if it exists
if os.path.exists('icon.ico'):
    args.append('--icon=icon.ico')

PyInstaller.__main__.run(args)

print("Build completed! Check the 'build_output' folder for TubeUI.exe")
