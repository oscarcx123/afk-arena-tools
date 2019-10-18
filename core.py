import cv2
import os
import numpy as np
import time
import random

import global_var

from PyQt5.QtCore import QObject, pyqtSignal

# QWidget无法在主线程之外被调用，因此构造一个QObject，使用自定义的信号来触发主线程的槽函数
# 具体可以看：https://stackoverflow.com/questions/2104779/qobject-qplaintextedit-multithreading-issues
# stackoverflow中的回答很好的解释了原因，但是没有给出示例代码。
# 我经过搜索以及研究，做出了解决方案，有同样需求的开发者可以参考本程序。
class UpdateLog(QObject):
    # 写入log框信号
    update_signal = pyqtSignal()
    # 程序出错停止当前执行任务信号
    error_stop_signal = pyqtSignal()
 
    def __init__(self):
        QObject.__init__(self)
 
    def update(self):
        self.update_signal.emit()

    def error_stop(self):
        self.error_stop_signal.emit()

class Utils():
    def __init__(self):
        # debug开关
        self.debug = False
        # 计数
        self.cnt = 0
        # 一般无需调整比例（默认为1），但是手机魔改之后如果点不到，可以尝试修改这个
        # 例如我的手机分辨率从1080p降低到了720p，需要调整比例
        self.ratio = 1
        # log临时堆栈，输出后会pop掉
        self.text = []
        
        # 加载图像资源
        self.load_res()
        # log转发
        self.logger = UpdateLog()
        # 停止操作回调
        self.stop_callback = False

    # 加载图像资源
    def load_res(self):
        # 匹配对象的字典
        self.res = {}
        file_dir = os.path.join(os.getcwd(), "img")
        temp_list = os.listdir(file_dir)
        for item in temp_list:
            self.res[item] = {}
            res_path = os.path.join(file_dir, item)
            self.res[item]["img"] = cv2.imread(res_path)
            self.res[item]["height"], self.res[item]["width"], self.res[item]["channel"] = self.res[item]["img"].shape[::]


    # 获取截图
    def get_img(self):
        cmd = "adb shell screencap -p > screenshot.png"
        self.exec_cmd(cmd)
        if self.is_file_empty("screenshot.png"):
            self.write_log(f"截图失败！原因：生成的screenshot.png为空文件，请检查adb是否已经跟手机连接！")
            self.error_stop()
        else:
            self.target_img = cv2.imread("screenshot.png")

    # 匹配并获取中心点
    def match(self, img_name):
        # 从加载好的图像资源中获取数据
        find_img = self.res[img_name]["img"]
        find_height = self.res[img_name]["height"]
        find_width = self.res[img_name]["width"]

        # 匹配
        try:
            result = cv2.matchTemplate(self.target_img, find_img, cv2.TM_CCOEFF_NORMED)
            min_val,max_val,min_loc,max_loc = cv2.minMaxLoc(result)
        except:
            self.write_log(f"OpenCV对比失败！请检查screenshot.png是否存在，并且不是空文件！")
            self.error_stop()
        print(f"{img_name}最大匹配度：{max_val}")
        if max_val < 0.93:
            return False
        
        # 计算位置
        self.pointUpLeft = max_loc
        self.pointLowRight = (int(max_loc[0] + find_width), int(max_loc[1] + find_height))
        self.pointCentre = (int(max_loc[0] + (find_width / 2)), int(max_loc[1] + (find_height / 2)))
        if self.debug:
            self.draw_circle()
        return True

    # 点击
    def tap(self, x_coord, y_coord):
        self.write_log(f"点击坐标：{(x_coord, y_coord)}")
        cmd = f"adb shell input tap {x_coord} {y_coord}"
        self.exec_cmd(cmd)

    # 执行指令
    def exec_cmd(self, cmd):
        os.system(cmd)

    # 控制台显示执行次数
    def show_cnt(self):
        self.write_log(f"已重试{self.cnt}次！")

    # adb连接
    def adb_connect(self):
        self.exec_cmd("adb connect 192.168.1.239:5555")

    # 画点（测试用）
    def draw_circle(self):
        cv2.circle(self.target_img, self.pointUpLeft, 2, (255, 255, 255), -1)
        cv2.circle(self.target_img, self.pointCentre, 2, (255, 255, 255), -1)
        cv2.circle(self.target_img, self.pointLowRight, 2, (255, 255, 255), -1)
        cv2.imwrite("shot_with_circle.png", self.target_img)

    # 获取坐标并进行随机偏移处理
    def get_coord(self):
        x_coord = int(self.pointCentre[0] * self.ratio)
        x_coord = random.randint(x_coord - 20, x_coord + 20)
        y_coord = int(self.pointCentre[1] * self.ratio)
        y_coord = random.randint(y_coord - 15, y_coord + 15)
        return x_coord, y_coord

    # 在GUI的文本框内写入log
    def write_log(self, text):
        self.text.append(text)
        self.logger.update()

    # 判断文件是否为空
    def is_file_empty(self, file_name):
        return os.stat(file_name).st_size == 0

    # 致命错误时转发到GUI实现停止当前任务
    def error_stop(self):
        self.logger.error_stop()
        # 等待GUI线程的回调，确保当前任务已经停止
        while True:
            if self.stop_callback:
                self.stop_callback = False
                break



