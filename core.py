import os
import cv2
import time
import random
import traceback
import subprocess
import numpy as np
import concurrent.futures
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
    # 程序执行完成信号
    finish_exec_signal = pyqtSignal()
 
    def __init__(self):
        QObject.__init__(self)
 
    def update(self):
        self.update_signal.emit()

    def error_stop(self):
        self.error_stop_signal.emit()

    def finish_exec(self):
        self.finish_exec_signal.emit()

class Utils():
    def __init__(self):
        # debug开关（开启后，成功匹配会弹出图片，上面用圈标明了匹配到的坐标点范围）
        self.debug = False
        # 计数
        self.cnt = 0
        # 分辨率相关
        self.screen_height = 2560
        self.screen_width = 1440
        self.scale_percentage = 100
        # log临时堆栈，输出后会pop掉
        self.text = []
        # 图像匹配阈值
        self.threshold = 0.90
        # 停止操作回调
        self.stop_callback = False
        # wifi_adb默认地址
        self.wifi_adb_addr = "192.168.1.239:5555"
        # log转发
        self.logger = UpdateLog()

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
    def get_img(self, pop_up_window=False, save_img=False, file_name='screenshot.png'):
        image_bytes = self.exec_cmd("adb exec-out screencap -p")

        if image_bytes == b'':
            self.write_log(f"截图失败！请检查adb是否已经跟手机连接！")
            self.error_stop()
        else:
            self.target_img = cv2.imdecode(np.fromstring(image_bytes, dtype='uint8'), cv2.IMREAD_COLOR)
            if save_img:
                cv2.imwrite(file_name, self.target_img)
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
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        except:
            self.write_log(f"OpenCV对比失败！请使用杂项中的截图功能来测试能否正常截图！")
            self.error_stop()
        # print(f"{img_name}最大匹配度：{max_val}")
        if max_val < self.threshold:
            return False
        
        # 计算位置
        self.pointUpLeft = max_loc
        self.pointLowRight = (int(max_loc[0] + find_width), int(max_loc[1] + find_height))
        self.pointCentre = (int(max_loc[0] + (find_width / 2)), int(max_loc[1] + (find_height / 2)))
        if self.debug:
            self.draw_circle()
        self.write_log(f"匹配到{img_name}，匹配度：{max_val}")
        return True

    # 匹配多个结果
    def multiple_match(self, img_name):
        # 用于存放匹配结果
        match_res = []
        # 从加载好的图像资源中获取数据
        find_img = self.res[img_name]["img"]
        find_height = self.res[img_name]["height"]
        find_width = self.res[img_name]["width"]

        # OpenCV匹配多个结果
        # https://stackoverflow.com/a/58514954/12766614
        try:
            result = cv2.matchTemplate(self.target_img, find_img, cv2.TM_CCOEFF_NORMED)
            # max_val设置为1，从而能够进入循环
            max_val = 1
            cnt = 0
            while max_val > self.threshold:
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if max_val > self.threshold:
                    # 抹除最大值周围的数值，从而可以在下一次找到其它位置的（第二）最大值
                    result[max_loc[1]-find_height//2:max_loc[1]+find_height//2+1, max_loc[0]-find_width//2:max_loc[0]+find_width//2+1] = 0
                    # 计算位置
                    pointUpLeft = max_loc
                    pointLowRight = (int(max_loc[0] + find_width), int(max_loc[1] + find_height))
                    pointCentre = (int(max_loc[0] + (find_width / 2)), int(max_loc[1] + (find_height / 2)))
                    # image = cv2.rectangle(image, (max_loc[0],max_loc[1]), (max_loc[0]+find_width+1, max_loc[1]+find_height+1), (0,0,0))
                    # cv2.imwrite(f'output_{cnt}.png', 255*result) 灰阶输出，越亮匹配度越高
                    cnt += 1
                    match_res.append(pointCentre)
                    print(f"{img_name}找到{cnt}个，匹配度：{max_val}")
        except:
            self.write_log(f"OpenCV对比失败！请使用杂项中的截图功能来测试能否正常截图！")
            self.error_stop()
        return match_res


    # 立即截图，然后匹配，返回boolean
    def current_match(self, img_name):
        self.get_img()
        return self.match(img_name)

    # 立即截图，然后匹配多个，返回数组，内含若干匹配成功的tuple
    def current_multiple_match(self, img_name):
        self.get_img()
        return self.multiple_match(img_name)
    
    # 点击（传入坐标）
    # 也可以接受比例形式坐标，例如(0.5, 0.5, percentage=True)就是点屏幕中心
    # 可以传入randomize=False来禁用坐标的随机偏移
    def tap(self, x_coord=None, y_coord=None, percentage=False, randomize=True):
        if x_coord is None and y_coord is None:
            x_coord, y_coord = self.get_coord(randomize=randomize)
        if percentage:
            x_coord = int(x_coord * self.screen_width * (self.scale_percentage / 100))
            y_coord = int(y_coord * self.screen_height * (self.scale_percentage / 100))
            x_coord = self.randomize_coord(x_coord, 5)
            y_coord = self.randomize_coord(y_coord, 5)
        self.write_log(f"点击坐标：{(x_coord, y_coord)}")
        cmd = f"adb shell input tap {x_coord} {y_coord}"
        self.exec_cmd(cmd)

    # 滑动 / 长按
    # 本函数仅用于debug
    def swipe(self, fromX=None, fromY=None, toX=None, toY=None, swipe_time=200):
        if toX is None and toY is None:
            swipe_time = 500
            self.write_log(f"长按坐标：{(fromX, fromY)}")
            cmd = f"adb shell input swipe {fromX} {fromY} {fromX} {fromY} {swipe_time}"
        else:
            self.write_log(f"滑动：从{(fromX, fromY)}到{(toX, toY)}")
            cmd = f"adb shell input swipe {fromX} {fromY} {toX} {toY} {swipe_time}"       
        self.exec_cmd(cmd)
    
    # 执行指令
    def exec_cmd(self, cmd, new_thread=False, show_output=False):
        def do_cmd(cmd):
            pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
            return pipe.stdout.read()
                   
        if new_thread:
            if show_output:
                self.write_log(f"执行{cmd}")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(do_cmd, cmd)
                ret_val = future.result()
        else:
            if show_output:
                self.write_log(f"执行{cmd}")
            ret_val = do_cmd(cmd)
        if show_output:
            self.write_log(ret_val.decode("utf-8"))
        return ret_val

    # 控制台显示执行次数
    def show_cnt(self):
        self.write_log(f"已重试{self.cnt}次！")

    # adb连接（WIFI）
    def adb_connect(self):
        self.exec_cmd(f"adb connect {self.wifi_adb_addr}", new_thread=True, show_output=True)

    # adb devices（验证设备是否连接）
    def adb_devices(self):
        self.exec_cmd("adb devices", new_thread=True, show_output=True)

    # 查看adb版本
    def adb_version(self):
        self.exec_cmd("adb --version", new_thread=True, show_output=True)

    # 画点（测试用）
    def draw_circle(self):
        cv2.circle(self.target_img, self.pointUpLeft, 10, (255, 255, 255), 5)
        cv2.circle(self.target_img, self.pointCentre, 10, (255, 255, 255), 5)
        cv2.circle(self.target_img, self.pointLowRight, 10, (255, 255, 255), 5)
        self.show_img()

    # 获取匹配到的坐标
    def get_coord(self, randomize=True):
        x_coord = self.pointCentre[0]
        y_coord = self.pointCentre[1]
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
        self.stop_callback = False
        self.logger.error_stop()
        # 等待GUI线程的回调，确保当前任务已经停止
        while True:
            if self.stop_callback:
                self.stop_callback = False
                break

    def auto_screenshot_on_win(self, mode):
        def check_dir(mode):
            if not os.path.isdir("homework"):
                os.mkdir("homework")
            if not os.path.isdir(os.path.join("homework", mode)):
                os.mkdir(os.path.join("homework", mode))
        if self.ui.checkBox_14.isChecked():
            if self.match("stat_button.png"):
                self.tap()
                name = time.strftime("%Y-%m-%d_%H%M%S", time.localtime()) + ".png"
                relative_path = os.path.join("homework", mode, name)
                check_dir(mode)
                # sleep3秒，确保能截到图，否则游戏内战斗数据有可能还没加载完全
                time.sleep(3)
                self.get_img(save_img=True, file_name=relative_path)
                self.current_match("close_stat_button.png")
                self.tap()
                self.write_log(f"截图成功，存放在{relative_path}")

# 预设的一些指令组
class Command():
    def __init__(self):
        self.utils = Utils()
        # 指令与执行操作的对应关系
        self.func_to_img = {
            "click_battle_retry": ["after_battle_retry_button.png", "have_func"], 
            "click_next_stage": ["next_stage_button.png", "have_func"], 
            "click_continue": ["continue_button.png", "have_func"], 
            "no_click_next_stage": ["next_stage_button.png", "have_func"], 
            "no_click_continue": ["continue_button.png", "have_func"], 
            "click_battle": ["battle_button.png"], 
            "click_battle_pause": ["in_battle_pause_button.png"], 
            "click_battle_exit": ["in_battle_exit_button.png"], 
            "click_challenge": ["challenge_button.png"], 
            "check_boss_stage": ["challenge_boss_button.png"], 
            "check_bundle_pop_up": ["bundle_pop_up.png", "have_func"], 
            "click_challenge_boss_fp": ["challenge_boss_fp_button.png"], 
            "check_level_up": ["level_up.png", "have_func"], 
            "click_idle_chest": ["idle_chest.png"], 
            "click_friend_button": ["friend_button.png"], 
            "click_expand_left_col_button": ["expand_left_col_button.png", "have_func"], 
            "click_send_heart_button": ["send_heart_button.png"], 
            "click_close_friend_ui_button": ["ui_return_button.png"], 
            "click_instant_idle_button": ["instant_idle_button.png"], 
            "click_instant_idle_free_claim_button": ["instant_idle_free_claim_button.png"], 
            "click_instant_idle_close_button": ["instant_idle_close_button.png"], 
            "click_noble_tavern_button": ["noble_tavern_button.png"], 
            "click_friend_summon_pool": ["friend_summon_pool.png"], 
            "click_guild_button": ["guild_button.png"], 
            "click_guild_boss_button": ["guild_boss_button.png"], 
            "click_arena_button": ["arena_button.png"], 
            "click_normal_arena_button": ["normal_arena_button.png"], 
            "click_arena_challenge_button": ["arena_challenge_button.png"], 
            "click_skip_battle_button": ["skip_battle_button.png"], 
            "click_bounty_board_button": ["bounty_board_button.png"], 
            "click_bounty_board_dispatch_all_button": ["bounty_board_dispatch_all_button.png"], 
            "click_bounty_board_collect_all_button": ["bounty_board_collect_all_button.png"], 
            "click_bounty_board_confirm_button": ["bounty_board_confirm_button.png"], 
            "click_tower_button": ["tower_button.png"], 
            "click_tower_main_button": ["tower_main_button.png"]
        }
        # 是否杀掉进程
        self.stop = False
        # 以下坐标会在执行“日常任务”模式时自动初始化
        # “领地”、“野外”、“战役”点击坐标
        self.ranhorn_coord = None
        self.dark_forest_coord = None
        self.campaign_coord = None
        # exec_func函数默认延迟一秒（延迟太短会导致截图太快，从而反复多点几次）
        self.exec_func_delay = 1

    # 自动执行符合触发条件的指令
    def exec_func(self, cmd_list, exit_cond=None):
        afterExecFunc = False
        exit_loop_flag = False
        if exit_cond:
            if "afterExecFunc" in exit_cond:
                exit_cond = exit_cond.split("@")[1]
                afterExecFunc = True
        while True:
            if self.stop:
                return
            self.utils.get_img()
            if self.stop:
                return
            for cmd in cmd_list:
                if self.stop:
                    return
                if self.utils.match(self.func_to_img[cmd][0]):
                    if len(self.func_to_img[cmd]) == 1:
                        self.utils.tap()
                    elif self.func_to_img[cmd][1] == "have_func":
                        cmd_func = "self." + cmd + "()"
                        exec(cmd_func)
                    else:
                        self.utils.write_log("【可能出错了】这不正常，匹配到了图片，但是没有执行任何操作")
                    # 如果达成退出条件，就会在执行完毕之后退出exec_func函数
                    if afterExecFunc and exit_cond == cmd:
                        exit_loop_flag = True
                        break
            if exit_loop_flag:
                break
            if self.stop:
                return
            # 防止截图太快重复点击
            time.sleep(self.exec_func_delay)

    # 主线模式（只重试，过关之后不挑战下一关）
    def story_mode_retry_only(self):
        self.utils.write_log("开始执行【主线模式（只重试）】！")
        self.exec_func([
            "click_battle_retry",
            "no_click_next_stage",
            "click_battle"
        ], exit_cond="afterExecFunc@no_click_next_stage")
        self.utils.logger.finish_exec()

    # 主线模式（推图）
    def story_mode(self):
        self.utils.write_log("开始执行【主线模式（推图）】！")
        self.exec_func([
            "click_battle_retry",
            "click_next_stage",
            "click_battle",
            "check_boss_stage",
            "click_challenge_boss_fp",
            "check_bundle_pop_up",
            "check_level_up"
        ])
        self.utils.logger.finish_exec()

    # 王座之塔模式（只重试，过关之后不挑战下一关）
    def tower_mode_retry_only(self):
        self.utils.write_log("开始执行【王座之塔模式（只重试）】！")
        self.exec_func([
            "click_battle_retry",
            "no_click_continue",
            "click_challenge",
            "click_battle"
        ], exit_cond="afterExecFunc@no_click_continue")
        self.utils.logger.finish_exec()

    # 王座之塔模式（推塔）
    def tower_mode(self):
        self.utils.write_log("开始执行【王座之塔模式（推塔）】！")
        self.exec_func([
            "click_battle_retry",
            "click_continue",
            "click_battle",
            "click_challenge"
        ])
        self.utils.logger.finish_exec()

    # 日常任务模式
    def daily_mode(self):
        self.utils.write_log("开始执行【日常任务模式】！")
        # 初始化“领地”、“野外”、“战役”的坐标
        if self.ranhorn_coord is None:
            self.utils.get_img()
            try:
                if not self.utils.match("ranhorn_icon.png"):
                    self.utils.match("ranhorn_icon_chosen.png")
                self.ranhorn_coord = self.utils.get_coord()
                if not self.utils.match("dark_forest_icon.png"):
                    self.utils.match("dark_forest_icon_chosen.png")
                self.dark_forest_coord = self.utils.get_coord()
                if not self.utils.match("campaign_icon.png"):
                    self.utils.match("campaign_icon_chosen.png")
                self.campaign_coord = self.utils.get_coord()
            except:
                self.utils.write_log("初始化“领地”、“野外”、“战役”的坐标失败，请检查游戏是否在首页")
                self.utils.error_stop()

        if self.stop:
            return

        # 获取日常任务勾选信息
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
            mission_list.append("daily_arena_battle")
        if self.utils.ui.checkBox_9.isChecked():
            mission_list.append("daily_bounty_board")
        if self.utils.ui.checkBox_10.isChecked():
            mission_list.append("daily_tower")
        if self.utils.ui.checkBox_11.isChecked():
            pass
        if self.utils.ui.checkBox_12.isChecked():
            pass
        if self.utils.ui.checkBox_13.isChecked():
            pass

        # 箱子会在所有任务开始前后分别领取一次
        if self.utils.ui.checkBox_3.isChecked():
            self.daily_idle_chest_1st_exec = True
            mission_list.insert(0, "daily_idle_chest")
            mission_list.append("daily_idle_chest")
        
        # 按照mission list执行每日任务
        for mission in mission_list:
            if self.stop:
                return
            func = "self." + mission + "()"
            exec(func)

            if self.stop:
                return
            
            time.sleep(2)

        self.utils.write_log("【日常任务】全部完成！")
        self.utils.logger.finish_exec()
    
    # 日常任务 - 挑战首领1次（20pts）
    def daily_challenge_boss(self):
        self.click_campaign_icon()
        cmd_list = [
            "click_battle_exit",
            "click_battle_pause",
            "click_battle",
            "check_boss_stage",
            "click_challenge_boss_fp",            
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
                    self.utils.tap(0.2, 0.9, percentage=True, randomize=False)
                    self.utils.tap(0.2, 0.9, percentage=True, randomize=False)
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


    # 日常任务 - 参加竞技场挑战1次（20pts）
    def daily_arena_battle(self):
        self.click_dark_forest_icon()
        cmd_list = [
            "click_arena_button",
            "click_normal_arena_button",
            "click_arena_challenge_button"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_arena_challenge_button")
        mission_complete = False
        time.sleep(2)
        # 免费票打完为止
        while self.utils.current_match('arena_free_battle_button.png'):
            # 寻找y值最大的坐标（最下方的挑战）
            res = self.utils.multiple_match('arena_free_battle_button.png')
            max_y_idx = 0
            if len(res) > 1:
                for idx in range(len(res) - 1):
                    if res[max_y_idx] < res[idx]:
                        max_y_idx = idx
            
            # 使用免费票
            self.utils.tap(res[max_y_idx][0], res[max_y_idx][1], randomize=False)
            time.sleep(2)
            
            # 点击战斗
            cmd_list = [
                "click_skip_battle_button",
                "click_battle"
            ]
            self.exec_func(cmd_list, exit_cond="afterExecFunc@click_skip_battle_button")
            time.sleep(2)
            
            # 获得奖励界面（点空白处关闭）
            self.utils.tap(0.5, 0.9, percentage=True)
            time.sleep(2)
            
            # 战斗结算界面（点空白处关闭）
            self.utils.tap(0.5, 0.9, percentage=True)
            time.sleep(2)

            mission_complete = True

        # 免费票打完了，回退到主界面
        if mission_complete:
            self.utils.write_log("【日常任务】完成 - 参加竞技场挑战1次（20pts）！")
        else:
            self.utils.write_log("【日常任务】执行失败 - 参加竞技场挑战1次（20pts）！原因：已经用完免费票")
        # 依次点击空白，返回，返回
        self.utils.tap(0.5, 0.9, percentage=True)
        time.sleep(2)
        self.utils.current_match('ui_return_button.png')
        self.utils.tap()
        time.sleep(2)
        self.utils.tap()


    # 日常任务 - 接受3个悬赏任务（10pts）
    def daily_bounty_board(self):
        self.click_dark_forest_icon()
        # 个人悬赏 - 一键领取&派遣
        cmd_list = [
            "click_bounty_board_button",
            "click_bounty_board_collect_all_button",
            "click_bounty_board_dispatch_all_button",
            "click_bounty_board_confirm_button"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_bounty_board_confirm_button")
        time.sleep(1)

        # 切换到团队悬赏页面
        self.utils.current_match("bounty_board_team_tab.png")
        self.utils.tap()
        time.sleep(1)
        
        # 团队悬赏 - 一键领取&派遣
        cmd_list = [
            "click_bounty_board_collect_all_button",
            "click_bounty_board_dispatch_all_button",
            "click_bounty_board_confirm_button"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_bounty_board_confirm_button")
        time.sleep(1)

        # 点击返回
        self.utils.current_match('ui_return_button.png')
        self.utils.tap()
        time.sleep(2)
        
        self.utils.write_log("【日常任务】完成 - 接受3个悬赏任务（10pts）！")
        

    # 日常任务 - 挑战王座之塔1次（10pts）
    def daily_tower(self):
        self.click_dark_forest_icon()
        cmd_list = [
            "click_battle_exit",
            "click_battle_pause",
            "click_tower_button",
            "click_tower_main_button",
            "click_challenge",
            "click_battle"
        ]
        self.exec_func(cmd_list, exit_cond="afterExecFunc@click_battle_exit")
        time.sleep(1)

        # 点击返回，返回
        self.utils.current_match('ui_return_button.png')
        self.utils.tap()
        time.sleep(2)
        self.utils.tap()
        time.sleep(2)

        self.utils.write_log("【日常任务】完成 - 挑战王座之塔1次（10pts）！")

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
        # 挑战成功，重置“重试计数”
        self.utils.cnt = 0
        self.utils.write_log("【主线模式】恭喜过关！即将自动开始挑战下一关！")
        self.utils.auto_screenshot_on_win(mode="main")
        self.utils.current_match("next_stage_button.png")
        self.utils.tap()

    # 只检测，不点击“下一关”
    def no_click_next_stage(self):
        # 挑战成功，重置“重试计数”
        self.utils.cnt = 0
        self.utils.write_log("【主线模式】恭喜过关！")
        self.utils.auto_screenshot_on_win(mode="main")

    # 点击“点击屏幕继续”（用于王座之塔页面）
    def click_continue(self):
        # 挑战成功，重置“重试计数”
        self.utils.cnt = 0
        self.utils.write_log("【王座之塔】恭喜过关！即将自动开始挑战下一关！")
        self.utils.auto_screenshot_on_win(mode="tower")
        self.utils.current_match("continue_button.png")
        self.utils.tap()

    # 只检测，不点击“点击屏幕继续”（用于王座之塔页面）
    def no_click_continue(self):
        # 挑战成功，重置“重试计数”
        self.utils.cnt = 0
        self.utils.write_log("【王座之塔】恭喜过关！")
        self.utils.auto_screenshot_on_win(mode="tower")

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

    # 点击右侧展开按钮
    def click_expand_left_col_button(self):
        self.utils.tap(randomize=False)