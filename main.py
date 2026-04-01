import random
import time
import json
import os
import requests
from datetime import datetime
import matplotlib.pyplot as plt

# ================= 配置区 =================
LOG_FILE = "lobster_history.json"
INITIAL_BALANCE = 100000.0
BET_AMOUNT = 10.01
WIN_REWARD = 1000.0
WIN_CHANCE = 0.031

# --- Telegram 配置 ---
TG_TOKEN = "8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY"      # 找 @BotFather 获取
TG_CHAT_ID = "5739995837"     # 找 @userinfobot 获取
ENABLE_TG = True               # 是否开启通知

# 风控开关
SHADOW_THRESHOLD = 20
# ==========================================

class LobsterBot:
    def __init__(self):
        self.balance = INITIAL_BALANCE
        self.total_roi = 0.0
        self.consecutive_losses = 0
        self.is_shadow_mode = False
        self.history = []
        self.markets = ["BTC", "ETH", "XRP", "BNB", "DOGE-YES", "SOL", "HYPE"]

    def send_tg_msg(self, text):
        """发送电报通知"""
        if not ENABLE_TG: return
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"❌ TG 发送失败: {e}")

    def run_round(self):
        timestamp = datetime.now().strftime("%H:%M:%S")
        round_wins = []
        round_win_count = 0

        # --- 风险状态检查 ---
        if not self.is_shadow_mode and self.consecutive_losses >= SHADOW_THRESHOLD:
            self.is_shadow_mode = True
            msg = f"⚠️ *风险预警*\n当前已连续亏损 {self.consecutive_losses} 次！\n🛡️ 系统已切入【影子模式】避险。"
            self.send_tg_msg(msg)

        # --- 执行下注 ---
        for mkt in self.markets:
            is_win = random.random() < WIN_CHANCE
            
            if self.is_shadow_mode:
                if is_win: 
                    round_win_count += 1
                    round_wins.append(f"{mkt}(SIM)")
            else:
                self.balance -= BET_AMOUNT
                if is_win:
                    self.balance += WIN_REWARD
                    round_win_count += 1
                    round_wins.append(mkt)
                    self.consecutive_losses = 0
                else:
                    self.consecutive_losses += 1

        # --- 影子模式恢复逻辑 ---
        if self.is_shadow_mode and round_win_count > 0:
            self.is_shadow_mode = False
            self.consecutive_losses = 0
            msg = f"✨ *信号回归*\n模拟环境捕获到 WIN: {', '.join(round_wins)}\n💰 系统恢复实战下注！"
            self.send_tg_msg(msg)

        # --- 实时盈利推送 (只在实战盈利时推) ---
        if not self.is_shadow_mode and round_win_count > 0:
            msg = f"💰 *盈利报表*\n时间: {timestamp}\n品种: {', '.join(round_wins)}\n当前余额: {self.balance:.2f}U\nROI: {self.total_roi:.4f}%"
            self.send_tg_msg(msg)

        # 记录数据
        self.total_roi = ((self.balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
        self.history.append({
            "time": timestamp,
            "balance": round(self.balance, 2),
            "roi": round(self.total_roi, 4),
            "mode": "Shadow" if self.is_shadow_mode else "Real"
        })
        self.save_history()

    def save_history(self):
        with open(LOG_FILE, "w") as f:
            json.dump(self.history, f, indent=2)

    def load_history(self):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                self.history = json.load(f)
                if self.history:
                    self.balance = self.history[-1]["balance"]
                    self.total_roi = self.history[-1]["roi"]
                    print(f"📥 已加载历史，余额: {self.balance}")

    def start_simulation(self, rounds=100, delay=1):
        self.load_history()
        self.send_tg_msg("🚀 *龙虾 Bot 启动*\n策略: 影子模式+尾部反转模拟\n初始本金: 100,000 U")
        
        try:
            for i in range(rounds):
                self.run_round()
                # 每 60 轮（约1小时）发一次心跳包报表
                if (i + 1) % 60 == 0:
                    self.send_tg_msg(f"📊 *整点盘点*\n当前余额: {self.balance:.2f}U\nROI: {self.total_roi:.4f}%")
                time.sleep(delay)
        except KeyboardInterrupt:
            self.send_tg_msg("🛑 程序被手动停止。")
        finally:
            print("模拟结束，生成图表中...")

# ================= 主程序 =================
if __name__ == "__main__":
    bot = LobsterBot()
    # 模拟 200 轮
    bot.start_simulation(rounds=200, delay=0.5)
