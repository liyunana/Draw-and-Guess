from typing import Tuple
from src.client.ui.button import Button


def make_button(x: int, y: int, width: int, height: int, text: str, bg_color: Tuple[int, int, int], fg_color: Tuple[int, int, int] = (255, 255, 255), font_size: int = 18, font_name: str = "Microsoft YaHei") -> Button:
    """Create a standard styled Button for settings UI."""
    return Button(x=x, y=y, width=width, height=height, text=text, bg_color=bg_color, fg_color=fg_color, font_size=font_size, font_name=font_name)


def make_slider_rect(x: int, y: int, width: int, height: int):
    """Create a pygame.Rect to represent a slider area used in settings."""
    try:
        import pygame
    except Exception:
        raise
    return pygame.Rect(x, y, width, height)
