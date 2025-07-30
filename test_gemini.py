# 测试Gemini API连接
import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置代理
os.environ["http_proxy"] = "http://127.0.0.1:7899"
os.environ["https_proxy"] = "http://127.0.0.1:7899"

# 配置API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
print(f"API Key: {GOOGLE_API_KEY[:10]}..." if GOOGLE_API_KEY else "API Key未找到")

genai.configure(api_key=GOOGLE_API_KEY)

# 创建模型
model = genai.GenerativeModel("gemini-2.0-flash-exp")

# 简单测试
prompt = "请用一句话介绍自己"
print(f"测试prompt: {prompt}")

try:
    print("开始调用API...")
    response = model.generate_content(prompt)
    print("API调用成功!")
    
    if response.parts:
        print(f"响应: {response.text}")
    else:
        print("响应为空")
        
except Exception as e:
    print(f"API调用失败: {e}")
    print(f"错误类型: {type(e)}")