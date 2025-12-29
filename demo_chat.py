#!/usr/bin/env python3
"""
聊天框功能演示脚本

演示以下改进：
1. 消息不被删除
2. 自动文本换行
3. 滚轮滚动支持
4. 内容自动裁剪
"""

import sys
import importlib.util
from pathlib import Path
import io

# 设置输出编码
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 直接导入 ChatPanel
chat_path = Path(__file__).parent / "src" / "client" / "ui" / "chat.py"
spec = importlib.util.spec_from_file_location("chat", chat_path)
chat_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chat_module)
ChatPanel = chat_module.ChatPanel

import pygame


def demo_chat_panel():
    """演示聊天框功能"""
    pygame.init()
    
    # 创建窗口
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("聊天框功能演示 - 使用滚轮滚动 | 关闭窗口退出")
    
    # 创建聊天框（占据窗口大部分）
    chat_rect = pygame.Rect(50, 100, 700, 450)
    chat = ChatPanel(chat_rect, font_size=16, font_name="Microsoft YaHei")
    
    # 添加演示消息
    demo_messages = [
        ("系统", "✨ 欢迎使用改进的聊天框！"),
        ("用户A", "嗨，大家好！"),
        ("用户B", "你好呀！"),
        ("用户A", "这是一条很长很长很长的消息，用来演示自动换行功能。看看这条消息是否能正确地折行显示，而不是超出聊天框的边界。这个功能非常重要，确保用户体验良好。"),
        ("用户C", "我同意！"),
        ("系统", "🎮 游戏即将开始，请准备好"),
        ("用户A", "我准备好了"),
        ("用户B", "可以开始了"),
        ("用户C", "我也准备好了！"),
        ("系统", "⏱️  倒计时：10 秒"),
        ("用户D", "大家好！我是新玩家"),
        ("用户A", "欢迎欢迎！"),
        ("用户B", "加油！"),
        ("系统", "🎨 轮到用户A绘图"),
        ("用户A", "我要开始画画了！"),
    ]
    
    # 添加消息到聊天框
    for user, text in demo_messages:
        chat.add_message(user, text)
    
    # 添加一些额外消息来确保有足够的滚动空间
    for i in range(15):
        chat.add_message(f"用户{i % 4 + 1}", f"这是额外消息 #{i + 1}")
    
    clock = pygame.time.Clock()
    running = True
    
    print("=" * 60)
    print("聊天框功能演示")
    print("=" * 60)
    print(f"\n✅ 当前消息总数: {len(chat.messages)}")
    print("\n功能演示:")
    print("  • 消息自动保留（存储最多 200 条）")
    print("  • 长消息自动换行")
    print("  • 所有内容保持在面板内")
    print("\n控制:")
    print("  • 在聊天框上滚动鼠标滚轮查看历史消息")
    print("  • 向上滚：查看旧消息")
    print("  • 向下滚：回到最新消息")
    print("  • 关闭窗口退出演示")
    print("\n" + "=" * 60 + "\n")
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                # 检查鼠标是否在聊天框上
                if chat_rect.collidepoint(pygame.mouse.get_pos()):
                    chat.handle_scroll(event.y)
                    # 打印滚动信息
                    direction = "向下滚（查看新消息）" if event.y < 0 else "向上滚（查看旧消息）"
                    print(f"滚轮事件: {direction}, 滚动偏移: {chat.scroll_offset}px")
        
        # 绘制背景
        screen.fill((240, 240, 240))
        
        # 绘制标题
        font_title = pygame.font.SysFont("Microsoft YaHei", 24, bold=True)
        title = font_title.render("聊天框功能演示", True, (50, 50, 50))
        screen.blit(title, (50, 20))
        
        # 绘制聊天框
        chat.draw(screen)
        
        # 绘制信息面板
        font_info = pygame.font.SysFont(None, 14)
        info_texts = [
            f"消息总数: {len(chat.messages)} | 滚动位置: {chat.scroll_offset}px",
            "在聊天框上使用鼠标滚轮滚动来查看历史消息",
        ]
        for idx, text in enumerate(info_texts):
            info_surf = font_info.render(text, True, (100, 100, 100))
            screen.blit(info_surf, (50, 570 - (idx + 1) * 20))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n✅ 聊天框改进总结:")
    print("  ✓ 消息自动保留（除非超过 200 条）")
    print("  ✓ 长消息自动换行")
    print("  ✓ 内容自动裁剪到面板范围")
    print("  ✓ 支持滚轮滚动浏览历史")
    print("  ✓ 新消息自动滚动到底部")
    print("  ✓ 滚动条动态显示/隐藏")
    print("\n祝游戏愉快！🎮")


if __name__ == "__main__":
    demo_chat_panel()