# 预设的一些指令组
class Command():
    def __init__(self):
        self.utils = Utils()
        # 指令与执行操作的对应关系
        self.func = {
            "retry_on_lose": "self.exec_status = self.utils.match('retry_button.png')",
            "proceed_on_win": "self.exec_status = self.utils.match('next_stage_button.png')",
            "tower_on_win": "self.exec_status = self.utils.match('tower_continue_button.png')",
            "challenge_tower": "self.exec_status = self.utils.match('tower_challenge_button.png')"
        }
        # 是否执行指令
        self.exec_status = None
        # 是否杀掉进程
        self.stop = False

    # 自动执行符合触发条件的指令
    def exec_func(self, cmd_list):
        while True:
            self.utils.get_img()
            if self.stop:
                self.stop = False
                break
            for cmd in cmd_list:
                exec(self.func[cmd])
                if self.exec_status:
                    cmd = "self." + cmd + "()"
                    exec(cmd)
                    break
            if self.stop:
                self.stop = False
                break

    # 故事模式（只重试，过关之后不挑战下一关）
    def story_mode_retry_only(self):
        cmd_list = [
            "retry_on_lose"
        ]
        self.exec_func(cmd_list)

    # 故事模式（推图）
    def story_mode(self):
        cmd_list = [
            "retry_on_lose",
            "proceed_on_win"
        ]
        self.exec_func(cmd_list)

    # 王座之塔模式（只重试，过关之后不挑战下一关）
    def tower_mode_retry_only(self):
        cmd_list = [
            "retry_on_lose",
        ]
        self.exec_func(cmd_list)

    # 王座之塔模式（推塔）
    def tower_mode(self):
        cmd_list = [
            "retry_on_lose",
            "tower_on_win",
            "challenge_tower"
        ]
        self.exec_func(cmd_list)
        
    # 点击“再次挑战”并开始挑战
    def click_retry_and_start(self):
        # 点击“再次挑战”
        x_coord, y_coord = self.utils.get_coord()
        self.utils.tap(x_coord, y_coord)
        
        time.sleep(2)
        
        # 开始挑战
        x_coord = random.randint(360-50, 360+50)
        y_coord = random.randint(1240-10, 1240+10)
        self.utils.tap(x_coord, y_coord)

    # 战斗失败时重试
    def retry_on_lose(self):
        self.utils.cnt += 1
        self.utils.show_cnt()
        self.click_retry_and_start()
        

    # 战斗成功时直接挑战下一关
    def proceed_on_win(self):
        # 挑战成功，重置”重试计数“
        self.utils.cnt = 0
        self.utils.write_log("【故事模式】恭喜过关！即将自动开始挑战下一关！")
        self.click_retry_and_start()

    # 王座之塔战斗胜利时点击屏幕继续
    def tower_on_win(self):
        # 挑战成功，重置”重试计数“
        self.utils.cnt = 0
        self.utils.write_log("【王座之塔】恭喜过关！即将自动开始挑战下一关！")
        x_coord, y_coord = self.utils.get_coord()
        self.utils.tap(x_coord, y_coord)

    # 挑战王座之塔
    def challenge_tower(self):
        self.click_retry_and_start()

