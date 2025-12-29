"""
测试绘画同步功能的脚本
模拟两个客户端连接，一个客户端绘画，验证另一个是否收到
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.client.network import NetworkClient
from src.shared.protocols import Message
import time
import threading

def test_draw_sync():
    """测试绘画同步"""
    print("=" * 50)
    print("绘画同步测试")
    print("=" * 50)
    
    # 创建两个客户端
    client1 = NetworkClient(host="localhost", port=5555)
    client2 = NetworkClient(host="localhost", port=5555)
    
    try:
        # 连接第一个客户端
        print("\n[客户端1] 连接到服务器...")
        ok1 = client1.connect("玩家1", "player_1", "default")
        if not ok1:
            print("[客户端1] 连接失败!")
            return False
        print("[客户端1] 连接成功!")
        
        # 连接第二个客户端
        print("[客户端2] 连接到服务器...")
        ok2 = client2.connect("玩家2", "player_2", "default")
        if not ok2:
            print("[客户端2] 连接失败!")
            return False
        print("[客户端2] 连接成功!")
        
        # 等待连接稳定
        time.sleep(1)
        
        # 客户端2清空之前的消息
        print("\n[客户端2] 清空之前的连接消息...")
        client2.drain_events()
        
        # 客户端1发送绘画动作
        print("[客户端1] 发送绘画动作...")
        draw_action = {
            "kind": "line",
            "from": (100, 100),
            "to": (200, 200),
            "color": (255, 0, 0),
            "size": 5,
            "mode": "draw"
        }
        client1.send_draw(draw_action)
        print(f"[客户端1] 已发送: {draw_action}")
        
        # 等待消息传输
        time.sleep(0.5)
        
        # 客户端2检查是否收到绘画消息
        print("\n[客户端2] 检查是否收到消息...")
        events = client2.drain_events()
        
        draw_sync_found = False
        for event in events:
            print(f"  收到消息类型: {event.type}, 数据: {event.data}")
            if event.type == "draw_sync":
                draw_sync_found = True
                data = event.data
                if data.get("by") == "player_1":
                    print(f"  ✓ 正确收到来自玩家1的绘画同步!")
                    draw_data = data.get("data", {})
                    if draw_data == draw_action:
                        print(f"  ✓ 绘画数据完全匹配!")
                        return True
                    else:
                        print(f"  ✗ 绘画数据不匹配!")
                        print(f"    期望: {draw_action}")
                        print(f"    实际: {draw_data}")
                        return False
        
        if not draw_sync_found:
            print("  ✗ 没有收到 draw_sync 消息!")
            return False
            
    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client1.close()
        client2.close()
        print("\n[完成] 已关闭连接")

if __name__ == "__main__":
    success = test_draw_sync()
    if success:
        print("\n✓ 绘画同步测试通过!")
        sys.exit(0)
    else:
        print("\n✗ 绘画同步测试失败!")
        sys.exit(1)
