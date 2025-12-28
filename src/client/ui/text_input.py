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
    - 中文输入法组合态可视化（候选/组合串预览）
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
        
        # 组合输入态（IME 组字预览）
        self.composition_text: str = ""
        self.comp_start: int = 0
        self.comp_length: int = 0
        
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
        - 其他按键：输入字符（最多 64 字符）；支持中文等输入法（TEXTINPUT/TEXTEDITING）
        
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
                    # 设置输入法候选框位置
                    pygame.key.set_text_input_rect(self.rect)
                except Exception as e:
                    print(f"启动文本输入失败: {e}")
            elif (not self.active) and was_active:
                try:
                    pygame.key.stop_text_input()
                except Exception as e:
                    print(f"停止文本输入失败: {e}")
        elif event.type == pygame.KEYDOWN and self.active:
            # 只在输入框激活状态下处理键盘输入
            if event.key == pygame.K_RETURN:
                # Shift+Enter 换行；Enter 发送
                try:
                    mods = event.mod if hasattr(event, "mod") else pygame.key.get_mods()
                except Exception:
                    mods = 0
                if mods & pygame.KMOD_SHIFT:
                    # 换行（限制总长度）
                    if len(self.text) < 64:
                        self.text += "\n"
                else:
                    # Enter 键：提交输入
                    if self.on_submit and self.text.strip():
                        self.on_submit(self.text.strip())  # 触发回调
                    self.text = ""  # 清空输入框
                    # 清除组合态显示
                    self.composition_text = ""
                    self.comp_start = 0
                    self.comp_length = 0
            elif event.key == pygame.K_ESCAPE:
                # Esc 键：取消激活（放弃输入）
                was_active = self.active
                self.active = False
                if was_active:
                    try:
                        pygame.key.stop_text_input()
                    except Exception:
                        pass
                # 清除组合态
                self.composition_text = ""
                self.comp_start = 0
                self.comp_length = 0
            elif event.key == pygame.K_BACKSPACE:
                # Backspace 键：删除最后一个字符
                if self.text:
                    self.text = self.text[:-1]
            # 注意：不再在KEYDOWN中处理字符输入，避免双击问题
            # 字符输入通过TEXTINPUT事件处理，支持输入法
        elif event.type == pygame.TEXTINPUT and self.active:
            # 处理中文等输入法提交事件（已选定候选）
            if event.text:
                remaining = 64 - len(self.text)
                if remaining > 0:
                    self.text += event.text[:remaining]
            # 提交后清除组合态预览
            self.composition_text = ""
            self.comp_start = 0
            self.comp_length = 0
        elif hasattr(pygame, "TEXTEDITING") and event.type == pygame.TEXTEDITING and self.active:
            # 处理 IME 组合态（正在组字）
            try:
                self.composition_text = getattr(event, "text", "") or ""
                self.comp_start = int(getattr(event, "start", 0) or 0)
                self.comp_length = int(getattr(event, "length", 0) or 0)
            except Exception:
                self.composition_text = ""
                self.comp_start = 0
                self.comp_length = 0

    def draw(self, screen: pygame.Surface) -> None:
        """每帧渲染输入框到屏幕
        
        - 绘制背景矩形
        - 绘制边框（激活时高亮）
        - 显示输入文本或占位符
        - 若处于组合态，显示输入法预览面板
        
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

        # 更新输入法候选框位置（若可用）
        if self.active:
            try:
                pygame.key.set_text_input_rect(self.rect)
            except Exception:
                pass

        # 绘制组合态预览面板（类似输入法候选框的组字串）
        if self.active and self.composition_text:
            # 面板尺寸根据文本宽度自适应
            comp_surf = self.font.render(self.composition_text, True, (20, 20, 20))
            pad_x, pad_y = 8, 6
            panel_w = min(max(120, comp_surf.get_width() + pad_x * 2), int(self.rect.width))
            panel_h = comp_surf.get_height() + pad_y * 2
            panel_rect = pygame.Rect(self.rect.x, self.rect.bottom + 4, panel_w, panel_h)
            # 阴影
            shadow = pygame.Rect(panel_rect.x + 3, panel_rect.y + 3, panel_rect.width, panel_rect.height)
            pygame.draw.rect(screen, (190, 200, 220), shadow, border_radius=6)
            # 背景与边框
            pygame.draw.rect(screen, (245, 248, 255), panel_rect, border_radius=6)
            pygame.draw.rect(screen, (140, 170, 220), panel_rect, 2, border_radius=6)
            # 文本
            screen.blit(comp_surf, (panel_rect.x + pad_x, panel_rect.y + pad_y))
            # 选区高亮（若有）
            if self.comp_length > 0:
                prefix = self.composition_text[:self.comp_start]
                sel = self.composition_text[self.comp_start:self.comp_start + self.comp_length]
                pre_w = self.font.size(prefix)[0]
                sel_w = self.font.size(sel)[0]
                sel_rect = pygame.Rect(panel_rect.x + pad_x + pre_w, panel_rect.y + pad_y, sel_w, comp_surf.get_height())
                pygame.draw.rect(screen, (220, 235, 255), sel_rect)
                pygame.draw.rect(screen, (120, 160, 220), sel_rect, 1)
