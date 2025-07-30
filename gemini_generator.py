# 简单AI回答生成器
import csv
import os
import time
import google.generativeai as genai
from typing import List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class SimpleAIGenerator:
    def __init__(self):
        """初始化AI生成器"""
        # 设置代理（如果需要）
        proxy = os.getenv('HTTP_PROXY', 'http://127.0.0.1:7899')
        if proxy:
            os.environ["http_proxy"] = proxy
            os.environ["https_proxy"] = proxy
            
        # 配置Gemini API
        self.api_key = "AIzaSyDd0iPb6AaKeV9uKtEevo-kERmI_dXJ9mI"
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
            
        self.high_quality_answers = []
        
    def load_high_quality_answers(self, min_score: int = 8) -> List[str]:
        """从scores.csv读取高分回答"""
        high_quality_answers = []
        
        if not os.path.exists('scores.csv'):
            print("警告: scores.csv文件不存在")
            return high_quality_answers
            
        try:
            with open('scores.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'score' in row and 'title' in row:
                        try:
                            score = int(row['score'])
                            if score >= min_score:
                                # 使用标题作为回答内容的代表
                                high_quality_answers.append(row['title'])
                        except (ValueError, TypeError):
                            continue
                            
        except Exception as e:
            print(f"读取scores.csv时发生错误: {e}")
            
        self.high_quality_answers = high_quality_answers
        print(f"成功加载 {len(high_quality_answers)} 个高质量回答")
        return high_quality_answers
    
    def build_prompt(self, question: str, sample_answers: List[str]) -> str:
        """构建用于AI生成的prompt"""
        # 选择前5个高质量回答作为示例
        samples = sample_answers[:5] if len(sample_answers) >= 5 else sample_answers
        
        prompt = "以下是一些高质量的知乎回答标题示例：\n\n"
        
        for i, sample in enumerate(samples, 1):
            prompt += f"示例{i}: {sample}\n"
            
        prompt += f"""
请参考以上高质量回答的风格和深度，回答以下问题：

问题：{question}

要求：
- 回答要有逻辑性和深度
- 语言生动，有说服力  
- 可以结合具体例子或个人见解
- 字数控制在500-1000字之间
- 用中文回答

请生成回答：
"""
        return prompt
    
    def generate_answer(self, question: str) -> dict:
        """生成AI回答"""
        result = {
            'success': False,
            'answer': '',
            'error': ''
        }
        
        # 检查API密钥和模型
        if not self.api_key or not self.model:
            result['error'] = '请先配置Google API密钥'
            return result
            
        # 加载高质量回答（如果还没加载）
        if not self.high_quality_answers:
            self.load_high_quality_answers()
            
        if len(self.high_quality_answers) < 3:
            result['error'] = f'高质量回答数量不足（当前：{len(self.high_quality_answers)}个，建议至少3个）'
            return result
            
        try:
            # 构建prompt
            prompt = self.build_prompt(question, self.high_quality_answers)
            print(f"构建的prompt长度: {len(prompt)} 字符")
            
            print("开始调用Gemini API...")
            # 调用Gemini API（使用默认配置）
            response = self.model.generate_content(prompt)
            
            print("API调用完成，处理响应...")
            if response.parts:
                answer = response.text.strip()
                result['success'] = True
                result['answer'] = answer
                print(f"生成回答长度: {len(answer)} 字符")
            else:
                result['error'] = 'Gemini API返回空响应'
                print("警告: API返回空响应")
                
            # 添加延时避免API调用过快
            time.sleep(1)
            
        except Exception as e:
            error_msg = str(e)
            if 'API_KEY' in error_msg:
                result['error'] = 'Google API密钥无效，请检查配置'
            elif 'quota' in error_msg.lower():
                result['error'] = 'API调用配额超限，请稍后重试'
            elif 'rate' in error_msg.lower():
                result['error'] = 'API调用频率超限，请稍后重试'
            else:
                result['error'] = f'生成回答时发生错误: {error_msg}'
            
        return result

# 测试函数
def test_generator():
    """测试AI生成器功能"""
    generator = SimpleAIGenerator()
    
    # 测试加载高质量回答
    answers = generator.load_high_quality_answers()
    print(f"加载了 {len(answers)} 个高质量回答")
    
    if len(answers) > 0:
        print("前3个示例:")
        for i, answer in enumerate(answers[:3], 1):
            print(f"{i}. {answer}")
    
    # 测试生成回答
    test_question = "如何提高工作效率？"
    print(f"\n测试问题: {test_question}")
    print("正在调用Gemini API生成回答...")
    
    result = generator.generate_answer(test_question)
    if result['success']:
        print("生成成功!")
        print("回答内容:")
        print(result['answer'])
    else:
        print(f"生成失败: {result['error']}")

if __name__ == "__main__":
    test_generator()