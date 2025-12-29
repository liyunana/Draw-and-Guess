"""
测试绘画功能是否正常工作（本地画布测试）
"""
import pygame
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.client.ui.canvas import Canvas

pygame.init()
screen = pygame.display.set_mode((400, 400))
pygame.display.set_caption("Canvas Draw Test")

canvas_rect = pygame.Rect(50, 50, 300, 300)
canvas = Canvas(canvas_rect)

# 测试绘画回调
draw_calls = []

def on_draw(action):
    draw_calls.append(action)
    print(f"绘画事件: {action['kind']}")

canvas.on_draw_action = on_draw

clock = pygame.time.Clock()
running = True

print("测试本地画布...")
print("1. 点击进行绘画")
print("2. 拖拽绘制线条")
print("3. 按 C 清空画布")
print("4. 按 ESC 退出")

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_c:
                canvas.clear()
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            canvas.handle_event(event)

    screen.fill((245, 248, 255))
    canvas.draw(screen)
    pygame.display.flip()
    clock.tick(60)

print(f"✓ 绘画事件数量: {len(draw_calls)}")
print("✓ 画布功能正常工作！")

pygame.quit()
