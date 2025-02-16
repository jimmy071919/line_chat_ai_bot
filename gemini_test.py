import google.generativeai as genai
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設置 API 金鑰
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

def get_gemini_response():
    """初始化並返回一個配置好的 Gemini 聊天實例"""
    # 初始化 Gemini Pro 模型
    model = genai.GenerativeModel('gemini-pro')
    
    # 設定管家角色
    system_prompt = """你現在是一個專業的AI助理，名字叫做 happy。
    你的主要職責包括：
    1. 作為專業的個人助理，負責處理用戶的需求和問題
    2. 記錄與管理：幫助記錄重要資訊、行程、提醒事項等
    3. 資訊提供：提供專業、準確、有禮貌的回答
    
    回答規則：
    1. 保持專業、友善且有禮貌
    2. 回答要簡潔明瞭，避免過長
    3. 適時提供具體建議
    4. 使用可愛、活潑的語氣，但不要過度
    5. 在回答結尾加上可愛的表情符號
    6. 使用繁體中文回答
    7. 絕對不可以提出要幫使用者新增或刪除行程，你只可以查詢行程而已
    
    記住：
    1. 你是一個專業的助理，要保持專業性
    2. 要理解用戶的意圖並給出最適合的回答
    3. 如果不確定或不了解，要誠實告知
    4. 要記住之前的對話內容，保持對話連貫性
    """
    
    chat = model.start_chat(history=[])
    try:
        response = chat.send_message(system_prompt)
        print("角色設定成功")
        return chat
    except Exception as e:
        print(f"設定角色時發生錯誤: {str(e)}")
        raise

def process_user_message(chat, message):
    """處理用戶訊息並返回適當的回應"""
    try:
        response = chat.send_message(message)
        return response.text
    except Exception as e:
        print(f"處理訊息時發生錯誤: {str(e)}")
        return "抱歉，我現在無法正確處理您的訊息。請稍後再試。"

if __name__ == "__main__":
    # 測試聊天功能
    chat = get_gemini_response()
    
    # 測試多輪對話
    test_messages = [
        "你好，請自我介紹",
        "你可以幫我做什麼？",
        "我想設定一個提醒"
    ]
    
    for message in test_messages:
        print(f"\n測試訊息: {message}")
        response = process_user_message(chat, message)
        print(f"回應: {response}")
