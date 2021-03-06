import os
import json
import time
import zipfile

# 版本号
ver = "1.1.3"
version_str = "V" + ver

# 生成version.json
version_data = {}
version_data["version"] = ver
version_data["url"] = "https://github.com/oscarcx123/afk-arena-tools/releases/latest"
version_data["time"] = time.strftime("%Y-%m-%d", time.localtime())
with open(os.path.join(os.getcwd(), "version.json"), "w") as f:
    json.dump(version_data, f)

# 核心文件清单，这些文件进入所有平台的包
core_file_list = [
    'core.py',
    'img',
    'LICENSE',
    'main.py',
    'main_gui.py',
    'README.md',
    'version.json'
]

# Windows相关文件
windows_file_list = [
    'adb.exe',
    'AdbWinApi.dll',
    'AdbWinUsbApi.dll',
    '【Windows】启动脚本.bat'
]

# Linux相关文件
linux_file_list = [
    '【Linux】启动脚本.sh'
]


# 获取当前工作目录下所有文件
file_list = os.listdir()

# 获取所有图片
img_dir = os.path.join(os.getcwd(), "img")
img_list = os.listdir(img_dir)

# 检测dist目录是否存在
if not os.path.isdir("dist"):
    os.makedirs("dist")

# 生成目标目录
destination_dir = os.path.join(os.getcwd(), "dist")

# Windows打包
file_name = "afk-arena-tools_" + version_str + "_windows.zip"
zip_dir = os.path.join(destination_dir, file_name)

with zipfile.ZipFile(zip_dir, "w", zipfile.ZIP_DEFLATED) as zfile:
    for f in core_file_list:
        zfile.write(f)
    for f in img_list:
        zfile.write(os.path.join("img", f))
    for f in windows_file_list:   
        zfile.write(f)

# Linux打包
file_name = "afk-arena-tools_" + version_str + "_linux.zip"
zip_dir = os.path.join(destination_dir, file_name)

with zipfile.ZipFile(zip_dir, "w", zipfile.ZIP_DEFLATED) as zfile:
    for f in core_file_list:   
        zfile.write(f)
    for f in img_list:
        zfile.write(os.path.join("img", f))
    for f in linux_file_list:   
        zfile.write(f)