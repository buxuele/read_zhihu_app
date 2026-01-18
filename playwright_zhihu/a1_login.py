import time
import json
from playwright.sync_api import sync_playwright

URL = "https://www.zhihu.com/" 
JSON_NAME = "cookies.json"

class PlaywrightLogin:
    def __init__(self):
        self.playwright = sync_playwright().start()
        # headless=False 方便肉眼观察
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def get_clean_cookies(self):
        print(f"正在读取 {JSON_NAME} ...")
        with open(JSON_NAME, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        for c in cookies:
            # 必须移除 sameSite，否则可能被浏览器拒绝
            if "sameSite" in c:
                del c["sameSite"]
            
            # 兼容性处理：Playwright 使用 expires，EditThisCookie 导出的是 expirationDate
            if "expirationDate" in c:
                c["expires"] = c["expirationDate"]
                del c["expirationDate"]
                
        return cookies

    def login(self):
        # 1. 先访问网站
        print(f"打开页面: {URL}")
        self.page.goto(URL)
        time.sleep(2)

        # 2. 获取并注入 Cookies
        cookies = self.get_clean_cookies()
        print(f"正在注入 {len(cookies)} 个 Cookies ...")
        
        # 这里如果没有 try，遇到格式错误的 Cookie 会直接抛出异常，方便你定位问题
        self.context.add_cookies(cookies)

        # 3. 刷新页面使其生效
        print("刷新页面 ...")
        self.page.reload()

        # 4. 停留观察
        print("等待观察登录状态 ...")
        time.sleep(10)

    def close(self):
        self.browser.close()
        self.playwright.stop()

if __name__ == "__main__":
    bot = PlaywrightLogin()
    bot.login()
    bot.close()