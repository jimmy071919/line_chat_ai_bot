from flask import Flask, request, abort, send_file
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent,
    PostbackEvent
)
from linebot.v3.messaging import (
    Configuration, 
    ApiClient, 
    MessagingApi,
    TextMessage,
    TemplateMessage,
    ButtonsTemplate,
    DatetimePickerAction,
    PostbackAction,
    ReplyMessageRequest,
    FlexMessage,
    FlexContainer,
    FlexBubble,
    FlexBox,
    FlexText,
    FlexButton,
    FlexCarousel,
    QuickReply,
    QuickReplyItem
)
from database import Database, init_db, get_db, close_db
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from urllib.parse import parse_qsl, quote
import json
import threading
import pytz
from gemini_test import get_gemini_response
from reminder_handler import reminder_handler

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# 設定Line Bot API
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 初始化 API client
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)

# 用戶狀態管理
user_states = {}
thread_local = threading.local()

# 用戶聊天歷史
user_chat_history = {}

# 初始化 Gemini 聊天
chat = get_gemini_response()

def get_db():
    if not hasattr(thread_local, "db"):
        thread_local.db = Database()
    return thread_local.db

def set_user_state(user_id, state):
    """設置用戶狀態"""
    if isinstance(state, str):
        user_states[user_id] = {"state": state}
    else:
        user_states[user_id] = state

def get_user_state(user_id):
    """獲取用戶狀態"""
    return user_states.get(user_id, {"state": None})

