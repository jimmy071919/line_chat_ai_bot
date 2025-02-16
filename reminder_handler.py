import threading
import time
from datetime import datetime, timedelta
import pytz
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration
from linebot.v3.messaging import TextMessage, PushMessageRequest
from database import get_db, dict_factory
import os
from dotenv import load_dotenv

load_dotenv()

class ReminderHandler:
    def __init__(self):
        self.configuration = Configuration(
            access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        )
        self.messaging_api = MessagingApi(
            api_client=ApiClient(configuration=self.configuration)
        )
        self.timezone = pytz.timezone('Asia/Taipei')
        self.check_interval = 60  # 每分鐘檢查一次
        self.reminder_thread = None
        self.running = False

    def start(self):
        """啟動提醒處理器"""
        if not self.running:
            self.running = True
            self.reminder_thread = threading.Thread(target=self._reminder_loop)
            self.reminder_thread.daemon = True
            self.reminder_thread.start()

    def stop(self):
        """停止提醒處理器"""
        self.running = False
        if self.reminder_thread:
            self.reminder_thread.join()

    def _reminder_loop(self):
        """定時檢查並發送提醒的主循環"""
        while self.running:
            try:
                self._check_and_send_reminders()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"提醒處理器錯誤: {str(e)}")

    def _check_and_send_reminders(self):
        """檢查並發送提醒"""
        db = get_db()
        db.row_factory = dict_factory
        current_time = datetime.now(self.timezone)
        
        # 檢查行程
        cursor = db.execute("""
            SELECT user_id, title, scheduled_time, description, remind_before
            FROM schedules 
            WHERE reminded = 0 
            AND datetime(scheduled_time, '-' || remind_before || ' minutes') <= datetime(?)
            AND datetime(scheduled_time) >= datetime(?)
        """, (
            current_time.strftime('%Y-%m-%d %H:%M:%S'),
            current_time.strftime('%Y-%m-%d %H:%M:%S')
        ))
        schedules = cursor.fetchall()

        # 發送行程提醒
        for schedule in schedules:
            try:
                scheduled_time = datetime.strptime(schedule['scheduled_time'], '%Y-%m-%d %H:%M:%S')
                message = f"提醒：您在 {scheduled_time.strftime('%Y-%m-%d %H:%M')} 有一個行程\n標題：{schedule['title']}"
                if schedule['description']:
                    message += f"\n描述：{schedule['description']}"

                self.messaging_api.push_message(
                    PushMessageRequest(
                        to=schedule['user_id'],
                        messages=[TextMessage(text=message)]
                    )
                )

                # 更新提醒狀態
                db.execute(
                    "UPDATE schedules SET reminded = 1 WHERE user_id = ? AND scheduled_time = ?",
                    (schedule['user_id'], schedule['scheduled_time'])
                )
                db.commit()
            except Exception as e:
                print(f"發送提醒時出錯: {str(e)}")

        # 檢查提醒
        cursor = db.execute("""
            SELECT user_id, content, remind_time 
            FROM reminders 
            WHERE reminded = 0 
            AND datetime(remind_time) <= datetime(?)
            AND datetime(remind_time) >= datetime(?)
        """, (
            current_time.strftime('%Y-%m-%d %H:%M:%S'),
            current_time.strftime('%Y-%m-%d %H:%M:%S')
        ))
        reminders = cursor.fetchall()

        # 發送一般提醒
        for reminder in reminders:
            try:
                remind_time = datetime.strptime(reminder['remind_time'], '%Y-%m-%d %H:%M:%S')
                message = f"提醒：{reminder['content']}"

                self.messaging_api.push_message(
                    PushMessageRequest(
                        to=reminder['user_id'],
                        messages=[TextMessage(text=message)]
                    )
                )

                # 更新提醒狀態
                db.execute(
                    "UPDATE reminders SET reminded = 1 WHERE user_id = ? AND remind_time = ?",
                    (reminder['user_id'], reminder['remind_time'])
                )
                db.commit()
            except Exception as e:
                print(f"發送提醒時出錯: {str(e)}")

reminder_handler = ReminderHandler()
