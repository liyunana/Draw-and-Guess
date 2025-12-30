import os
import pygame
from typing import Optional, Callable


class Button:
    """
    A class representing a button in the UI.

    Supports separate background (`bg_color`) and foreground/text (`fg_color`),
    and accepts an optional `font_name` (either a system font name or a path
    to a .ttf file) to improve rendering of non-ASCII characters.
    """

    def __init__(
        self,
        x,
        y,
        width,
        height,
        text,
        bg_color=(0, 0, 0),
        fg_color=(255, 255, 255),
        hover_bg_color: Optional[tuple] = None,
        font_size=24,
        font_name=None,
        click_sound: Optional[str] = None,
        on_click: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize the button with position, size, text, colors and font.
        - `bg_color`: background color (button rectangle)
        - `fg_color`: text color
        - `hover_bg_color`: background color when hovered
        - `font_name`: optional; either a system font name or path to .ttf file
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.bg_color = bg_color
        self.orig_bg_color = bg_color
        self.hover_bg_color = hover_bg_color
        self.fg_color = fg_color
        self.font_size = font_size
        # 按钮状态
        self.pressed: bool = False
        self.hovered: bool = False

        # 点击回调（可选）
        self.on_click: Optional[Callable[[], None]] = on_click

        # 可选点击音效（可以是路径字符串或已加载的 pygame.mixer.Sound）
        self.click_sound: Optional[pygame.mixer.Sound] = None
        if click_sound:
            try:
                # 初始化 mixer（如果尚未初始化）
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init()
                    except Exception:
                        # 有些环境没有可用音频设备，忽略初始化错误
                        pass

                if isinstance(click_sound, str) and os.path.exists(click_sound):
                    self.click_sound = pygame.mixer.Sound(click_sound)
                elif hasattr(click_sound, "play"):
                    # 传入了一个已加载的 Sound 对象
                    self.click_sound = click_sound  # type: ignore
            except Exception:
                # 若加载失败则静默忽略，让按钮仍然可用
                self.click_sound = None

        # Try to load the requested font. If a path is provided and exists,
        # use pygame.font.Font. Otherwise attempt pygame.font.SysFont, and
        # finally fall back to the default font.
        try:
            if font_name:
                # If provided value looks like a path, try Font()
                import os

                if os.path.exists(font_name):
                    self.font = pygame.font.Font(font_name, font_size)
                else:
                    self.font = pygame.font.SysFont(font_name, font_size)
            else:
                # No font specified, use Microsoft YaHei for Chinese support
                try:
                    self.font = pygame.font.SysFont("Microsoft YaHei", font_size)
                except Exception:
                    # Fallback to SimHei if Microsoft YaHei is not available
                    try:
                        self.font = pygame.font.SysFont("SimHei", font_size)
                    except Exception:
                        # Last resort: system default
                        self.font = pygame.font.SysFont(None, font_size)
        except Exception:
            self.font = pygame.font.Font(None, font_size)

        self.text_surface = self.font.render(text, True, self.fg_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle pygame mouse events to manage pressed state and clicks.

        - MOUSEMOTION: update hovered state
        - MOUSEBUTTONDOWN (left): set pressed True when hovered
        - MOUSEBUTTONUP (left): if was pressed and still hovered, trigger click
        """
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                # 播放音效（如果有）
                try:
                    if self.click_sound:
                        self.click_sound.play()
                except Exception:
                    pass
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed:
                was_hovered = self.rect.collidepoint(event.pos)
                self.pressed = False
                if was_hovered:
                    # 调用回调
                    if self.on_click:
                        try:
                            self.on_click()
                        except Exception:
                            pass

    def draw(self, screen):
        """Draw the button on the given screen with shadow and rounded corners."""
        # Determine current background color based on state
        current_bg = self.bg_color
        if self.hovered and self.hover_bg_color:
            current_bg = self.hover_bg_color

        # 根据是否按下绘制不同的视觉效果：按下时缩短阴影并将文本向右下偏移，边框更深，模拟凹陷
        if self.pressed:
            shadow_offset = 2
            # 按下时阴影靠内，背景颜色略微变暗
            shadow_rect = pygame.Rect(self.rect.x + shadow_offset, self.rect.y + shadow_offset, self.rect.width, self.rect.height)
            pygame.draw.rect(screen, (130, 130, 130), shadow_rect, border_radius=8)

            # 背景（略微加深）
            darker = tuple(max(0, c - 20) for c in current_bg)
            pygame.draw.rect(screen, darker, self.rect, border_radius=8)
            # 内部浅色边框模拟内凹
            inner = self.rect.inflate(-4, -4)
            pygame.draw.rect(screen, (90, 90, 90), self.rect, 2, border_radius=8)
            pygame.draw.rect(screen, (200, 200, 200), inner, 2, border_radius=6)

            # 文本下移右移一像素或两像素，营造按下效果
            pressed_text_pos = (self.text_rect.x + 2, self.text_rect.y + 2)
            screen.blit(self.text_surface, pressed_text_pos)
        else:
            # 常态：明显阴影和常规边框
            shadow_offset = 4
            shadow_rect = pygame.Rect(self.rect.x + shadow_offset, self.rect.y + shadow_offset, self.rect.width, self.rect.height)
            pygame.draw.rect(screen, (150, 150, 150), shadow_rect, border_radius=8)

            pygame.draw.rect(screen, current_bg, self.rect, border_radius=8)
            pygame.draw.rect(screen, (100, 100, 100), self.rect, 2, border_radius=8)  # 边框

            # 文本居中
            screen.blit(self.text_surface, self.text_rect)

    def is_hovered(self, mouse_pos):
        """Check if the button is hovered by the mouse."""
        return self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos, mouse_button):
        """Check if the button is clicked (left mouse button)."""
        return self.is_hovered(mouse_pos) and mouse_button == 1

    def update_text(self, new_text):
        """Update the button's text and re-render the surface."""
        self.text = new_text
        self.text_surface = self.font.render(new_text, True, self.fg_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def set_colors(self, bg_color=None, fg_color=None):
        """Update the button's background and/or foreground color."""
        if bg_color is not None:
            self.bg_color = bg_color
        if fg_color is not None:
            self.fg_color = fg_color
        self.text_surface = self.font.render(self.text, True, self.fg_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def set_position(self, x, y):
        """Update the button's position."""
        self.rect.topleft = (x, y)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def set_size(self, width, height):
        """Update the button's size."""
        self.rect.size = (width, height)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def set_font_size(self, font_size):
        """Update the button's font size and re-render the text."""
        self.font_size = font_size
        self.font = pygame.font.Font(None, font_size)
        self.text_surface = self.font.render(self.text, True, self.fg_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

