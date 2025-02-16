import sqlite3

def update_database():
    conn = sqlite3.connect('line_bot.db')
    cursor = conn.cursor()
    
    # 備份原有數據
    cursor.execute("SELECT * FROM reminders")
    reminders_data = cursor.fetchall()
    
    # 重命名原有表格
    cursor.execute("ALTER TABLE reminders RENAME TO reminders_old")
    
    # 創建新表格
    cursor.execute('''
    CREATE TABLE reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id INTEGER,
        user_id TEXT,
        content TEXT,
        remind_time TEXT,
        sent INTEGER DEFAULT 0,
        reminded INTEGER DEFAULT 0,
        FOREIGN KEY (schedule_id) REFERENCES schedules (id)
    )
    ''')
    
    # 遷移數據
    for row in reminders_data:
        cursor.execute('''
        INSERT INTO reminders (id, schedule_id, user_id, content, remind_time, sent)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', row)
    
    # 刪除舊表格
    cursor.execute("DROP TABLE reminders_old")
    
    conn.commit()
    conn.close()
    print("提醒表更新完成")

if __name__ == '__main__':
    update_database()
