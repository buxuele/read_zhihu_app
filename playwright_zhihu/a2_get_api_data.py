import os
import time
import json
import datetime
from datetime import date
from playwright.sync_api import sync_playwright

"""
此文件，使用 playwright：

1. 登录知乎
2. 自动刷新，下载 api 推荐的数据。

"""

URL = "https://www.zhihu.com/"
JSON_NAME = "cookies.json"
TARGET_API = "api/v3/feed/topstory/recommend"

class PlaywrightZhihu:
    def __init__(self):
        self.playwright = sync_playwright().start()
        # 4K 左半屏设置
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=[
                "--window-position=0,0",    
                "--window-size=1200,2000"   
            ]
        )
        
        self.context = self.browser.new_context(viewport=None)
        self.page = self.context.new_page()

        # 数据保存路径
        self.data_folder = date.today().isoformat()  
        os.makedirs(self.data_folder, exist_ok=True)
        
        # 标记是否正在运行，用于安全退出判断
        self.is_running = True

    def get_clean_cookies(self):
        print(f"读取 {JSON_NAME} ...")
        try:
            with open(JSON_NAME, "r", encoding="utf-8") as f:
                cookies = json.load(f)
        except FileNotFoundError:
            print(" 未找到 cookies.json，请检查文件位置。")
            return []

        for c in cookies:
            if "sameSite" in c:
                del c["sameSite"]
            if "expirationDate" in c:
                c["expires"] = c["expirationDate"]
                del c["expirationDate"]
        return cookies

    # 【核心逻辑】监听网络响应
    def handle_response(self, response):
        # 1. 如果脚本已经标记停止，或者页面已关闭，直接忽略后续请求，防止报错
        if not self.is_running or self.page.is_closed():
            return

        try:
            # 只处理包含目标 API 且请求成功的响应
            if TARGET_API in response.url and response.status == 200:
                print(f"捕获到推荐流数据: {response.url[:60]}...")
                
                # 2. 加上 try-except 保护 json 解析
                # 防止在浏览器关闭的一瞬间，body 还没下载完导致报错
                try:
                    data = response.json()
                except Exception as e:
                    print(f"️ 获取响应体失败 (可能浏览器已关闭): {e}")
                    return

                # 生成文件名
                timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                filename = f"./{self.data_folder}/zhihu_recommend_{timestamp}.json"
                
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"--> 已保存到: {filename}")
        except Exception as e:
            # 捕获其他未知错误，防止中断主线程
            print(f"️ 处理响应时发生非致命错误: {e}")

    def run(self):
        # 1. 登录逻辑
        print(f"打开页面: {URL}")
        self.page.goto(URL)
        time.sleep(2)

        cookies = self.get_clean_cookies()
        if cookies:
            self.context.add_cookies(cookies)

        print("刷新页面 ...")
        self.page.reload()
        
        # 2. 注册监听器
        self.page.on("response", self.handle_response)

        print("登录完成，监听器已就绪。开始模拟滚动...")
        time.sleep(2)

        # 3. 模拟滚动
        # 滚动 20 次
        try:
            for i in range(20):
                if not self.is_running: break # 允许中途打断
                print(f"第 {i+1}/20 次滚动...")
                self.page.keyboard.press("End") 
                time.sleep(2) 
        except KeyboardInterrupt:
            print("\n 用户强制中断...")

        print("采集结束，准备清理...")
        
        # 4. 【关键步骤】在退出前，主动移除监听器
        # 这能防止关闭浏览器时，残留的请求触发回调报错
        self.is_running = False # 设置标志位
        try:
            self.page.remove_listener("response", self.handle_response)
        except:
            pass # 如果已经移除了也不要紧

        # 停留一会儿确保最后的 IO 写完
        time.sleep(3)

    def close(self):
        print("正在关闭浏览器...")
        try:
            self.browser.close()
            self.playwright.stop()
        except Exception as e:
            print(f"关闭时出现轻微异常(可忽略): {e}")
        print(" 程序已安全退出。")

if __name__ == "__main__":
    bot = PlaywrightZhihu()
    try:
        bot.run()
    finally:
        bot.close()
