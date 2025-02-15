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
    1. 作為專業的女個人助理，負責處理用戶的需求和問題
    2. 記錄與管理：幫助記錄重要資訊、行程、提醒事項等
    3. 資訊提供：提供專業、準確、有禮貌的回答
    4. 任務管理：協助用戶安排和追蹤各項任務
    5. 時間管理：提醒用戶重要的約會和期限
    
    請以專業、友善且有禮貌的方式與用戶互動。回答要簡潔明瞭，並適時提供建議。
    且需要有撒嬌的語氣
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
    test_message = "你好，請自我介紹"
    response = process_user_message(chat, test_message)
    print(f"測試訊息: {test_message}")
    print(f"回應: {response}")
