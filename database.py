import sqlite3
import json
import threading
from datetime import datetime, timedelta

DATABASE = 'line_bot.db'
thread_local = threading.local()

def dict_factory(cursor, row):
    """將資料庫查詢結果轉換為字典格式"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    """獲取資料庫連接"""
    if not hasattr(thread_local, "db"):
        thread_local.db = sqlite3.connect(DATABASE)
        thread_local.db.row_factory = dict_factory
    return thread_local.db

def close_db():
    """關閉資料庫連接"""
    if hasattr(thread_local, "db"):
        thread_local.db.close()
        del thread_local.db

def init_db():
    """初始化資料庫表"""
    with sqlite3.connect(DATABASE) as db:
        db.row_factory = dict_factory
        
        # 創建筆記表
        db.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME NOT NULL
        )
        ''')
        
        # 創建行程表
        db.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            scheduled_time DATETIME NOT NULL,
            created_at DATETIME NOT NULL
        )
        ''')
        
        # 創建提醒表
        db.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            reminder_time DATETIME NOT NULL,
            created_at DATETIME NOT NULL,
            reminded INTEGER DEFAULT 0
        )
        ''')
        
        # 創建用戶狀態表
        db.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            data TEXT
        )
        ''')
        
        db.commit()

class Database:
    def __init__(self):
        self.db = sqlite3.connect(DATABASE)
        self.db.row_factory = dict_factory
    
    def get_user_state(self, user_id):
        """獲取用戶狀態"""
        cursor = self.db.execute('SELECT * FROM user_states WHERE user_id = ?', (user_id,))
        state = cursor.fetchone()
        if state and state['data']:
            state['data'] = json.loads(state['data'])
        return state

    def set_user_state(self, user_id, state_data):
        """設置用戶狀態"""
        if isinstance(state_data.get('data'), dict):
            state_data['data'] = json.dumps(state_data['data'])
        
        self.db.execute('''
            INSERT OR REPLACE INTO user_states (user_id, state, data)
            VALUES (?, ?, ?)
        ''', (user_id, state_data.get('state'), state_data.get('data')))
        self.db.commit()

    def clear_user_state(self, user_id):
        """清除用戶狀態"""
        self.db.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
        self.db.commit()

    def add_schedule(self, user_id, title, description, scheduled_time):
        """添加行程
        Args:
            user_id (str): 用戶ID
            title (str): 行程標題
            description (str): 行程描述
            scheduled_time (str): 行程時間，格式為 YYYY-MM-DD HH:MM:SS
        Returns:
            bool: 是否成功添加
        """
        try:
            cursor = self.db.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 將 scheduled_time 轉換為正確的格式
            if 'T' in scheduled_time:
                # 處理 ISO 格式的時間 (YYYY-MM-DDTHH:MM)
                scheduled_time = scheduled_time.replace('T', ' ') + ':00'
            
            cursor.execute(
                "INSERT INTO schedules (user_id, title, description, scheduled_time, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, title, description, scheduled_time, now)
            )
            self.db.commit()
            return True
        except Exception as e:
            print(f"添加行程時出錯: {e}")
            return False

    def add_reminder(self, user_id, content, reminder_time):
        """添加提醒"""
        self.db.execute('''
            INSERT INTO reminders (user_id, content, reminder_time)
            VALUES (?, ?, ?)
        ''', (user_id, content, reminder_time))
        self.db.commit()

    def add_note(self, user_id, content):
        """添加筆記"""
        try:
            cursor = self.db.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO notes (user_id, content, created_at) VALUES (?, ?, ?)",
                (user_id, content, now)
            )
            self.db.commit()
            return True
        except Exception as e:
            print(f"添加筆記時出錯: {e}")
            return False

    def get_schedules(self, user_id):
        """獲取用戶的所有行程
        Args:
            user_id (str): 用戶ID
        Returns:
            list: 行程列表
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT * FROM schedules WHERE user_id = ? ORDER BY scheduled_time ASC",
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"獲取行程時出錯: {e}")
            return []

    def get_reminders(self, user_id):
        """獲取用戶的所有提醒"""
        cursor = self.db.execute('SELECT * FROM reminders WHERE user_id = ? ORDER BY reminder_time', (user_id,))
        return cursor.fetchall()

    def get_notes(self, user_id):
        """獲取用戶的所有筆記"""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id, user_id, content, created_at FROM notes WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return cursor.fetchall()

    def get_upcoming_reminders(self, user_id):
        """獲取用戶即將到來的提醒"""
        cursor = self.db.execute('''
            SELECT * FROM reminders 
            WHERE user_id = ? 
            AND datetime(reminder_time) >= datetime(?)
            ORDER BY reminder_time
        ''', (user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return cursor.fetchall()

    def get_today_schedules(self, user_id):
        """獲取用戶今天的行程"""
        today = datetime.now().date()
        today_start = today.strftime('%Y-%m-%d 00:00:00')
        today_end = today.strftime('%Y-%m-%d 23:59:59')
        
        cursor = self.db.execute('''
            SELECT * FROM schedules 
            WHERE user_id = ? 
            AND datetime(scheduled_time) >= datetime(?)
            AND datetime(scheduled_time) <= datetime(?)
            ORDER BY scheduled_time
        ''', (user_id, today_start, today_end))
        return cursor.fetchall()

    def get_schedule_by_id(self, schedule_id):
        """根據ID獲取行程
        Args:
            schedule_id (str): 行程ID
        Returns:
            dict: 行程信息，如果不存在則返回 None
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT * FROM schedules WHERE id = ?",
                (schedule_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"根據ID獲取行程時出錯: {e}")
            return None

    def delete_note(self, note_id):
        """刪除筆記"""
        try:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"刪除筆記時出錯: {e}")
            return False

    def delete_reminder(self, reminder_id):
        """刪除提醒"""
        self.db.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
        self.db.commit()

    def delete_schedule(self, schedule_id):
        """刪除行程"""
        self.db.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
        self.db.commit()

    def close(self):
        """關閉資料庫連接"""
        self.db.close()
