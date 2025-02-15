from rich_menu import create_rich_menu
from create_menu_image import create_rich_menu_image

def main():
    print("開始設置圖文選單...")
    
    # 1. 創建圖文選單圖片
    print("正在創建圖文選單圖片...")
    create_rich_menu_image()
    print("圖文選單圖片已創建")
    
    # 2. 創建並設置圖文選單
    print("正在設置圖文選單...")
    rich_menu_id = create_rich_menu()
    print(f"圖文選單已設置完成！ID: {rich_menu_id}")

if __name__ == "__main__":
    main()
