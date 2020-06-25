import os
import sys
import time
import json
from functools import partial
from threading import Thread
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import pyqtSignal

from core import Utils, Command

import main_gui

'''
【主窗口类】
主窗口类继承自QMainWindow类。
图形程序绝大部分交互都在这里。
'''
class MainWin(QMainWindow):
    def __init__(self, parent=None):
        # pyqt必要的代码
        self.app = QApplication(sys.argv)
        QMainWindow.__init__(self, parent)
        self.ui = main_gui.Ui_MainWindow()
        self.ui.setupUi(self)
        # 程序功能模块（core.py）初始化
        self.afk = Command()
        # 让功能模块（core.py）也能访问UI
        self.afk.utils.ui = self.ui
        # 图形界面数值的初始化
        self.init_interface()
        # 信号初始化
        self.init_signal()
        self.write_log("初始化完成！")
        self.write_log("afk-arena-tools是开源软件，如果有任何问题建议想法，欢迎提issue或PR~")
        # pyqt必要的代码
        self.show()
        sys.exit(self.app.exec_())


    # 图形界面数值的初始化
    def init_interface(self):
        # 当前正在执行的功能
        self.curr_func = None
        # log框只读
        self.ui.textBrowser.setReadOnly(True)
        # 加载配置
        self.load_conf()


    # 信号和槽（绑定事件）初始化
    def init_signal(self):
        # 绑定“生成器”页面的“生成”按钮到generate函数
        self.ui.pushButton.clicked.connect(partial(self.do_func, self.afk.story_mode_retry_only))
        self.ui.pushButton_2.clicked.connect(partial(self.do_func, self.afk.story_mode))
        self.ui.pushButton_5.clicked.connect(partial(self.do_func, self.afk.tower_mode_retry_only))
        self.ui.pushButton_6.clicked.connect(partial(self.do_func, self.afk.tower_mode))
        self.ui.pushButton_10.clicked.connect(self.get_thread_status)
        self.ui.pushButton_20.clicked.connect(self.stop_thread)
        self.ui.pushButton_21.clicked.connect(self.wifi_adb_connect)
        self.ui.pushButton_22.clicked.connect(partial(self.afk.utils.get_img, pop_up_window=True))
        self.ui.pushButton_23.clicked.connect(self.afk.utils.adb_devices)
        self.ui.pushButton_24.clicked.connect(self.afk.utils.adb_version)
        self.ui.pushButton_25.clicked.connect(partial(self.afk.utils.get_img, save_img=True))
        self.ui.pushButton_26.clicked.connect(self.gui_swipe)
        self.ui.pushButton_27.clicked.connect(self.gui_tap)
        self.ui.pushButton_28.clicked.connect(self.gui_long_press)
        self.ui.pushButton_9.clicked.connect(partial(self.do_func, self.afk.daily_mode))
        self.ui.radioButton.clicked.connect(partial(self.change_resolution, 100))
        self.ui.radioButton_2.clicked.connect(partial(self.change_resolution, 75))
        self.ui.radioButton_3.clicked.connect(partial(self.change_resolution, 50))
        self.afk.utils.logger.update_signal.connect(self.write_log)
        self.afk.utils.logger.error_stop_signal.connect(self.stop_thread)
        self.afk.utils.logger.finish_exec_signal.connect(self.thread_finish_exec)
        self.ui.doubleSpinBox.valueChanged.connect(self.change_exec_time_delay)
        self.ui.doubleSpinBox_2.valueChanged.connect(self.change_threshold)
        
    # 加载默认配置
    def load_default_conf(self):
        # 默认wifi_adb地址
        self.ui.lineEdit.setText(self.afk.utils.wifi_adb_addr)
        # 默认分辨率是1440P
        self.ui.radioButton.setChecked(True)
        # 日常任务默认勾选
        self.ui.checkBox_2.setChecked(True)
        self.ui.checkBox_3.setChecked(True)
        self.ui.checkBox_4.setChecked(True)
        self.ui.checkBox_5.setChecked(True)
        self.ui.checkBox_6.setChecked(True)
        self.ui.checkBox_7.setChecked(True)
        self.ui.checkBox_8.setChecked(True)
        self.ui.checkBox_9.setChecked(True)
        self.ui.checkBox_10.setChecked(True)
        self.ui.checkBox_11.setCheckable(False)
        self.ui.checkBox_12.setCheckable(False)
        self.ui.checkBox_13.setCheckable(False)
        # 脚本执行设置
        self.ui.doubleSpinBox.setValue(1.00)
        self.ui.doubleSpinBox_2.setValue(0.90)

    # 保存配置
    def save_conf(self):
        conf_data = {}
        conf_data["wifi_adb_addr"] = self.afk.utils.wifi_adb_addr
        conf_data["radioButton"] = self.ui.radioButton.isChecked()
        conf_data["radioButton_2"] = self.ui.radioButton_2.isChecked()
        conf_data["radioButton_3"] = self.ui.radioButton_3.isChecked()
        conf_data["checkBox_2"] = self.ui.checkBox_2.isChecked()
        conf_data["checkBox_3"] = self.ui.checkBox_3.isChecked()
        conf_data["checkBox_4"] = self.ui.checkBox_4.isChecked()
        conf_data["checkBox_5"] = self.ui.checkBox_5.isChecked()
        conf_data["checkBox_6"] = self.ui.checkBox_6.isChecked()
        conf_data["checkBox_7"] = self.ui.checkBox_7.isChecked()
        conf_data["checkBox_8"] = self.ui.checkBox_8.isChecked()
        conf_data["checkBox_9"] = self.ui.checkBox_9.isChecked()
        conf_data["checkBox_10"] = self.ui.checkBox_10.isChecked()
        conf_data["checkBox_11"] = self.ui.checkBox_11.isCheckable()
        conf_data["checkBox_12"] = self.ui.checkBox_12.isCheckable()
        conf_data["checkBox_13"] = self.ui.checkBox_13.isCheckable()
        conf_data["doubleSpinBox"] = self.afk.exec_func_delay
        conf_data["doubleSpinBox_2"] = self.afk.utils.threshold
        with open(os.path.join(os.getcwd(), "conf.json"), "w") as f:
            json.dump(conf_data, f)

    # 加载配置
    def load_conf(self):
        full_path = os.path.join(os.getcwd(), "conf.json")
        if os.path.isfile(full_path):
            with open(full_path) as f:
                conf_data = json.load(f)
            try:
                self.afk.utils.wifi_adb_addr = conf_data["wifi_adb_addr"]
                self.ui.lineEdit.setText(self.afk.utils.wifi_adb_addr)
                self.ui.radioButton.setChecked(conf_data["radioButton"])
                if conf_data["radioButton"]:
                    self.change_resolution(100, show_log=False)
                self.ui.radioButton_2.setChecked(conf_data["radioButton_2"])
                if conf_data["radioButton_2"]:
                    self.change_resolution(75, show_log=False)
                self.ui.radioButton_3.setChecked(conf_data["radioButton_3"])
                if conf_data["radioButton_3"]:
                    self.change_resolution(50, show_log=False)
                # 日常任务默认勾选
                self.ui.checkBox_2.setChecked(conf_data["checkBox_2"])
                self.ui.checkBox_3.setChecked(conf_data["checkBox_3"])
                self.ui.checkBox_4.setChecked(conf_data["checkBox_4"])
                self.ui.checkBox_5.setChecked(conf_data["checkBox_5"])
                self.ui.checkBox_6.setChecked(conf_data["checkBox_6"])
                self.ui.checkBox_7.setChecked(conf_data["checkBox_7"])
                self.ui.checkBox_8.setChecked(conf_data["checkBox_8"])
                self.ui.checkBox_9.setChecked(conf_data["checkBox_9"])
                self.ui.checkBox_10.setChecked(conf_data["checkBox_10"])
                self.ui.checkBox_11.setCheckable(conf_data["checkBox_11"])
                self.ui.checkBox_12.setCheckable(conf_data["checkBox_12"])
                self.ui.checkBox_13.setCheckable(conf_data["checkBox_13"])
                self.afk.exec_func_delay = float(conf_data["doubleSpinBox"])
                self.ui.doubleSpinBox.setValue(self.afk.exec_func_delay)
                self.afk.utils.threshold = float(conf_data["doubleSpinBox_2"])
                self.ui.doubleSpinBox_2.setValue(self.afk.utils.threshold)
            except:
                self.write_log("配置读取错误，加载默认配置并生成配置文件conf.json")
                self.load_default_conf()
                self.save_conf()
        else:
            self.write_log("检测到是首次启动，加载默认配置并生成配置文件conf.json")
            self.load_default_conf()
            self.save_conf()
  

    # 执行功能
    def do_func(self, func):
        if not self.curr_func:
            self.afk.stop = False
            self.save_conf()
            self.curr_func = Thread(target=func)
            self.curr_func.start()

    # 杀掉线程
    def stop_thread(self):
        self.afk.utils.stop_callback = True
        if self.curr_func:
            self.afk.stop = True
            self.curr_func = None
            self.write_log("成功停止当前执行的功能！如果还在继续，说明还有残余指令在运行，可以等待执行完毕或者直接重启软件")  
        else:
            self.write_log("当前没有正在执行的功能！")

    # 线程正常执行完毕
    def thread_finish_exec(self):
        self.curr_func = None
    
    # 在GUI窗口的log框中输出日志
    def write_log(self, text=None):
        #print(self.afk.utils.text)
        curr_time = time.strftime("%H:%M:%S", time.localtime())
        if not text:
            while len(self.afk.utils.text) > 0:
                text = self.afk.utils.text.pop(0)
                self.ui.textBrowser.insertPlainText(f"[{curr_time}]{text}\n")
                self.ui.textBrowser.ensureCursorVisible()
        else:
            self.ui.textBrowser.insertPlainText(f"[{curr_time}]{text}\n")
            self.ui.textBrowser.ensureCursorVisible()


    # 更改分辨率
    def change_resolution(self, percentage, show_log=True):
        self.afk.utils.scale_percentage = percentage
        self.afk.utils.load_res()
        if show_log:
            self.write_log(f"成功将分辨率更改为{int(1440 * percentage / 100)}P")

    # 写入新的wifi_adb地址并连接
    def wifi_adb_connect(self):
        self.afk.utils.wifi_adb_addr = self.ui.lineEdit.text()
        self.write_log("保存wifi_adb地址成功！")
        self.afk.utils.adb_connect()

    # 通过GUI点击
    def gui_tap(self):
        self.afk.utils.tap(x_coord=int(self.ui.lineEdit_2.text()), y_coord=int(self.ui.lineEdit_3.text()), randomize=False)

    # 通过GUI长按
    def gui_long_press(self):
        self.afk.utils.swipe(fromX=int(self.ui.lineEdit_4.text()), fromY=int(self.ui.lineEdit_5.text()))

    # 通过GUI滑动
    def gui_swipe(self):
        self.afk.utils.swipe(fromX=int(self.ui.lineEdit_4.text()), fromY=int(self.ui.lineEdit_5.text()), toX=int(self.ui.lineEdit_6.text()), toY=int(self.ui.lineEdit_7.text()))

    # 获得当前执行状态
    def get_thread_status(self):
        if self.curr_func:
            self.write_log(f"【运行状态】正在执行，线程名称：{self.curr_func.name}")
        else:
            self.write_log(f"【运行状态】没在执行")

    # exec_time延迟设置
    def change_exec_time_delay(self):
        self.afk.exec_func_delay = self.ui.doubleSpinBox.value()

    # 图片匹配阈值设置
    def change_threshold(self):
        self.afk.utils.threshold = self.ui.doubleSpinBox_2.value()

if __name__ == '__main__':
    window = MainWin()