def format_datetime(dt_str):
    """格式化日期時間字符串"""
    try:
        # 嘗試解析不同格式的日期時間
        formats = [
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_str, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        
        raise ValueError(f"無法解析日期時間: {dt_str}")
    except Exception as e:
        print(f"格式化日期時間出錯: {str(e)}")  # 添加日誌
        raise

def handle_schedule_input(user_id, text):
    """處理行程輸入"""
    print(f"處理行程輸入: user_id={user_id}, text={text}")  # 添加日誌
    try:
        user_state = get_user_state(user_id)
        print(f"用戶當前狀態: {user_state}")  # 添加日誌
        db = get_db()
        
        if user_state.get("state") == "waiting_for_schedule":
            # 設置標題
            set_user_state(user_id, {
                "state": "adding_schedule",
                "schedule_title": text,
                "selected_time": user_state.get("selected_time")
            })
            return "請輸入行程描述："
            
        elif user_state.get("state") == "adding_schedule":
            # 設置描述
            schedule_title = user_state.get("schedule_title")
            selected_time = user_state.get("selected_time")
            
            if not schedule_title or not selected_time:
                return "發生錯誤，請重新開始添加行程。"
            
            # 添加行程
            try:
                db.add_schedule(
                    user_id,
                    schedule_title,
                    text,  # 描述
                    selected_time,
                    selected_time  # 暫時使用相同的時間作為結束時間
                )
                
                # 重置狀態
                set_user_state(user_id, {"state": None})
                return "行程已添加！"
                
            except Exception as e:
                print(f"添加行程時發生錯誤: {str(e)}")  # 添加日誌
                return f"添加行程失敗：{str(e)}"
    
    except Exception as e:
        print(f"處理行程輸入時出錯: {str(e)}")  # 添加日誌
        return "處理行程時發生錯誤，請重試。"

def handle_reminder_input(user_id, text):
    """處理提醒輸入"""
    print(f"處理提醒輸入: user_id={user_id}, text={text}")  # 添加日誌
    try:
        user_state = get_user_state(user_id)
        print(f"用戶當前狀態: {user_state}")  # 添加日誌
        db = get_db()
        
        if user_state.get("state") == "waiting_for_reminder":
            try:
                selected_time = user_state.get("selected_time")
                if not selected_time:
                    return "發生錯誤，請重新開始添加提醒。"
                
                # 添加提醒
                db.add_reminder(
                    user_id,
                    text,  # 提醒內容
                    selected_time
                )
                
                # 重置狀態
                set_user_state(user_id, {"state": None})
                return "提醒已添加！"
                
            except Exception as e:
                print(f"添加提醒時發生錯誤: {str(e)}")  # 添加日誌
                return f"添加提醒失敗：{str(e)}"
    
    except Exception as e:
        print(f"處理提醒輸入時出錯: {str(e)}")  # 添加日誌
        return "處理提醒時發生錯誤，請重試。"

def generate_ics_content(schedule):
    """生成 ICS 文件內容
    Args:
        schedule (dict): 行程信息
    Returns:
        str: ICS 文件內容
    """
    start_time = datetime.strptime(schedule['scheduled_time'], '%Y-%m-%d %H:%M:%S')
    end_time = start_time + timedelta(hours=1)
    
    # 轉換為 UTC 時間
    tz = pytz.timezone('Asia/Taipei')
    start_utc = tz.localize(start_time).astimezone(pytz.UTC)
    end_utc = tz.localize(end_time).astimezone(pytz.UTC)
    
    now = datetime.now(pytz.UTC)
    
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Line Bot//Calendar Event//TW",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"DTSTART:{start_utc.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{end_utc.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}",
        f"UID:{schedule['id']}@linebotcalendar",
        f"SUMMARY:{schedule['title']}",
        f"DESCRIPTION:{schedule.get('description', '')}",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    
    return "\r\n".join(ics_content)

def save_ics_file(schedule):
    """保存 ICS 文件
    Args:
        schedule (dict): 行程信息
    Returns:
        str: 文件路徑
    """
    try:
        content = generate_ics_content(schedule)
        file_path = os.path.join(os.path.dirname(__file__), 'temp', f"{schedule['id']}.ics")
        
        # 確保 temp 目錄存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    except Exception as e:
        print(f"保存 ICS 文件時出錯: {e}")
        return None

@app.route('/calendar_events/<event_id>.ics')
def serve_calendar_event(event_id):
    """提供 ICS 文件下載"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'temp', f"{event_id}.ics")
        if os.path.exists(file_path):
            return send_file(
                file_path,
                mimetype='text/calendar',
                as_attachment=True,
                download_name=f'event_{event_id}.ics'
            )
        else:
            return "Calendar event not found", 404
    except Exception as e:
        print(f"提供 ICS 文件時出錯: {e}")
        return "Error serving calendar event", 500

def send_calendar_link(event_id):
    """生成並發送日曆連結"""
    try:
        db = get_db()
        event = db.get_schedule(event_id)
        if not event:
            return None

        # 處理日期時間
        start_time = datetime.strptime(format_datetime(event['start_time']), '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(format_datetime(event['end_time']), '%Y-%m-%d %H:%M:%S')
        
        # 創建 ICS 文件
        c = Calendar()
        e = Event()
        e.name = event['title']
        e.description = event['description']
        
        # 設置時區為台北時間
        taipei = pytz.timezone('Asia/Taipei')
        start_time = taipei.localize(start_time)
        end_time = taipei.localize(end_time)
        
        e.begin = start_time
        e.end = end_time
        c.events.add(e)
        
        # 生成 ICS 文件
        ics_content = str(c)
        
        # 將 ICS 內容寫入臨時文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ics', delete=False, encoding='utf-8') as f:
            f.write(ics_content)
            temp_file_path = f.name
        
        return temp_file_path
        
    except Exception as e:
        print(f"生成日曆文件時出錯: {str(e)}")
        return None

@app.route('/calendar_events/<event_id>.ics')
def serve_calendar_file(event_id):
    temp_file_path = send_calendar_link(event_id)
    if temp_file_path:
        return send_file(temp_file_path, 
                        mimetype='text/calendar',
                        as_attachment=True,
                        download_name=f"event_{event_id}.ics")
    else:
        return "找不到指定的行程"

@app.route("/")
def home():
    return 'Line Bot is running!'

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def create_note_bubble(note):
    """創建筆記氣泡
    Args:
        note (dict): 包含筆記數據的字典，包括 id, user_id, content, created_at
    Returns:
        FlexBubble: 筆記氣泡
    """
    # 從字典中獲取數據
    note_id = note['id']
    content = note['content']
    created_at = note['created_at']
    
    # 將 note_id 轉換為字符串，確保它是有效的
    note_id_str = str(note_id)
    
    # 格式化創建時間
    try:
        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        created_at_str = dt.strftime("%Y-%m-%d %H:%M")
    except:
        created_at_str = created_at
    
    return FlexBubble(
        size="kilo",
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(text=f"記事 #{note_id_str}", weight="bold", size="xl"),
                FlexText(text=content, wrap=True, size="md", margin="md"),
                FlexText(text=created_at_str, size="xs", color="#aaaaaa", margin="md"),
                FlexBox(
                    layout="horizontal",
                    margin="md",
                    contents=[
                        FlexButton(
                            style="link",
                            height="sm",
                            action=PostbackAction(
                                label="刪除",
                                data=f"action=delete_note&id={note_id_str}"
                            )
                        )
                    ]
                )
            ]
        )
    )

def create_schedule_bubble(schedule):
    """創建行程氣泡"""
    scheduled_time = schedule['scheduled_time'] if schedule['scheduled_time'] else "未設定"
    title = schedule['title'] if schedule['title'] else "未設定標題"
    description = schedule['description'] if schedule['description'] else "無詳細內容"
    remind_before = schedule['remind_before'] if schedule['remind_before'] else 5
    
    # 格式化提醒時間顯示
    remind_text = "提前 "
    if remind_before >= 1440:  # 1天 = 1440分鐘
        remind_text += f"{remind_before // 1440} 天"
    elif remind_before >= 60:  # 1小時 = 60分鐘
        remind_text += f"{remind_before // 60} 小時"
    else:
        remind_text += f"{remind_before} 分鐘"
    remind_text += "提醒"
    
    return FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            contents=[
                FlexText(text=f"行程 #{schedule['id']}", weight="bold", size="xl"),
                FlexText(text=title, size="lg", wrap=True),
            ]
        ),
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(text=description, wrap=True),
                FlexText(text=f"時間：{scheduled_time}", size="sm"),
                FlexText(text=f"提醒：{remind_text}", size="sm"),
            ]
        ),
        footer=FlexBox(
            layout="horizontal",
            spacing="sm",
            contents=[
                FlexButton(
                    style="link",
                    height="sm",
                    action=PostbackAction(label="刪除", data=f"action=delete_schedule&id={schedule['id']}")
                ),
                FlexButton(
                    style="link",
                    height="sm",
                    action=PostbackAction(label="加入行事曆", data=f"action=add_to_calendar&id={schedule['id']}")
                )
            ]
        )
    )

def create_reminder_bubble(reminder):
    """創建提醒氣泡"""
    # 確保所有文字欄位都有值
    content = reminder['content'] if reminder['content'] else "無內容"
    reminder_time = reminder['reminder_time'] if reminder['reminder_time'] else "未設定"

    return FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            contents=[
                FlexText(text=f"提醒 #{reminder['id']}", weight="bold", size="xl"),
            ]
        ),
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(text=content, wrap=True),
                FlexText(text=f"提醒時間: {reminder_time}", size="sm"),
            ]
        ),
        footer=FlexBox(
            layout="horizontal",
            spacing="sm",
            contents=[
                FlexButton(
                    style="link",
                    height="sm",
                    action=PostbackAction(label="刪除", data=f"action=delete_reminder&id={reminder['id']}")
                )
            ]
        )
    )

def parse_postback_data(data):
    """解析 postback 數據
    Args:
        data (str): postback 數據字符串
    Returns:
        dict: 解析後的數據字典
    """
    try:
        if not data:
            return {}
        return dict(parse_qsl(data))
    except Exception as e:
        print(f"解析 postback 數據出錯: {e}")
        return {}

@handler.add(PostbackEvent)
def handle_postback(event):
    """處理 Postback 事件"""
    user_id = event.source.user_id
    data = parse_postback_data(event.postback.data)
    params = event.postback.params
    
    print(f"處理 Postback: action={data.get('action')}, data={data}, params={params}")
    
    if data.get('action') == 'note':
        db = Database()
        db.set_user_state(user_id, {'state': 'waiting_for_note'})
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="請輸入要記錄的內容：")]
            )
        )
    
    elif data.get('action') == "schedule":
        # 顯示時間選擇器
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TemplateMessage(
                        alt_text="選擇時間",
                        template=ButtonsTemplate(
                            title="選擇時間",
                            text="請選擇行程時間",
                            actions=[
                                DatetimePickerAction(
                                    label="選擇時間",
                                    data="action=add_schedule",
                                    mode="datetime"
                                )
                            ]
                        )
                    )
                ]
            )
        )
    
    elif data.get('action') == "add_schedule":
        if hasattr(event.postback, 'params') and event.postback.params:
            selected_time = event.postback.params.get('datetime')
            print(f"用戶選擇的時間: {selected_time}")
            
            if selected_time:
                # 將選擇的時間保存到用戶狀態
                db = Database()
                db.set_user_state(user_id, {
                    'state': 'waiting_for_schedule',
                    'data': {'selected_time': selected_time}
                })
                
                # 提示用戶輸入行程標題
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="請輸入行程標題：")]
                    )
                )
            else:
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="選擇時間時發生錯誤，請重試。")]
                    )
                )
    
    elif data.get('action') == "reminder":
        # 顯示時間選擇器
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TemplateMessage(
                        alt_text="選擇時間",
                        template=ButtonsTemplate(
                            title="選擇時間",
                            text="請選擇提醒時間",
                            actions=[
                                DatetimePickerAction(
                                    label="選擇時間",
                                    data="action=add_reminder",
                                    mode="datetime"
                                )
                            ]
                        )
                    )
                ]
            )
        )
    
    elif data.get('action') == "add_reminder":
        try:
            # 檢查是否有時間參數
            if hasattr(event.postback, 'params') and event.postback.params:
                selected_time = event.postback.params.get('datetime')
                print(f"用戶選擇的提醒時間: {selected_time}")
                
                if selected_time:
                    db = Database()
                    # 設置用戶狀態為等待輸入提醒內容，並保存選擇的時間
                    db.set_user_state(user_id, {
                        'state': 'waiting_for_reminder',
                        'data': {'selected_time': selected_time}
                    })
                    
                    messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text="請輸入提醒內容：")]
                        )
                    )
                else:
                    messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text="請選擇有效的時間")]
                        )
                    )
        except Exception as e:
            print(f"設置提醒時間時出錯: {e}")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="設置提醒時間失敗，請重試")]
                )
            )

    elif data.get('action') == "view_schedule":
        db = get_db()
        schedules = db.get_today_schedules(user_id)
        
        if not schedules:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="今天沒有行程")]
                )
            )
        else:
            flex_message = create_schedule_list_flex_message(schedules)
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[flex_message]
                )
            )
    
    elif data.get('action') == "view_reminder":
        db = get_db()
        reminders = db.get_upcoming_reminders(user_id)
        
        if not reminders:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="沒有待辦提醒")]
                )
            )
        else:
            flex_message = create_reminder_list_flex_message(reminders)
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[flex_message]
                )
            )
    
    elif data.get('action') == "delete_note":
        try:
            note_id = data.get('id')
            if not note_id:
                raise ValueError("筆記 ID 不能為空")
            
            print(f"正在刪除筆記，ID: {note_id}")  # 添加日誌
            db = Database()
            if db.delete_note(note_id):
                message = TextMessage(text="筆記已成功刪除")
                
                # 重新獲取筆記列表
                notes = db.get_notes(user_id)
                if notes:
                    bubbles = [create_note_bubble(note) for note in notes]
                    message = FlexMessage(
                        alt_text="更新後的筆記列表",
                        contents=FlexCarousel(contents=bubbles)
                    )
                else:
                    message = TextMessage(text="筆記已刪除。目前沒有任何筆記。")
            else:
                message = TextMessage(text="找不到要刪除的筆記")
        except Exception as e:
            print(f"刪除筆記時出錯: {e}")
            message = TextMessage(text="刪除筆記失敗，請稍後再試")
        
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[message]
            )
        )
        
    elif data.get('action') == "delete_schedule":
        schedule_id = data.get('id')
        if not schedule_id:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="無效的行程ID")]
                )
            )
            return

        db = Database()
        if db.delete_schedule(schedule_id):
            # 同時刪除相關的 ICS 文件
            try:
                ics_file = os.path.join(os.path.dirname(__file__), 'temp', f"{schedule_id}.ics")
                if os.path.exists(ics_file):
                    os.remove(ics_file)
            except Exception as e:
                print(f"刪除 ICS 文件時出錯: {e}")

            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="行程已刪除")]
                )
            )
        else:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="刪除行程失敗，請重試")]
                )
            )
        
    elif data.get('action') == "delete_reminder":
        reminder_id = data.get('id')
        if not reminder_id:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="無效的提醒ID")]
                )
            )
            return

        db = Database()
        if db.delete_reminder(reminder_id):
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="提醒已刪除")]
                )
            )
        else:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="刪除提醒失敗，請重試")]
                )
            )
        
    elif data.get('action') == "add_to_calendar":
        schedule_id = data.get('id')
        if not schedule_id:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="無效的行程ID")]
                )
            )
            return

        db = Database()
        schedule = db.get_schedule_by_id(schedule_id)
        if not schedule:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="找不到指定的行程")]
                )
            )
            return

        try:
            # 生成 ICS 文件
            file_path = save_ics_file(schedule)
            if not file_path:
                raise Exception("生成 ICS 文件失敗")

            # 生成 Google Calendar 連結
            title = quote(schedule['title'])
            description = quote(schedule.get('description', ''))
            start_time = schedule['scheduled_time'].replace(' ', 'T')
            end_time = (datetime.strptime(schedule['scheduled_time'], '%Y-%m-%d %H:%M:%S') + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')
            
            calendar_url = (
                f"https://calendar.google.com/calendar/render?"
                f"action=TEMPLATE&text={title}&details={description}"
                f"&dates={start_time}/{end_time}"
                f"&ctz=Asia/Taipei"
            )
            
            # 生成 ICS 文件下載連結
            ics_url = f"{request.url_root.rstrip('/')}/calendar_events/{schedule_id}.ics"
            
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="請選擇要使用的日曆：\n\n" +
                                       "1. iPhone/Mac 內建日曆：\n" +
                                       f"{ics_url}\n\n" +
                                       "2. Google 日曆：\n" +
                                       f"{calendar_url}")
                    ]
                )
            )
        except Exception as e:
            print(f"生成日曆連結時出錯: {e}")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="生成日曆連結失敗，請重試")]
                )
            )
    
    elif data.get('action') == "set_remind_time":
        # 初始化數據庫連接
        db = Database()
        
        # 從用戶狀態中獲取行程信息
        user_state = db.get_user_state(user_id)
        if not user_state or 'data' not in user_state:
            return
        
        state_data = user_state['data']
        title = state_data.get('title', '')
        description = state_data.get('description', '')
        selected_time = state_data.get('selected_time', '')
        remind_minutes = int(data.get('minutes', '5'))  # 獲取用戶選擇的提醒時間
        
        if not all([title, selected_time]):
            return
        
        # 添加行程到數據庫
        print(f"添加行程: 標題={title}, 內容={description}, 時間={selected_time}, 提前{remind_minutes}分鐘提醒")
        db.add_schedule(user_id, title, description, selected_time, remind_minutes)
        
        # 清除用戶狀態
        db.clear_user_state(user_id)
        
        # 發送確認消息
        remind_text = "提前 "
        if remind_minutes >= 1440:  # 1天 = 1440分鐘
            remind_text += f"{remind_minutes // 1440} 天"
        elif remind_minutes >= 60:  # 1小時 = 60分鐘
            remind_text += f"{remind_minutes // 60} 小時"
        else:
            remind_text += f"{remind_minutes} 分鐘"
        remind_text += "提醒"
        
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=f"已為您添加行程：\n標題：{title}\n時間：{selected_time}\n{remind_text}")
                ]
            )
        )
    
    elif data.get('action') == "add_schedule":
        # 設置用戶狀態為等待輸入行程標題
        set_user_state(user_id, {"state": "waiting_for_schedule"})
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="請輸入行程標題：")]
            )
        )
        
    elif data.get('action') == "add_reminder":
        # 設置用戶狀態為等待輸入提醒內容
        set_user_state(user_id, {"state": "waiting_for_reminder"})
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="請輸入提醒內容：")]
            )
        )
    elif data.get('action') == "view_schedule":
        db = get_db()
        schedules = db.get_all_schedules()
        if schedules:
            bubbles = [create_schedule_bubble(schedule) for schedule in schedules]
            carousel = FlexCarousel(contents=bubbles)
            message = FlexMessage(
                alt_text="行程列表",
                contents=carousel
            )
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[message]
                )
            )
        else:
            message = TextMessage(text="目前沒有任何行程")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[message]
                )
            )
    elif data.get('action') == 'note':
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="請輸入要記錄的內容：")]
            )
        )
        set_user_state(user_id, "waiting_for_note")
        
    elif data.get('action') == 'schedule':
        template = ButtonsTemplate(
            title='新增行程',
            text='請選擇時間',
            actions=[
                DatetimePickerAction(
                    label='選擇時間',
                    data='schedule_time_select',
                    mode='datetime'
                )
            ]
        )
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TemplateMessage(
                    alt_text='選擇時間',
                    template=template
                )]
            )
        )
        
    elif data.get('action') == 'reminder':
        template = ButtonsTemplate(
            title='新增提醒',
            text='請選擇提醒時間',
            actions=[
                DatetimePickerAction(
                    label='選擇時間',
                    data='reminder_time_select',
                    mode='datetime'
                )
            ]
        )
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TemplateMessage(
                    alt_text='選擇提醒時間',
                    template=template
                )]
            )
        )
        
    elif data.get('action') == 'view_notes':
        try:
            print("正在獲取筆記列表...")  # 添加日誌
            db = Database()
            notes = db.get_notes(user_id)
            
            if not notes:
                print("沒有找到任何筆記")  # 添加日誌
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="目前沒有任何筆記")]
                    )
                )
                return

            print(f"找到 {len(notes)} 條筆記")  # 添加日誌
            bubbles = []
            for i, note in enumerate(notes):
                try:
                    print(f"處理第 {i+1} 條筆記: {note}")  # 添加詳細的筆記信息
                    bubble = create_note_bubble(note)
                    bubbles.append(bubble)
                except Exception as e:
                    print(f"創建筆記氣泡時出錯: {e}, note={note}")  # 添加日誌
                    continue

            if not bubbles:
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="顯示筆記列表時出錯，請稍後再試")]
                    )
                )
                return

            print(f"成功創建 {len(bubbles)} 個筆記氣泡")  # 添加日誌
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        FlexMessage(
                            alt_text="你的筆記列表",
                            contents=FlexCarousel(contents=bubbles)
                        )
                    ]
                )
            )
        except Exception as e:
            print(f"處理筆記列表時出錯: {e}")  # 添加日誌
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="獲取筆記列表失敗，請稍後再試")]
                )
            )
    
    elif data.get('action') == 'view_schedules':
        db = get_db()
        schedules = db.get_schedules(user_id)
        
        if not schedules:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="目前沒有任何行程")]
                )
            )
        else:
            bubbles = [create_schedule_bubble(schedule) for schedule in schedules]
            carousel = FlexCarousel(contents=bubbles)
            
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        FlexMessage(
                            alt_text="行程列表",
                            contents=carousel
                        )
                    ]
                )
            )
        
    elif data.get('action') == 'view_reminders':
        db = get_db()
        reminders = db.get_upcoming_reminders(user_id)
        if reminders:
            bubbles = [create_reminder_bubble(reminder) for reminder in reminders]
            carousel = FlexCarousel(contents=bubbles)
            message = FlexMessage(alt_text="提醒列表", contents=carousel)
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[message]
                )
            )
        else:
            message = TextMessage(text="目前沒有待辦的提醒事項")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[message]
                )
            )
    
    elif data.get('action') == 'schedule_time_select':
        selected_time = event.postback.params['datetime']
        set_user_state(user_id, "waiting_for_schedule", {"selected_time": selected_time})
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="請輸入行程標題：")]
            )
        )
        
    elif data.get('action') == 'reminder_time_select':
        selected_time = event.postback.params['datetime']
        set_user_state(user_id, "waiting_for_reminder", {"selected_time": selected_time})
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="請輸入提醒內容：")]
            )
        )

def create_remind_time_options():
    """創建提醒時間選項"""
    options = [
        QuickReplyItem(
            action=PostbackAction(
                label="5分鐘前",
                data="action=set_remind_time&minutes=5"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="10分鐘前",
                data="action=set_remind_time&minutes=10"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="15分鐘前",
                data="action=set_remind_time&minutes=15"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="30分鐘前",
                data="action=set_remind_time&minutes=30"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="1小時前",
                data="action=set_remind_time&minutes=60"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="2小時前",
                data="action=set_remind_time&minutes=120"
            )
        ),
        QuickReplyItem(
            action=PostbackAction(
                label="1天前",
                data="action=set_remind_time&minutes=1440"
            )
        )
    ]
    return QuickReply(items=options)

def check_schedule_keywords(text):
    """檢查文字是否包含行程相關關鍵字"""
    keywords = ['行程', '日程', '安排', '計畫', '活動', '提醒', '待辦', '今天', '明天', '下週', '下个月']
    return any(keyword in text for keyword in keywords)

def format_schedule_info(schedules):
    """格式化行程信息"""
    if not schedules:
        return "目前沒有任何行程安排喔！ 😊"
    
    result = "📅 以下是您的行程安排：\n"
    for schedule in schedules:
        result += f"\n🔸 {schedule['title']}\n"
        result += f"📝 內容：{schedule['description']}\n"
        result += f"⏰ 時間：{schedule['time']}\n"
        if schedule['remind_before']:
            result += f"⚡ 提前 {schedule['remind_before']} 分鐘提醒\n"
        result += "─────────────\n"
    return result

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """處理文字消息"""
    user_id = event.source.user_id
    text = event.message.text
    print(f"處理文字消息: user_id={user_id}, text={text}")

    # 獲取用戶當前狀態
    db = Database()
    state = db.get_user_state(user_id)
    print(f"用戶當前狀態: {state}")

    if state and state['state'] == 'waiting_for_note':
        # 添加筆記
        db.add_note(user_id, text)
        db.clear_user_state(user_id)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="筆記已保存！")]
            )
        )
    elif state and state['state'] == 'waiting_for_schedule':
        try:
            data = state.get('data', {})
            if not data.get('title'):
                # 第一步：保存標題
                data['title'] = text
                db = Database()
                db.set_user_state(user_id, {
                    'state': 'waiting_for_schedule',
                    'data': data
                })
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="請輸入行程內容：")]
                    )
                )
            elif not data.get('description'):
                # 第二步：保存內容並詢問提醒時間
                data['description'] = text
                db = Database()
                db.set_user_state(user_id, {
                    'state': 'waiting_for_schedule',
                    'data': data
                })
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="請選擇要提前多久提醒：",
                                quick_reply=create_remind_time_options()
                            )
                        ]
                    )
                )
            else:
                # 不應該到達這裡
                db = Database()
                db.clear_user_state(user_id)
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="發生錯誤，請重新開始")]
                    )
                )
        except Exception as e:
            print(f"添加行程時出錯: {e}")
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="添加行程失敗，請重試")]
                )
            )
            db = Database()
            db.clear_user_state(user_id)
    else:
        # AI 對話處理
        try:
            # 檢查是否包含行程相關關鍵字
            if check_schedule_keywords(text):
                print("檢測到行程相關關鍵字，正在查詢行程...")
                # 查詢用戶的行程
                schedules = db.get_user_schedules(user_id)
                print(f"查詢到的行程: {schedules}")
                schedule_info = format_schedule_info(schedules)
                print(f"格式化後的行程信息: {schedule_info}")
                
                # 將行程信息加入到用戶的提示中
                prompt = f"""用戶詢問行程相關信息。

目前的行程資料如下：
{schedule_info}

請根據以上資料，以專業助理的身份回答用戶的問題：{text}
如果沒有行程，可以建議用戶添加新的行程。
請使用活潑、友善的語氣回答。"""
            else:
                prompt = text

            # 獲取或創建用戶的聊天實例
            if user_id not in user_chat_history:
                user_chat_history[user_id] = get_gemini_response()
            
            # 使用用戶的聊天實例
            response = user_chat_history[user_id].send_message(prompt)
            reply_text = response.text
        except Exception as e:
            print(f"AI 回應錯誤: {str(e)}")
            if hasattr(e, 'finish_reason') and e.finish_reason == 'SAFETY':
                reply_text = "抱歉，我無法回應這個問題。請嘗試用不同的方式提問。"
            else:
                # 如果出錯，重新初始化聊天實例
                try:
                    user_chat_history[user_id] = get_gemini_response()
                    response = user_chat_history[user_id].send_message(prompt)
                    reply_text = response.text
                except:
                    reply_text = "抱歉，我現在無法正確處理這個請求。請稍後再試。"
        
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

@app.teardown_appcontext
def teardown_db(exception):
    close_db()

if __name__ == "__main__":
    init_db()  # 初始化資料庫
    reminder_handler.start()  # 啟動提醒處理器
    app.run(debug=True, use_reloader=False)  # 關閉 reloader 以避免重複啟動提醒處理器
