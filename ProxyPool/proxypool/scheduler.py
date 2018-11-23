import time 
from multiprocessing import Process 
from proxypool.api import app 
from proxypool.getter import Getter 
from proxypool.tester import Tester 
from proxypool.db import RedisClient
from proxypool.setting import * 

class Scheduler():
    def scheduler_tester(self, cycle=TESTER_CYCLE):
        tester = Tester() 
        while True:
            tester.run() 
            time.sleep(cycle)

    def scheduler_getter(self, cycle=GETTER_CYCLE):
        getter = Getter()
        while True:
            getter.run() 
            time.sleep(cycle)
    
    def scheduler_api(self):
        app.run(API_HOST, API_PORT)

    def run(self):
        print('代理池开始运行')

        if TESTER_ENABLED:
            tester_process = Process(target=self.scheduler_tester)
            tester_process.start()
        
        if GETTER_ENABLED:
            getter_process = Process(target=self.scheduler_getter)
            getter_process.start() 
        
        if API_ENABLED:
            api_process = Process(target=self.scheduler_api)
            api_process.start()