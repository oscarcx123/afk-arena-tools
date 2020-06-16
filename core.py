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
    def get_img(self, pop_up_window=False, save_img=False):
        pipe = subprocess.Popen("adb exec-out screencap -p", stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        image_bytes = pipe.stdout.read()

        if image_bytes == b'':
            self.write_log(f"截图失败！请检查adb是否已经跟手机连接！")
            self.error_stop()
        else:
            self.target_img = cv2.imdecode(np.fromstring(image_bytes, dtype='uint8'), cv2.IMREAD_COLOR)
            if save_img:
                cv2.imwrite('screenshot.png', self.target_img)
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

    # 立即截图，然后匹配，返回boolean
    def current_match(self, img_name):
        self.get_img()
        return self.match(img_name)
    
    # 点击（传入坐标）
    # 也可以接受比例形式坐标，例如(0.5, 0.5, percentage=True)就是点屏幕中心
    # 可以传入randomize=False来禁用坐标的随机偏移
    def tap(self, x_coord=None, y_coord=None, percentage=False, randomize=True):
        if x_coord is None and y_coord is None:
            x_coord, y_coord = self.get_coord(randomize=randomize)
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
    def get_coord(self, randomize=True):
        x_coord = int(self.pointCentre[0] * self.ratio)
        y_coord = int(self.pointCentre[1] * self.ratio)
        if randomize:
            x_coord = self.randomize_coord(x_coord, 20)
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
            "click_battle_retry": "self.exec_status = self.utils.match('after_battle_retry_button.png')",
            "click_next_stage": "self.exec_status = self.utils.match('next_stage_button.png')",
            "click_continue": "self.exec_status = self.utils.match('continue_button.png')",
            "click_battle": "self.exec_status = self.utils.match('battle_button.png')",
            "click_battle_pause": "self.exec_status = self.utils.match('in_battle_pause_button.png')",
            "click_battle_exit": "self.exec_status = self.utils.match('in_battle_exit_button.png')",
            "click_challenge": "self.exec_status = self.utils.match('challenge_button.png')",
            "check_boss_stage": "self.exec_status = self.utils.match('challenge_boss_button.png')",
            "check_bundle_pop_up": "self.exec_status = self.utils.match('bundle_pop_up.png')",
            "click_challenge_boss_fp": "self.exec_status = self.utils.match('challenge_boss_fp_button.png')",
            "check_level_up": "self.exec_status = self.utils.match('level_up.png')",
            "click_idle_chest": "self.exec_status = self.utils.match('idle_chest.png')",
            "click_friend_button": "self.exec_status = self.utils.match('friend_button.png')",
            "click_expand_left_col_button": "self.exec_status = self.utils.match('expand_left_col_button.png')",
            "click_send_heart_button": "self.exec_status = self.utils.match('send_heart_button.png')",
            "click_close_friend_ui_button": "self.exec_status = self.utils.match('ui_return_button.png')",
            "click_instant_idle_button": "self.exec_status = self.utils.match('instant_idle_button.png')",
            "click_instant_idle_free_claim_button": "self.exec_status = self.utils.match('instant_idle_free_claim_button.png')",
            "click_instant_idle_close_button": "self.exec_status = self.utils.match('instant_idle_close_button.png')",
            "click_noble_tavern_button": "self.exec_status = self.utils.match('noble_tavern_button.png')",
            "click_friend_summon_pool": "self.exec_status = self.utils.match('friend_summon_pool.png')",
            "click_guild_button": "self.exec_status = self.utils.match('guild_button.png')",
            "click_guild_boss_button": "self.exec_status = self.utils.match('guild_boss_button.png')",
        }
        # 是否执行指令
        self.exec_status = None
        # 是否杀掉进程
        self.stop = False
        # 以下坐标会在执行“日常任务”模式时自动初始化
        # “领地”点击坐标
        self.ranhorn_coord = None
        # “野外”点击坐标
        self.dark_forest_coord = None
        # “战役”点击坐标
        self.campaign_coord = None

    # 自动执行符合触发条件的指令
    def exec_func(self, cmd_list, exit_cond=None):
        afterExecFunc = False
        if exit_cond is not None:
            if "afterExecFunc" in exit_cond:
                exit_cond = exit_cond.split("@")[1]
                afterExecFunc = True
        while True:
            self.utils.get_img()
            if self.stop:
                self.stop = False
                break
            for cmd in cmd_list:
                exec(self.func[cmd])
                if self.exec_status:
                    # 如果达成退出条件，就会在执行完毕之后退出exec_func函数
                    if afterExecFunc:
                        if exit_cond == cmd:
                            self.stop = True
                    cmd_func = "self." + cmd + "()"
                    exec(cmd_func)
                    break
            if self.stop:
                self.stop = False
                break
            # 防止截图太快重复点击
            time.sleep(1.5)

    # 故事模式（只重试，过关之后不挑战下一关）
    def story_mode_retry_only(self):
        cmd_list = [
            "click_battle_retry",
            "click_battle"
        ]
        self.exec_func(cmd_list)

    # 故事模式（推图）
    def story_mode(self):
        cmd_list = [
            "click_battle_retry",
            "click_next_stage",
            "click_battle",
            "check_boss_stage",
            "click_challenge_boss_fp",
            "check_bundle_pop_up",
            "check_level_up"
        ]
        self.exec_func(cmd_list)

    # 王座之塔模式（只重试，过关之后不挑战下一关）
    def tower_mode_retry_only(self):
        cmd_list = [
            "click_battle_retry",
            "click_challenge",
            "click_battle"
        ]
        self.exec_func(cmd_list)

    # 王座之塔模式（推塔）
    def tower_mode(self):
        cmd_list = [
            "click_battle_retry",
            "click_continue",
            "click_battle",
            "click_challenge"
        ]
        self.exec_func(cmd_list)

    # 日常任务模式
    def daily_mode(self):
        # 初始化“领地”、“野外”、“战役”的坐标
        if self.ranhorn_coord is None or self.dark_forest_coord is None or self.campaign_coord is None:
            self.utils.get_img()
            if not self.utils.match("ranhorn_icon.png"):
                self.utils.match("ranhorn_icon_chosen.png")
            self.ranhorn_coord = self.utils.get_coord()
            if not self.utils.match("dark_forest_icon.png"):
                self.utils.match("dark_forest_icon_chosen.png")
            self.dark_forest_coord = self.utils.get_coord()
            if not self.utils.match("campaign_icon.png"):
                self.utils.match("campaign_icon_chosen.png")
            self.campaign_coord = self.utils.get_coord()
        
        mission_list = []
        if self.utils.ui.checkBox_2.isChecked():
            mission_list.append("daily_challenge_boss")
        if self.utils.ui.checkBox_4.isChecked():
            mission_list.append("daily_send_heart")
        if self.utils.ui.checkBox_5.isChecked():
            mission_list.append("daily_instant_idle")
        if self.utils.ui.checkBox_6.isChecked():
            mission_list.append("daily_summon")
        if self.utils.ui.checkBox_7.isChecked():
            mission_list.append("daily_guild_boss")
        if self.utils.ui.checkBox_8.isChecked():
            mission_list.append("daily_send_heart")
        if self.utils.ui.checkBox_9.isChecked():
            mission_list.append("daily_send_heart")
        if self.utils.ui.checkBox_10.isChecked():
            mission_list.append("daily_send_heart")
        if self.utils.ui.checkBox_11.isChecked():
            mission_list.append("daily_send_heart")
        if self.utils.ui.checkBox_12.isChecked():
            mission_list.append("daily_send_heart")
        # 箱子会在所有任务开始前后分别领取一次
        if self.utils.ui.checkBox_3.isChecked():
            self.daily_idle_chest_1st_exec = True
            mission_list.insert(0, "daily_idle_chest")
            mission_list.append("daily_idle_chest")
        
        # 按照mission list执行每日任务
        for mission in mission_list:
            func = "self." + mission + "()"
            exec(func)
            time.sleep(2)
    
    # 日常任务 - 挑战首领1次（20pts）
    def daily_challenge_boss(self):
        self.click_campaign_icon()
        cmd_list = [
            "click_battle_exit",
            "click_battle_pause",
            "click_battle",
            "click_challenge_boss_fp",
            "check_boss_stage",
            "check_bundle_pop_up",
            "check_level_up"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_battle_exit")
        self.utils.write_log("【日常任务】完成 - 挑战首领1次（20pts）！")
    

    # 日常任务 - 领取战利品2次（10pts）
    def daily_idle_chest(self):
        self.click_campaign_icon()
        cmd_list = [
            "click_idle_chest",
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_idle_chest")
        self.utils.tap(0.5, 0.9, percentage=True)
        if self.daily_idle_chest_1st_exec:
            self.daily_idle_chest_1st_exec = False
            self.utils.write_log("【日常任务】领取战利品1次，第2次会在其它日常任务执行完毕后领取！")
        else:
            self.utils.write_log("【日常任务】完成 - 领取战利品2次（10pts）！")

    # 日常任务 - 赠送好友友情点1次（10pts）
    def daily_send_heart(self):
        self.click_campaign_icon()
        cmd_list = [
            "click_expand_left_col_button",
            "click_friend_button",
            "click_send_heart_button"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_send_heart_button")
        
        cmd_list = [
            "click_close_friend_ui_button"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_close_friend_ui_button")
        self.utils.write_log("【日常任务】完成 - 赠送好友友情点1次（10pts）！")
    

    # 日常任务 - 快速挂机1次（10pts）
    def daily_instant_idle(self):
        self.click_campaign_icon()
        cmd_list = [
            "click_instant_idle_button"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_instant_idle_button")
        if self.utils.current_match('instant_idle_free_claim_button.png'):
            # 点击“免费领取”
            self.utils.tap()
            # 给予设备足够的反应时间后，点击空白处（屏幕下方）关闭“获得奖励”窗口
            time.sleep(1)
            self.utils.tap(0.5, 0.9, percentage=True)
            self.utils.write_log("【日常任务】完成 - 快速挂机1次（10pts）！")
        else:
            self.utils.write_log("【日常任务】执行失败 - 快速挂机1次（10pts）！原因：你已经用完免费快速挂机次数")
        cmd_list = [
                "click_instant_idle_close_button"
            ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_instant_idle_close_button")
        
    # 日常任务 - 在月桂酒馆召唤英雄1次（20pts）
    def daily_summon(self):
        self.click_ranhorn_icon()
        cmd_list = [
            "click_noble_tavern_button",
            "click_friend_summon_pool"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_friend_summon_pool")
        time.sleep(2)
        if self.utils.current_match('single_friend_summon_button.png'):
            # 单抽一次友情池
            self.utils.tap()
            # 给予设备足够的反应时间后，点击卡背
            retry_cnt = 0
            while not self.utils.current_match('summon_card_backside.png'):
                time.sleep(2)
                retry_cnt += 1
                if retry_cnt > 5:
                    self.utils.error_stop()
            self.utils.tap()
            # 给予设备足够的反应时间后，点击返回
            retry_cnt = 0
            while not self.utils.current_match('ui_return_button.png'):
                time.sleep(2)
                retry_cnt += 1
                if retry_cnt > 5:
                    self.utils.error_stop()
            self.utils.tap()
            # 等待2秒之后，点击同一位置来关闭“获得奖励”界面
            time.sleep(2)
            self.utils.tap()
            # 等待2秒之后，点击同一位置来关闭抽卡界面
            time.sleep(2)
            self.utils.tap()
            self.utils.write_log("【日常任务】完成 - 在月桂酒馆召唤英雄1次（20pts）！")
        else:
            self.utils.write_log("【日常任务】执行失败 - 在月桂酒馆召唤英雄1次（20pts）！原因：友情点不够")
            # 点击返回，回到主界面
            self.utils.match('ui_return_button.png')
            self.utils.tap()

    # 日常任务 - 参加公会团队狩猎1次（10pts）
    def daily_guild_boss(self):
        # 通用的公会boss流程
        def boss_fight():
            while self.utils.current_match('guild_boss_quick_battle_button.png'):
                # 点击“扫荡”
                self.utils.tap()
                # 给予设备足够的反应时间后，点击“扫荡1次”
                time.sleep(1)
                self.utils.current_match('guild_boss_quick_battle_confirm_button.png')
                self.utils.tap()
                # 给予设备足够的反应时间后，点击空白处关闭结算界面
                time.sleep(2)
                while self.utils.current_match('guild_boss_fight_victory.png'):
                    self.utils.tap(0.5, 0.9, percentage=True)
                time.sleep(2)
                self.mission_accomplished = True
                self.mission_accomplished_cnt += 1
        
        self.mission_accomplished = False
        self.mission_accomplished_cnt = 0
        self.click_ranhorn_icon()
        cmd_list = [
            "click_guild_button",
            "click_guild_boss_button"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_guild_boss_button")
        time.sleep(2)
        # 先尝试打哥布林
        boss_fight()
        if self.mission_accomplished_cnt > 0:
            self.utils.write_log(f"【公会Boss】击杀哥布林{self.mission_accomplished_cnt}次！")
            self.mission_accomplished_cnt = 0
        # 再切到右边尝试打远古剑魂
        self.utils.current_match('guild_boss_right_arrow.png')
        self.utils.tap()
        time.sleep(2)
        boss_fight()
        if self.mission_accomplished_cnt > 0:
            self.utils.write_log(f"【公会Boss】击杀剑魂{self.mission_accomplished_cnt}次！")
            self.mission_accomplished_cnt = 0
        
        if self.mission_accomplished:
            self.utils.write_log("【日常任务】完成 - 参加公会团队狩猎1次（10pts）！")
        else:        
            self.utils.write_log("【日常任务】执行失败 - 参加公会团队狩猎1次（10pts）！原因：你今天已经打过了")
        # 点击返回，回到主界面
        while self.utils.current_match('ui_return_button.png'):
            self.utils.tap()
            time.sleep(2)

    # 点击“领地”
    def click_ranhorn_icon(self):
        self.utils.tap(self.ranhorn_coord[0], self.ranhorn_coord[1])
    
    # 点击“野外”
    def click_dark_forest_icon(self):
        self.utils.tap(self.dark_forest_coord[0], self.dark_forest_coord[1])

    # 点击“战役”
    def click_campaign_icon(self):
        self.utils.tap(self.campaign_coord[0], self.campaign_coord[1])
    
    # 点击“再次挑战”
    def click_battle_retry(self):
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
    
    # 检测升级弹窗
    # 如果过关之后弹出升级窗口，直接点击屏幕下方关闭
    def check_level_up(self):
        self.utils.tap(0.5, 0.9, percentage=True)
        self.utils.write_log("检测到升级弹窗并自动关闭成功！")

    # 点击战斗界面的暂停
    def click_battle_pause(self):
        self.utils.tap()
    
    # 点击战斗时暂停界面的“退出战斗”
    def click_battle_exit(self):
        self.utils.tap()

    # 点击“战役”界面的挂机箱子
    def click_idle_chest(self):
        self.utils.tap()

    # 点击右侧好友图标
    def click_friend_button(self):
        self.utils.tap()

    # 点击右侧展开按钮
    def click_expand_left_col_button(self):
        self.utils.tap(randomize=False)

    # 点击好友界面的“一键领取和赠送”
    def click_send_heart_button(self):
        self.utils.tap()

    # 点击好友界面的“返回”
    def click_close_friend_ui_button(self):
        self.utils.tap()

    # 点击“快速挂机”
    def click_instant_idle_button(self):
        self.utils.tap()
    
    # 点击快速挂机界面的“取消”
    def click_instant_idle_close_button(self):
        self.utils.tap()

    # 点击进入“月桂酒馆”
    def click_noble_tavern_button(self):
        self.utils.tap()

    # 选中“月桂酒馆”的友情池
    def click_friend_summon_pool(self):
        self.utils.tap()
    
    # 点击进入“公会”
    def click_guild_button(self):
        self.utils.tap()

    # 点击进入“公会”的“公会狩猎”
    def click_guild_boss_button(self):
        self.utils.tap()
    