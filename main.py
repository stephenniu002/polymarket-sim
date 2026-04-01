import random
import time
import requests
import json
from datetime import datetime, timedelta

# ================= 配置区 =================
INITIAL_BALANCE = 100000.0
BET_AMOUNT = 10.01
WIN_REWARD = 1000.0
WIN_CHANCE = 0.031

# --- Telegram 配置 ---
TG_TOKEN = "8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY"
TG_CHAT_ID = "5739995837"

# --- 时间控制 ---
DELAY = 5                       # 每轮 5 秒
REPORT_5MIN_INTERVAL = 60       # 60轮 = 5分钟
REPORT_1HOUR_INTERVAL = 720     # 720轮 = 1小时
SHADOW_THRESHOLD = 20           # 连亏 20 次触发影子模式
# ==========================================

class LobsterPro:
    def __init__(self):
        self.balance = INITIAL_BALANCE
        self.start_bal_hour = INITIAL_BALANCE
        self.consecutive_losses = 0
        self.is_shadow_mode = False
        
        self.markets = ["BTC", "ETH", "XRP", "BNB", "DOGE-YES", "SOL", "HYPE"]
        
        # 统计桶
        self.reset_stats(full=True)

    def reset_stats(self, full=False):
        self.five_min_wins = []
        if full:
            self.hour_stats = {
                "total_bets": 0,
                "wins": 0,
                "shadow_blocked": 0,
                "market_win_dist": {m: 0 for m in self.markets}, # 品种胜率分布
                "start_time": datetime.now()
            }

    def send_tg(self, text):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        try: requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except: pass

    def run_engine(self):
        round_has_win = False
        self.hour_stats["total_bets"] += len(self.markets)

        for mkt in self.markets:
            # 核心模拟逻辑：3.1% 胜率
            is_win = random.random() < WIN_CHANCE
            
            if self.is_shadow_mode:
                if is_win:
                    self.five_min_wins.append(f"{mkt}(🧪)")
                    self.hour_stats["wins"] += 1
                    self.hour_stats["market_win_dist"][mkt] += 1
                    round_has_win = True
                else:
                    self.hour_stats["shadow_blocked"] += 1
            else:
                self.balance -= BET_AMOUNT
                if is_win:
                    self.balance += WIN_REWARD
                    self.five_min_wins.append(f"{mkt}(💰)")
                    self.hour_stats["wins"] += 1
                    self.hour_stats["market_win_dist"][mkt] += 1
                    self.consecutive_losses = 0
                    round_has_win = True
                else:
                    self.consecutive_losses += 1

        # 避险状态切换
        if not self.is_shadow_mode and self.consecutive_losses >= SHADOW_THRESHOLD:
            self.is_shadow_mode = True
        if self.is_shadow_mode and round_has_win:
            self.is_shadow_mode = False
            self.consecutive_losses = 0

    def push_5min_brief(self):
        """5分钟简报：只看核心结果"""
        win_str = "、".join(self.five_min_wins) if self.five_min_wins else "暂无"
        status = "🛡️ 影子避险" if self.is_shadow_mode else "🟢 实战中"
        
        msg = (
            f"⏱ *5min 简报*\n"
            f"💰 余额: `{self.balance:.2f} U`\n"
            f"🎯 捕获: {win_str}\n"
            f"📡 状态: {status}"
        )
        self.send_tg(msg)
        self.five_min_wins = []

    def push_1hour_report(self):
        """1小时深度报告：盈亏、胜率、品种分布"""
        profit = self.balance - self.start_bal_hour
        roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        win_rate = (self.hour_stats["wins"] / (self.hour_stats["total_bets"] or 1)) * 100
        
        # 找到本小时表现最好的品种
        best_mkt = max(self.hour_stats["market_win_dist"], key=self.hour_stats["market_win_dist"].get)
        best_val = self.hour_stats["market_win_dist"][best_mkt]

        msg = (
            f"📊 *══ 小时结算清单 ══*\n"
            f"📅 周期: {self.hour_stats['start_time'].strftime('%H:%M')} - {datetime.now().strftime('%H:%M')}\n"
            f"💰 当前余额: `{self.balance:.2f} U`\n"
            f"💵 本时段盈亏: `{profit:+.2f} U`\n"
            f"📈 总计 ROI: `{roi:.4f}%`\n"
            f"🎯 统计胜率: `{win_rate:.2f}%` (预期3.1%)\n"
            f"🛡️ 影子避险: `{self.hour_stats['shadow_blocked']} 次` (省下约 {self.hour_stats['shadow_blocked']*BET_AMOUNT:.0f}U)\n"
            f"🔥 本时段最佳: `{best_mkt}` ({best_val}次WIN)\n"
            f"━━━━━━━━━━━━━━"
        )
        self.send_tg(msg)
        
        # 更新参考本金并重置统计
        self.start_bal_hour = self.balance
        self.reset_stats(full=True)

    def main_loop(self):
        print(f"🦞 龙虾 Pro 启动中...")
        self.send_tg("🚀 *龙虾 Pro 启动*\n初始本金: 100,000 U\n已开启多市场并发模拟与双级汇报系统。")
        
        step = 1
        while True:
            try:
                self.run_engine()
                
                # 5分钟汇报
                if step % REPORT_5MIN_INTERVAL == 0:
                    self.push_5min_brief()
                
                # 1小时汇总
                if step % REPORT_1HOUR_INTERVAL == 0:
                    self.push_1hour_report()
                    step = 0 # 归零防止溢出
                
                time.sleep(DELAY)
                step += 1
            except Exception as e:
                print(f"Loop Error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    bot = LobsterPro()
    bot.main_loop()
