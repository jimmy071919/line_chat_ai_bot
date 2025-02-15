from PIL import Image, ImageDraw, ImageFont
import os

def create_rich_menu_image():
    # 創建一個新的圖片
    width = 2500
    height = 1686
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # 定義按鈕區域
    button_width = width // 3
    button_height = height // 2
    
    # 繪製網格線
    for i in range(1, 3):
        # 垂直線
        draw.line([(i * button_width, 0), (i * button_width, height)], fill='black', width=2)
    # 水平線
    draw.line([(0, button_height), (width, button_height)], fill='black', width=2)
    
    # 定義按鈕文字
    buttons = [
        ['記事', '行程', '提醒'],
        ['查看記事', '查看行程', '查看提醒']
    ]
    
    # 嘗試多個可能的字體
    possible_fonts = [
        "msjh.ttc",  # 微軟正黑體
        "mingliu.ttc",  # 細明體
        "simsun.ttc",  # 新細明體
        "msgothic.ttc",  # MS Gothic
        "arial.ttf",
        "MEIRYO.TTC"  # 日文字體（通常也支援中文）
    ]
    
    font = None
    font_size = 60
    
    # 嘗試載入字體
    for font_name in possible_fonts:
        try:
            # 嘗試從 Windows 字體目錄載入
            font_path = os.path.join(os.environ['SYSTEMROOT'], 'Fonts', font_name)
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
                print(f"使用字體: {font_name}")
                break
        except Exception as e:
            print(f"無法載入字體 {font_name}: {str(e)}")
    
    if font is None:
        print("無法載入任何字體，使用預設字體")
        font = ImageFont.load_default()
        font_size = 30  # 預設字體較小，調整大小
    
    # 繪製按鈕文字
    for row in range(2):
        for col in range(3):
            text = buttons[row][col]
            # 計算文字位置使其居中
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = col * button_width + (button_width - text_width) // 2
            y = row * button_height + (button_height - text_height) // 2
            
            # 繪製文字背景（可選）
            padding = 20
            draw.rectangle([
                x - padding,
                y - padding,
                x + text_width + padding,
                y + text_height + padding
            ], fill='lightgray')
            
            # 繪製文字
            draw.text((x, y), text, fill='black', font=font)
            print(f"已繪製文字: {text} 在位置 ({x}, {y})")
    
    # 保存圖片
    image.save('rich_menu_image.png')
    print("圖片已保存為 rich_menu_image.png")

if __name__ == "__main__":
    create_rich_menu_image()
