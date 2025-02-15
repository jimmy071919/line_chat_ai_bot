from linebot.models import (
    RichMenu, RichMenuArea, RichMenuBounds, RichMenuSize,
    PostbackAction, MessageAction, URIAction
)
from linebot import LineBotApi
import os
from dotenv import load_dotenv

load_dotenv()
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))

def create_rich_menu():
    # 創建圖文選單
    rich_menu_to_create = RichMenu(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,
        name="Nice rich menu",
        chat_bar_text="點擊開啟選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                action=PostbackAction(label='記事', data='action=note')
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                action=PostbackAction(label='行程', data='action=schedule')
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1666, y=0, width=833, height=843),
                action=PostbackAction(label='提醒', data='action=reminder')
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
                action=PostbackAction(label='查看記事', data='action=view_notes')
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=843, width=833, height=843),
                action=PostbackAction(label='查看行程', data='action=view_schedules')
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1666, y=843, width=833, height=843),
                action=PostbackAction(label='查看提醒', data='action=view_reminders')
            )
        ]
    )
    
    # 創建圖文選單
    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu_to_create)
    
    # 上傳圖文選單圖片
    with open("rich_menu_image.png", 'rb') as f:
        line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)
    
    # 將圖文選單設為預設
    line_bot_api.set_default_rich_menu(rich_menu_id)
    
    return rich_menu_id
