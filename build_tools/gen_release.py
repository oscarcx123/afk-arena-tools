import os
import zipfile

version = "1.0.5"

core_file_list = [
    'about_gui.py',
    'core.py',
    'help_gui.py',
    'img',
    'LICENSE',
    'main.py',
    'main_gui.py',
    'README.md'
]

windows_file_list = [
    'adb.exe',
    'AdbWinApi.dll',
    'AdbWinUsbApi.dll',
    '启动脚本（Windows）.bat'
]

linux_file_list = [
    '启动脚本（Linux）.sh'
]

version_str = "V" + version

img_dir = os.path.join(os.getcwd(), "img")

file_list = os.listdir()
img_list = os.listdir(img_dir)

with zipfile.ZipFile("afk-arena-tools_" + version_str + "_windows.zip", "w") as zfile:
    for f in core_file_list:
        zfile.write(f)
    for f in img_list:
        zfile.write(os.path.join("img", f))
    for f in windows_file_list:   
        zfile.write(f)

with zipfile.ZipFile("afk-arena-tools_" + version_str + "_linux.zip", "w") as zfile:
    for f in core_file_list:   
        zfile.write(f)
    for f in img_list:
        zfile.write(os.path.join("img", f))
    for f in linux_file_list:   
        zfile.write(f)