import pygame
from typing import Callable, Optional, Tuple


class TextInput:
    """
    简易文本输入框：用于猜词或聊天输入。

    功能特性：
    - 点击激活；Enter 提交内容；Esc 取消激活；Backspace 删除字符
    - 支持输入长度限制（最多 64 字符）
    - 占位符提示（输入框为空时显示）
    - `on_submit` 回调在提交时触发，用于处理提交事件
    """

    def __init__(
        self,
        rect: pygame.Rect,
        font_name: Optional[str] = None,
        font_size: int = 22,
        text_color: Tuple[int, int, int] = (0, 0, 0),
        bg_color: Tuple[int, int, int] = (240, 240, 240),
        placeholder: str = "输入猜词...",
    ) -> None:
        """初始化文本输入框
        
        Args:
            rect: 输入框的矩形区域
            font_name: 字体名称（如 "Microsoft YaHei"），默认系统字体
            font_size: 字体大小
            text_color: 文字颜色
            bg_color: 背景颜色
            placeholder: 占位符文本（输入框为空时显示）
        """
        self.rect = rect
        self.text = ""  # 当前输入的文本
        self.placeholder = placeholder  # 占位符
        self.text_color = text_color
        self.bg_color = bg_color
        self.active = False  # 是否激活（获得焦点）
        
        # 尝试加载指定字体，失败则使用默认字体
        try:
            if font_name:
                self.font = pygame.font.SysFont(font_name, font_size)
            else:
                self.font = pygame.font.SysFont(None, font_size)
        except Exception:
            self.font = pygame.font.SysFont(None, font_size)
        
        # 提交回调函数：在用户按 Enter 提交时触发
        # 回调参数为提交的文本内容
        self.on_submit: Optional[Callable[[str], None]] = None

    def handle_event(self, event: pygame.event.Event) -> None:
        """处理键盘和鼠标事件
        
        事件说明：
        - 鼠标点击：激活或取消激活输入框
        - Enter 键：提交输入内容（触发 on_submit 回调），然后清空
        - Esc 键：取消激活（放弃输入）
        - Backspace：删除最后一个字符
        - 其他按键：输入字符（最多 64 字符）；支持中文等输入法（TEXTINPUT）
        
        Args:
            event: pygame 事件对象
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 鼠标点击：检查是否点击了输入框区域
            was_active = self.active
            self.active = self.rect.collidepoint(event.pos)
            # 根据激活状态开启/关闭文本输入（支持中文输入法）
            if self.active and not was_active:
                try:
                    pygame.key.start_text_input()
                except Exception:
                    pass
            elif (not self.active) and was_active:
                try:
                    pygame.key.stop_text_input()
                except Exception:
                    pass
        elif event.type == pygame.KEYDOWN and self.active:
            # 只在输入框激活状态下处理键盘输入
            if event.key == pygame.K_RETURN:
                # Enter 键：提交输入
                if self.on_submit and self.text.strip():
                    self.on_submit(self.text.strip())  # 触发回调，传入去空格的文本
                self.text = ""  # 清空输入框
            elif event.key == pygame.K_ESCAPE:
                # Esc 键：取消激活（放弃输入）
                was_active = self.active
                self.active = False
                if was_active:
                    try:
                        pygame.key.stop_text_input()
                    except Exception:
                        pass
            elif event.key == pygame.K_BACKSPACE:
                # Backspace 键：删除最后一个字符
                self.text = self.text[:-1]
            else:
                # 其他按键：输入字符（限制长度为 64）
                if event.unicode and len(self.text) < 64:
                    self.text += event.unicode  # 只接受可打印字符
        elif event.type == pygame.TEXTINPUT and self.active:
            # 处理中文等输入法文本事件
            if event.text:
                remaining = 64 - len(self.text)
                if remaining > 0:
                    self.text += event.text[:remaining]

    def draw(self, screen: pygame.Surface) -> None:
        """每帧渲染输入框到屏幕
        
        - 绘制背景矩形
        - 绘制边框（激活时高亮）
        - 显示输入文本或占位符
        
        Args:
            screen: pygame 屏幕 Surface 对象
        """
        # 阴影
        shadow = pygame.Rect(self.rect.x + 3, self.rect.y + 3, self.rect.width, self.rect.height)
        pygame.draw.rect(screen, (200, 200, 200), shadow, border_radius=6)
        # 绘制背景矩形（圆角）
        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=6)
        # 绘制边框（激活时蓝色高亮）
        border_color = (80, 120, 200) if self.active else (180, 180, 180)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=6)
        
        # 决定显示的文本：若有输入或激活则显示输入内容，否则显示占位符
        txt = self.text if (self.text or self.active) else self.placeholder
        # 决定文字颜色：有输入或激活时黑色，占位符时浅灰色
        color = self.text_color if self.text or self.active else (130, 130, 130)
        # 渲染文本
        surf = self.font.render(txt, True, color)
        # 绘制在输入框内（左边距 8 像素，垂直居中）
        screen.blit(surf, (self.rect.x + 8, self.rect.y + (self.rect.height - surf.get_height()) // 2))
