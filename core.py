import os
import cv2
import time
import random
import platform
import subprocess
import numpy as np
from threading import Thread

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
        # debug开关（开启后，成功匹配会弹出图片，上面用圈标明了匹配到的坐标点范围）
        self.debug = False
        # 计数
        self.cnt = 0
        # 一般无需调整比例（默认为1），但是手机魔改之后如果点不到，可以尝试修改这个
        # 例如我的旧手机分辨率从1080p降低到了720p，需要调整比例
        self.ratio = 1
        # 分辨率相关
        self.screen_height = 2560
        self.screen_width = 1440
        self.scale_percentage = 100
        # log临时堆栈，输出后会pop掉
        self.text = []
        
        # 加载图像资源
        self.load_res()
        # log转发
        self.logger = UpdateLog()
        # 停止操作回调
        self.stop_callback = False
        # 系统平台
        self.system = platform.system()
        # wifi_adb默认地址
        self.wifi_adb_addr = "192.168.1.239:5555"

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
            # 如果不是原尺寸（1440P），进行对应缩放操作
            if self.scale_percentage != 100:
                self.res[item]["width"] = int(self.res[item]["img"].shape[1] * self.scale_percentage / 100) 
                self.res[item]["height"] = int(self.res[item]["img"].shape[0] * self.scale_percentage / 100)
                self.res[item]["img"] = cv2.resize(self.res[item]["img"], (self.res[item]["width"], self.res[item]["height"]), interpolation=cv2.INTER_AREA)
            else:
                self.res[item]["height"], self.res[item]["width"], self.res[item]["channel"] = self.res[item]["img"].shape[::]


    # 获取截图
    def get_img(self, pop_up_window=False):
        pipe = subprocess.Popen("adb exec-out screencap -p", stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        image_bytes = pipe.stdout.read()

        if image_bytes == b'':
            self.write_log(f"截图失败！请检查adb是否已经跟手机连接！")
            self.error_stop()
        else:
            self.target_img = cv2.imdecode(np.fromstring(image_bytes, dtype='uint8'), cv2.IMREAD_COLOR)
            if pop_up_window:
                self.show_img()

    def show_img(self):
        cv2.namedWindow("screenshot", cv2.WINDOW_NORMAL)
        cv2.resizeWindow('screenshot', 360, 640)
        cv2.imshow("screenshot", self.target_img)
        cv2.waitKey(0)
        cv2.destroyWindow("screenshot")


    # 匹配并获取中心点
    def match(self, img_name):
        # 从加载好的图像资源中获取数据
        find_img = self.res[img_name]["img"]
        find_height = self.res[img_name]["height"]
        find_width = self.res[img_name]["width"]

        # 匹配
        try:
            result = cv2.matchTemplate(self.target_img, find_img, cv2.TM_CCOEFF_NORMED)
            min_val,self.max_val,min_loc,max_loc = cv2.minMaxLoc(result)
        except:
            self.write_log(f"OpenCV对比失败！请使用杂项中的截图功能来测试能否正常截图！")
            self.error_stop()
        print(f"{img_name}最大匹配度：{self.max_val}")
        if self.max_val < 0.93:
            return False
        
        # 计算位置
        self.pointUpLeft = max_loc
        self.pointLowRight = (int(max_loc[0] + find_width), int(max_loc[1] + find_height))
        self.pointCentre = (int(max_loc[0] + (find_width / 2)), int(max_loc[1] + (find_height / 2)))
        if self.debug:
            self.draw_circle()
        return True

    # 点击（传入坐标）
    # 也可以接受比例形式坐标，例如(0.5, 0.5, percentage=True)就是点屏幕中心
    def tap(self, x_coord=None, y_coord=None, percentage=False):
        if x_coord is None and y_coord is None:
            x_coord, y_coord = self.get_coord()
        if percentage:
            x_coord = int(x_coord * self.screen_width * (self.scale_percentage / 100) * self.ratio)
            y_coord = int(y_coord * self.screen_height * (self.scale_percentage / 100) * self.ratio)
            x_coord = self.randomize_coord(x_coord, 5)
            y_coord = self.randomize_coord(y_coord, 5)
        self.write_log(f"点击坐标：{(x_coord, y_coord)}")
        cmd = f"adb shell input tap {x_coord} {y_coord}"
        self.exec_cmd(cmd)

    # 执行指令
    def exec_cmd(self, cmd, new_thread=False):
        if self.system == "Windows":
            cmd = cmd.replace("adb", "adb.exe")
        if new_thread:
            t = Thread(target=self.thread_exec_cmd, args=[cmd])
            t.start()
        else:
            os.system(cmd)

    # 子线程执行指令（防止阻塞）
    def thread_exec_cmd(self, cmd):
        os.system(cmd)
        self.write_log(f"{cmd}执行完毕")

    # 控制台显示执行次数
    def show_cnt(self):
        self.write_log(f"已重试{self.cnt}次！")

    # adb连接（WIFI）
    def adb_connect(self):
        self.exec_cmd(f"adb connect {self.wifi_adb_addr}", new_thread=True)

    # adb连接（USB）
    def adb_connect_usb(self):
        self.exec_cmd("adb devices", new_thread=True)

    # 画点（测试用）
    def draw_circle(self):
        cv2.circle(self.target_img, self.pointUpLeft, 10, (255, 255, 255), 5)
        cv2.circle(self.target_img, self.pointCentre, 10, (255, 255, 255), 5)
        cv2.circle(self.target_img, self.pointLowRight, 10, (255, 255, 255), 5)
        self.show_img()

    # 获取匹配到的坐标
    def get_coord(self):
        x_coord = int(self.pointCentre[0] * self.ratio)
        x_coord = self.randomize_coord(x_coord, 20)
        y_coord = int(self.pointCentre[1] * self.ratio)
        y_coord = self.randomize_coord(y_coord, 15)
        return x_coord, y_coord

    # 坐标进行随机偏移处理
    def randomize_coord(self, coord, diff):
        return random.randint(coord - diff, coord + diff)

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
            "click_retry": "self.exec_status = self.utils.match('retry_button.png')",
            "click_next_stage": "self.exec_status = self.utils.match('next_stage_button.png')",
            "click_continue": "self.exec_status = self.utils.match('continue_button.png')",
            "click_battle": "self.exec_status = self.utils.match('battle_button.png')",
            "click_challenge": "self.exec_status = self.utils.match('challenge_button.png')",
            "check_boss_stage": "self.exec_status = self.utils.match('challenge_boss_button.png')",
            "check_bundle_pop_up": "self.exec_status = self.utils.match('bundle_pop_up.png')",
            "click_challenge_boss_fp": "self.exec_status = self.utils.match('challenge_boss_fp_button.png')",
            
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
            # 防止截图太快重复点击
            time.sleep(1)

    # 故事模式（只重试，过关之后不挑战下一关）
    def story_mode_retry_only(self):
        cmd_list = [
            "click_retry",
            "click_battle"
        ]
        self.exec_func(cmd_list)

    # 故事模式（推图）
    def story_mode(self):
        cmd_list = [
            "click_retry",
            "click_next_stage",
            "click_battle",
            "check_boss_stage",
            "click_challenge_boss_fp",
            "check_bundle_pop_up"
        ]
        self.exec_func(cmd_list)

    # 王座之塔模式（只重试，过关之后不挑战下一关）
    def tower_mode_retry_only(self):
        cmd_list = [
            "click_retry",
            "click_challenge",
            "click_battle"
        ]
        self.exec_func(cmd_list)

    # 王座之塔模式（推塔）
    def tower_mode(self):
        cmd_list = [
            "click_retry",
            "click_continue",
            "click_battle",
            "click_challenge"
        ]
        self.exec_func(cmd_list)
        
    
    # 点击“再次挑战”
    def click_retry(self):
        self.utils.cnt += 1
        self.utils.show_cnt()
        self.utils.tap()
        

    # 点击“下一关”
    def click_next_stage(self):
        # 挑战成功，重置”重试计数“
        self.utils.cnt = 0
        self.utils.write_log("【故事模式】恭喜过关！即将自动开始挑战下一关！")
        self.utils.tap()


    # 点击“点击屏幕继续”（用于王座之塔页面）
    def click_continue(self):
        # 挑战成功，重置“重试计数”
        self.utils.cnt = 0
        self.utils.write_log("【王座之塔】恭喜过关！即将自动开始挑战下一关！")
        self.utils.tap()


    # 点击“战斗”
    def click_battle(self):
        self.utils.tap()


    # 点击“挑战”（用于王座之塔页面）
    def click_challenge(self):
        self.utils.tap()

    # 检测是否为推图boss关卡
    # 推图到boss关卡时，点击“下一关”无效，会退回到关卡详情页面，需要点击“挑战首领”一次才能进入搭配阵容界面
    def check_boss_stage(self):
        self.utils.tap()

    # 点击主页面（战役tab）的“挑战首领”
    def click_challenge_boss_fp(self):
        self.utils.tap()

    # 检测限时礼包弹窗
    # 如果过关之后弹出限时礼包购买窗口，直接点击屏幕下方关闭
    def check_bundle_pop_up(self):
        self.utils.tap(0.5, 0.9, percentage=True)
        self.utils.write_log("检测到有限时礼包弹窗并自动关闭成功！")
    