import sqlite3

def update_database():
    conn = sqlite3.connect('line_bot.db')
    cursor = conn.cursor()
    
    # 備份原有數據
    cursor.execute("SELECT * FROM schedules")
    schedules_data = cursor.fetchall()
    
    # 重命名原有表格
    cursor.execute("ALTER TABLE schedules RENAME TO schedules_old")
    
    # 創建新表格
    cursor.execute('''
    CREATE TABLE schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        title TEXT,
        description TEXT,
        scheduled_time TEXT,
        remind_before INTEGER DEFAULT 5,
        created_at TEXT,
        ics_file TEXT,
        reminded INTEGER DEFAULT 0
    )
    ''')
    
    # 遷移數據
    for row in schedules_data:
        cursor.execute('''
        INSERT INTO schedules (id, user_id, title, description, scheduled_time, remind_before, created_at, ics_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', row)
    
    # 刪除舊表格
    cursor.execute("DROP TABLE schedules_old")
    
    conn.commit()
    conn.close()
    print("數據庫更新完成")

if __name__ == '__main__':
    update_database()
