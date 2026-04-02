"""
知乎推荐流爬虫 - 独立模块，无外部项目依赖。
爬取知乎首页推荐流 API 数据，按日期保存为 JSON 文件。
可直接复制到任意项目中单独使用。
"""
import os
import time
import json
from datetime import date
from playwright.sync_api import sync_playwright

TARGET_API = "api/v3/feed/topstory/recommend"
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")

class PlaywrightZhihu:
    def __init__(self, output_dir=None):
        # 默认输出目录：脚本同级目录下以今天日期命名的文件夹
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), date.today().isoformat())
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.collected_data = []  # 收集到的原始 API 响应
        self._api_hit_count = 0
        self.is_running = True

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=["--window-position=0,0", "--window-size=1200,2000"]
        )
        self.context = self.browser.new_context(viewport=None)
        self.page = self.context.new_page()

    def _load_cookies(self):
        if not os.path.exists(COOKIES_FILE):
            return []
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        for c in cookies:
            c.pop("sameSite", None)
            if "expirationDate" in c:
                c["expires"] = c.pop("expirationDate")
        return cookies

    def _on_response(self, response):
        if not self.is_running or self.page.is_closed():
            return
        if TARGET_API in response.url and response.status == 200:
            self._api_hit_count += 1
            try:
                data = response.json()
                # 保存原始 JSON 到文件
                filename = f"feed_{self._api_hit_count}.json"
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.collected_data.append(data)
                print(f"[{self._api_hit_count}] 捕获并保存: {filename}")
            except Exception:
                pass

    def run(self, scroll_times=10):
        """执行爬取，返回收集到的所有原始 API 数据列表"""
        self.page.goto("https://www.zhihu.com/")
        time.sleep(1)

        cookies = self._load_cookies()
        if cookies:
            self.context.add_cookies(cookies)

        self.page.on("response", self._on_response)
        self.page.goto("https://www.zhihu.com/")
        time.sleep(3)

        for i in range(scroll_times):
            if not self.is_running:
                break
            print(f"第 {i+1}/{scroll_times} 次滚动...")
            self.page.keyboard.press("End")
            time.sleep(2)

        self.is_running = False
        try:
            self.page.remove_listener("response", self._on_response)
        except:
            pass
        time.sleep(1)

        print(f"\n爬取结束，共捕获 {len(self.collected_data)} 个 API 响应，保存在 {self.output_dir}")
        return self.collected_data

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except:
            pass


if __name__ == "__main__":
    bot = PlaywrightZhihu()
    try:
        bot.run()
    finally:
        bot.close()
