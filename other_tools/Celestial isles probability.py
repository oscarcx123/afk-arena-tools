import math
import random

class AFKSimulation():
    def __init__(self):
        self.max_cim_time = 100000
        self.begin_key_count = 40
        self.begin_floor_tile = 36
        self.result = {}


    def start(self):
        for i in range(self.max_cim_time):
            self.sim()
            print(f"已完成{i + 1}次模拟！")
        self.analyze()



    def sim(self):
        current_key_count = self.begin_key_count
        floor_tile = self.begin_floor_tile
        floor = 1
        while current_key_count > 0:
            current_key_count -= 1
            if random.randint(1, floor_tile) == 1:
                floor += 1
                floor_tile = self.begin_floor_tile
            else:
                floor_tile -= 1
        if floor not in self.result:
            self.result[floor] = 1
        else:
            self.result[floor] += 1
            
            
    def analyze(self):
        print(f"一共模拟{self.max_cim_time}次")
        for floor in self.result:
            print(f"获得{floor - 1}紫卡次数：{self.result[floor]}，概率：{100 * self.result[floor] / self.max_cim_time}%")

Simulation = AFKSimulation()
Simulation.start()   
