import sys
import time
from functools import partial
from threading import Thread
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import pyqtSignal

from core import Utils, Command

import main_gui
import about_gui
import help_gui


'''
【主窗口类】
主窗口类继承自QMainWindow类。
图形程序绝大部分交互都在这里。
'''
class MainWin(QMainWindow):
    def __init__(self, parent=None):
        self.app = QApplication(sys.argv)
        QMainWindow.__init__(self, parent)
        self.ui = main_gui.Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_core()
        self.init_other()
        self.init_subwindow()
        self.init_interface()
        self.init_signal()
        self.write_log("初始化完成！")
        self.write_log("afk-arena-tools是开源软件，如果有任何问题建议想法，欢迎提issue或PR~")
        self.show()
        sys.exit(self.app.exec_())


    # 子窗口初始化（在这里创建实例，从而规避子窗口多开问题）
    def init_subwindow(self):
        self.about_window = About()
        self.help_window = Help()


    # 配置文件模块初始化
    def init_conf(self):
        pass
    
    # 图形界面数值的初始化
    def init_interface(self):
        # 当前正在执行的功能
        self.curr_func = None
        # log框只读
        self.ui.textBrowser.setReadOnly(True)
        # 默认wifi_adb地址
        self.ui.lineEdit.setText(self.afk.utils.wifi_adb_addr)
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


    # 信号和槽（绑定事件）初始化
    def init_signal(self):
        # 绑定“生成器”页面的“生成”按钮到generate函数
        self.ui.action.triggered.connect(self.help_window.show_window)
        self.ui.action_2.triggered.connect(self.about_window.show_window)
        self.ui.pushButton.clicked.connect(partial(self.do_func, self.afk.story_mode_retry_only))
        self.ui.pushButton_2.clicked.connect(partial(self.do_func, self.afk.story_mode))
        self.ui.pushButton_5.clicked.connect(partial(self.do_func, self.afk.tower_mode_retry_only))
        self.ui.pushButton_6.clicked.connect(partial(self.do_func, self.afk.tower_mode))
        self.ui.pushButton_20.clicked.connect(self.stop_thread)
        self.ui.pushButton_21.clicked.connect(self.afk.utils.adb_connect)
        self.ui.pushButton_22.clicked.connect(partial(self.afk.utils.get_img, pop_up_window=True))
        self.ui.pushButton_23.clicked.connect(self.afk.utils.adb_connect_usb)
        self.ui.pushButton_25.clicked.connect(partial(self.afk.utils.get_img, save_img=True))
        self.ui.pushButton_29.clicked.connect(self.get_new_wifi_adb_addr)
        self.ui.pushButton_9.clicked.connect(partial(self.do_func, self.afk.daily_mode))
        self.ui.checkBox.clicked.connect(self.check_ratio)
        self.ui.radioButton.clicked.connect(partial(self.change_resolution, 100))
        self.ui.radioButton_2.clicked.connect(partial(self.change_resolution, 75))
        self.ui.radioButton_3.clicked.connect(partial(self.change_resolution, 50))
        self.afk.utils.logger.update_signal.connect(self.write_log)
        self.afk.utils.logger.error_stop_signal.connect(self.stop_thread)
        

    # 程序核心（core）代码初始化
    def init_core(self):
        self.afk = Command()
        
    # 初始化其余内容
    def init_other(self):
        self.afk.utils.ui = self.ui


    # 执行功能
    def do_func(self, func):
        if not self.curr_func:
            self.curr_func = Thread(target=func)
            self.curr_func.start()

    # 杀掉线程
    def stop_thread(self):
        if self.curr_func:
            self.afk.stop = True
            self.curr_func = None
            self.write_log("成功停止当前执行的功能！")
            self.afk.utils.stop_callback = True
            if self.afk.is_daily_mode:
                self.afk.kill_daily_mode = True
        else:
            self.write_log("当前没有正在执行的功能！")

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

    # 更改截图与实际坐的比例
    # 例如：手机截图是1080P但是点击坐标系是720P，就勾选这个
    def check_ratio(self):
        if self.ui.checkBox.isChecked():
            self.afk.utils.ratio = 720 / 1080
            self.write_log("成功将比例调整为“720/1080”")
        else:
            self.afk.utils.ratio = 1
            self.write_log("成功将比例调整为1")

    # 更改分辨率
    def change_resolution(self, percentage):
        self.afk.utils.scale_percentage = percentage
        self.afk.utils.load_res()
        self.write_log(f"成功将分辨率更改为{int(1440 * percentage / 100)}P")

    # 写入新的wifi_adb地址
    def get_new_wifi_adb_addr(self):
        self.afk.utils.wifi_adb_addr = self.ui.lineEdit.text()
        self.write_log("保存wifi_adb地址成功！")

'''
【子窗口基类】
需要继承并复写ui_init函数才能使用。
使用时需要在MainWin类的init_subwindow函数中注册。
每次显示窗口就只调用show方法而不是重新实例化，这样可以防止子窗口多开。
'''
class SubWin(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.ui_init()
        self.ui.setupUi(self)

    # 此函数留白，用于在继承子窗口基类时复写
    # 复写格式为 self.ui = gui_file.ui_type()
    # 例子：self.ui = about_gui.Ui_Dialog()
    def ui_init(self):
        pass

    # 显示窗口
    def show_window(self):
        self.show()
        self.raise_()

# “关于”窗口
class About(SubWin):
    def ui_init(self):
        self.ui = about_gui.Ui_Dialog()


# “使用帮助”窗口
class Help(SubWin):
    def ui_init(self):
        self.ui = help_gui.Ui_Dialog()

if __name__ == '__main__':
    window = MainWin()