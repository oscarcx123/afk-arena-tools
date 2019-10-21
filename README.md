# afk-arena-tools

## 简介

使用 Python + OpenCV + PyQt5 + adb 制作的AFK Arena / 剑与远征 辅助。

原理是OpenCV识别图片，adb负责截图和点击操作，仅此而已。

<p align="center">
  <img src="./_docs/img/main_gui.png" alt="main_gui" width="500"/>
  <br><br>
  <b>游戏界面</b>
</p>

既然已经来了，不点个star鼓励下作者吗？

## 运行说明

电脑需要安装：

* Python3.6或以上版本
* OpenCV（从pip安装即可）
* adb（Android Debug Bridge）
* PyQt5（从pip安装即可）

输入下面指令即可安装，Linux用户记得加sudo

```
pip install opencv-python PyQt5
```

因为使用到ADB，只能作用于安卓手机。

目前以下操作系统测试通过：
* Manjaro Linux
* Windows 10 (ver 1903)

双击启动脚本或者运行main.py

## 操作说明

连接adb后点击对应功能即可。

## 开发计划

*  一键完成每日必做的任务
*  一键打迷宫（感觉本菜鸡水平不足，不一定能做到）

## 更新说明

### 2019.10.20 V1.0.1

* [x] 适配Windows系统
* [x] adb连接使用子线程防止阻塞

### 2019.10.18 V1.0.0

* [x] 最初版本发布
