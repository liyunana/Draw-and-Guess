import pygame
from typing import List, Tuple, Optional


class ChatPanel:
    """
    简易聊天面板：显示聊天消息，支持滚动和自适应。

    功能特性：
    - 存储并显示玩家输入的聊天内容
    - 支持消息滚动（鼠标滚轮）
    - 自动换行，文本不超出面板宽度
    - 保留最多 200 条历史消息
    - 新消息自动滚动到底部
    """

    def __init__(self, rect: pygame.Rect, font_size: int = 18, font_name: Optional[str] = None) -> None:
        """初始化聊天面板

        Args:
            rect: 聊天面板的矩形区域
            font_size: 字体大小
            font_name: 字体名称（如 "Microsoft YaHei"），默认使用 Microsoft YaHei 支持中文
        """
        self.rect = rect

        # 尝试加载指定字体，失败则使用默认的中文字体
        try:
            # 如果没有指定字体，默认使用 Microsoft YaHei（Windows 中文字体）
            if font_name is None:
                font_name = "Microsoft YaHei"
            self.font = pygame.font.SysFont(font_name, font_size)
        except Exception:
            # 如果 Microsoft YaHei 失败，尝试其他中文字体
            try:
                self.font = pygame.font.SysFont("SimHei", font_size)
            except Exception:
                # 最后的备选方案
                self.font = pygame.font.SysFont(None, font_size)

        # 消息列表：每个消息是 (用户名, 文本) 元组
        self.messages: List[Tuple[str, str]] = []  # (user, text)
        
        # 滚动参数
        self.scroll_offset = 0  # 滚动偏移量（像素）
        self.line_height = self.font.get_height() + 4  # 行高（包含间距）
        
        # 计算面板内容区域（留出边距）
        self.content_margin = 8
        self.content_width = rect.width - 2 * self.content_margin - 20  # 留20像素给滚动条

        # 颜色定义
        self.bg_color = (250, 250, 250)      # 浅灰色背景
        self.border_color = (200, 200, 200)  # 灰色边框
        self.scrollbar_color = (180, 180, 180)  # 滚动条颜色

    def resize(self, rect: pygame.Rect) -> None:
        """调整聊天框大小（窗口改变时调用）
        
        Args:
            rect: 新的矩形区域
        """
        self.rect = rect
        # 重新计算内容宽度
        self.content_width = rect.width - 2 * self.content_margin - 20
        # 重新计算滚动位置（确保不会超出范围）
        self._scroll_to_bottom()

    def add_message(self, user: str, text: str) -> None:
        """添加一条新消息到聊天面板

        Args:
            user: 发送者名字（如 "你", "对方", "系统"）
            text: 消息内容
        """
        self.messages.append((user, text))  # 添加消息到列表末尾
        # 限制历史消息数量不超过 200 条（防止内存溢出）
        if len(self.messages) > 200:
            self.messages = self.messages[-200:]
        # 新消息到达时，自动滚动到底部
        self._scroll_to_bottom()

    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """将文本按宽度换行
        
        算法：贪心算法，每行尽可能多地放入字符，直到超过最大宽度
        优点：不丢失字符，完全保留原始文本
        
        Args:
            text: 要换行的文本
            max_width: 最大宽度（像素）
            
        Returns:
            换行后的文本行列表
        """
        if not text or max_width <= 0:
            return [""]
        
        lines = []
        remaining_text = text
        
        while remaining_text:
            # 二分查找最多能放入多少个字符
            left, right = 1, len(remaining_text)
            best_length = 1
            
            while left <= right:
                mid = (left + right) // 2
                line_part = remaining_text[:mid]
                width = self.font.size(line_part)[0]
                
                if width <= max_width:
                    # 这个长度可以放入
                    best_length = mid
                    left = mid + 1
                else:
                    # 这个长度超出，需要减少
                    right = mid - 1
            
            # 获取这一行的文本
            line = remaining_text[:best_length]
            lines.append(line)
            
            # 剩余文本
            remaining_text = remaining_text[best_length:]
        
        return lines if lines else [""]

    def _get_total_height(self) -> int:
        """计算所有消息的总高度"""
        total_height = 0
        for user, text in self.messages:
            line = f"{user}: {text}"
            wrapped_lines = self._wrap_text(line, self.content_width)
            total_height += len(wrapped_lines) * self.line_height
        return total_height

    def _scroll_to_bottom(self) -> None:
        """自动滚动到底部，显示最新消息"""
        total_height = self._get_total_height()
        max_scroll = max(0, total_height - (self.rect.height - 2 * self.content_margin))
        self.scroll_offset = max_scroll

    def handle_scroll(self, delta: int) -> None:
        """处理滚动事件
        
        Args:
            delta: 滚动增量（正值向下滚，负值向上滚）
        """
        total_height = self._get_total_height()
        max_scroll = max(0, total_height - (self.rect.height - 2 * self.content_margin))
        
        # 增加或减少滚动偏移
        self.scroll_offset = max(0, min(max_scroll, self.scroll_offset - delta * 20))

    def draw(self, screen: pygame.Surface) -> None:
        """每帧渲染聊天面板到屏幕

        - 绘制圆角背景与阴影
        - 绘制边框
        - 显示所有消息（自动换行、支持滚动）
        - 绘制滚动条

        Args:
            screen: pygame 屏幕 Surface 对象
        """
        # 阴影
        shadow = pygame.Rect(self.rect.x + 3, self.rect.y + 3, self.rect.width, self.rect.height)
        pygame.draw.rect(screen, (210, 210, 210), shadow, border_radius=8)
        # 背景圆角
        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=8)
        # 边框
        pygame.draw.rect(screen, self.border_color, self.rect, 2, border_radius=8)

        # 创建裁剪区域，确保内容不超出面板
        clip_rect = pygame.Rect(
            self.rect.x + self.content_margin,
            self.rect.y + self.content_margin,
            self.rect.width - 2 * self.content_margin - 20,  # 留20像素给滚动条
            self.rect.height - 2 * self.content_margin
        )
        screen.set_clip(clip_rect)

        # 绘制消息
        y = self.rect.y + self.content_margin - self.scroll_offset
        bubble_pad_x = 10
        bubble_pad_y = 4

        for msg_idx, (user, text) in enumerate(self.messages):
            line = f"{user}: {text}"
            wrapped_lines = self._wrap_text(line, self.content_width)

            for line_idx, wrapped_line in enumerate(wrapped_lines):
                surf = self.font.render(wrapped_line, True, (40, 40, 40))
                
                # 只绘制在可见区域内的行
                if y + surf.get_height() >= self.rect.y and y <= self.rect.y + self.rect.height:
                    # 气泡背景
                    bubble_rect = pygame.Rect(
                        self.rect.x + self.content_margin,
                        y - bubble_pad_y,
                        self.content_width,
                        surf.get_height() + bubble_pad_y * 2
                    )
                    bubble_color = (245, 248, 255) if msg_idx % 2 == 0 else (252, 252, 252)
                    pygame.draw.rect(screen, bubble_color, bubble_rect, border_radius=6)
                    pygame.draw.rect(screen, (230, 230, 230), bubble_rect, 1, border_radius=6)
                    
                    # 绘制文本
                    screen.blit(surf, (self.rect.x + self.content_margin + bubble_pad_x, y))
                
                y += self.line_height

        # 取消裁剪
        screen.set_clip(None)

        # 绘制滚动条
        self._draw_scrollbar(screen)

    def _draw_scrollbar(self, screen: pygame.Surface) -> None:
        """绘制滚动条
        
        Args:
            screen: pygame 屏幕 Surface 对象
        """
        total_height = self._get_total_height()
        visible_height = self.rect.height - 2 * self.content_margin
        
        # 如果内容高度 <= 可见高度，不需要滚动条
        if total_height <= visible_height:
            return
        
        # 滚动条轨道
        scrollbar_x = self.rect.right - 12
        scrollbar_track = pygame.Rect(
            scrollbar_x,
            self.rect.y + self.content_margin,
            10,
            visible_height
        )
        pygame.draw.rect(screen, (235, 235, 235), scrollbar_track)
        
        # 滚动条拇指（滑块）
        thumb_height = max(20, visible_height * visible_height // total_height)
        thumb_y = (self.scroll_offset * visible_height // total_height)
        thumb = pygame.Rect(
            scrollbar_x,
            self.rect.y + self.content_margin + thumb_y,
            10,
            thumb_height
        )
        pygame.draw.rect(screen, self.scrollbar_color, thumb, border_radius=5)
