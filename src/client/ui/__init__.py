"""
用户界面模块

提供基础 UI 组件以支撑“你画我猜”的客户端表现层：
- 画布 Canvas：本地绘图与同步到服务器
- 聊天缓冲 ChatBuffer：收发聊天记录并渲染
- HUD 渲染器 HudRenderer：记分板/计时器/房间状态展示

该模块与 Pygame 紧耦合用于渲染，但不负责网络逻辑；
网络交互由 `src.client.game.ClientGame` 提供，通过回调进行联动。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import pygame


@dataclass
class Stroke:
	"""一条绘图笔划（由多个点组成）"""

	color: Tuple[int, int, int]
	size: int
	points: List[Tuple[int, int]] = field(default_factory=list)
	is_active: bool = True


class Canvas:
	"""画布组件：处理本地绘图并通过回调同步到服务器"""

	def __init__(self, width: int, height: int, sync_cb: Optional[Callable[[Dict[str, Any]], None]] = None):
		self.width = width
		self.height = height
		self._strokes: List[Stroke] = []
		self._current: Optional[Stroke] = None
		# // 同步回调：将绘图事件发送给网络层（ClientGame.send_draw）
		self._sync_cb = sync_cb

	# 绘图流程
	def begin_stroke(self, color: Tuple[int, int, int], size: int, pos: Tuple[int, int]) -> None:
		# // 开始一条笔划：记录首点并发起同步
		self._current = Stroke(color=color, size=max(1, int(size)))
		self._current.points.append((int(pos[0]), int(pos[1])))
		if self._sync_cb:
			self._sync_cb({"kind": "begin", "color": list(color), "size": size, "point": [pos[0], pos[1]]})

	def add_point(self, pos: Tuple[int, int]) -> None:
		# // 增加中间点：实时同步给其他客户端
		if not self._current:
			return
		p = (int(pos[0]), int(pos[1]))
		self._current.points.append(p)
		if self._sync_cb:
			self._sync_cb({"kind": "point", "point": [p[0], p[1]]})

	def end_stroke(self) -> None:
		# // 结束笔划：存档并通知同步结束
		if not self._current:
			return
		self._current.is_active = False
		self._strokes.append(self._current)
		if self._sync_cb:
			self._sync_cb({"kind": "end"})
		self._current = None

	def clear(self) -> None:
		# // 清空本地画布（不强制同步，由上层决定是否广播）
		self._strokes.clear()
		self._current = None

	# 渲染
	def render(self, surface: pygame.Surface) -> None:
		# // 逐笔划绘制到传入的表面上
		for s in self._strokes:
			self._draw_stroke(surface, s)
		# // 当前笔划也绘制，避免拖尾
		if self._current:
			self._draw_stroke(surface, self._current)

	def _draw_stroke(self, surface: pygame.Surface, stroke: Stroke) -> None:
		pts = stroke.points
		n = len(pts)
		if n == 0:
			return
		if n == 1:
			pygame.draw.circle(surface, stroke.color, pts[0], max(1, stroke.size // 2))
			return
		# // 使用相邻点连线近似笔划
		for i in range(1, n):
			pygame.draw.line(surface, stroke.color, pts[i - 1], pts[i], stroke.size)


class ChatBuffer:
	"""聊天缓冲：记录消息并负责渲染"""

	def __init__(self, capacity: int = 50, font: Optional[pygame.font.Font] = None):
		self.capacity = max(10, capacity)
		self._messages: List[Tuple[str, str, float]] = []  # (by, text, ts)
		self._font = font or pygame.font.SysFont(None, 18)

	def add(self, by: str, text: str) -> None:
		# // 追加消息并按容量裁剪
		self._messages.append((by, text, time.time()))
		if len(self._messages) > self.capacity:
			overflow = len(self._messages) - self.capacity
			del self._messages[:overflow]

	def render(self, surface: pygame.Surface, rect: pygame.Rect, fg=(20, 20, 20)) -> None:
		# // 将消息逐行绘制到指定矩形区域内
		x, y = rect.left + 6, rect.top + 6
		line_h = self._font.get_linesize() + 4
		max_lines = max(1, rect.height // line_h)
		# // 只渲染末尾若干行
		for by, text, _ in self._messages[-max_lines:]:
			msg = f"{by}: {text}"
			surf = self._font.render(msg, True, fg)
			surface.blit(surf, (x, y))
			y += line_h


class HudRenderer:
	"""HUD 渲染器：记分板与计时器"""

	def __init__(self, title_font: Optional[pygame.font.Font] = None, item_font: Optional[pygame.font.Font] = None):
		self._title_font = title_font or pygame.font.SysFont(None, 24)
		self._item_font = item_font or pygame.font.SysFont(None, 20)

	def render(self, surface: pygame.Surface, room_state: Dict[str, Any], rect: pygame.Rect) -> None:
		# // 标题与基本信息
		title = f"Room: {room_state.get('room_id', '-') }"
		round_idx = int(room_state.get("round_index", 0) or 0)
		drawer = room_state.get("drawer_id")
		time_left = int(room_state.get("time_left", 0) or 0)

		# // 渲染房间标题
		surf_title = self._title_font.render(title, True, (10, 10, 10))
		surface.blit(surf_title, (rect.left + 6, rect.top + 6))

		# // 渲染回合与计时
		meta = f"Round {round_idx}  Drawer: {drawer or '-'}  Time: {time_left}s"
		surf_meta = self._item_font.render(meta, True, (30, 30, 30))
		surface.blit(surf_meta, (rect.left + 6, rect.top + 6 + self._title_font.get_linesize() + 4))

		# // 记分板
		y = rect.top + 6 + self._title_font.get_linesize() + self._item_font.get_linesize() + 10
		players: Dict[str, Dict[str, Any]] = room_state.get("players", {}) or {}
		for pid, p in players.items():
			line = f"{p.get('name', pid)}: {int(p.get('score', 0))}"
			surf_line = self._item_font.render(line, True, (40, 40, 40))
			surface.blit(surf_line, (rect.left + 6, y))
			y += self._item_font.get_linesize() + 3


__all__ = [
	"Stroke",
	"Canvas",
	"ChatBuffer",
	"HudRenderer",
]

