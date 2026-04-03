import time
import requests
from config import TELEGRAM_TOKEN, CHAT_ID

class Reporter:
    def init(self):
        self.start_balance = 1000
        self.last_balance = 1000
        self.current_balance = 1000

        self.trades = []
        self.last_5m = time.time()
        self.last_1h = time.time()

    def update_balance(self, balance):
        self.current_balance = balance

    def record_trade(self, token, pnl, strategy):
        self.trades.append({
            "token": token,
            "pnl": pnl,
            "strategy": strategy,
            "time": time.time()
        })

    def send(self, msg):
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

    # 🟢 5分钟报告
    def report_5m(self):
        now = time.time()

        if now - self.last_5m < 300:
            return

        recent = [t for t in self.trades if now - t["time"] < 300]

        pnl = sum(t["pnl"] for t in recent)

        msg = f"""
📊 5分钟报告
------------------
交易数: {len(recent)}
收益: {pnl:.2f}
余额: {self.current_balance:.2f}
变化: {self.current_balance - self.last_balance:.2f}
"""

        self.send(msg)

        self.last_balance = self.current_balance
        self.last_5m = now

    # 🟣 1小时报告
    def report_1h(self):
        now = time.time()

        if now - self.last_1h < 3600:
            return

        total_pnl = self.current_balance - self.start_balance

        # 胜率
        wins = len([t for t in self.trades if t["pnl"] > 0])
        total = len(self.trades)
        winrate = wins / total if total > 0 else 0

        # 最赚钱策略
        strat_pnl = {}
        for t in self.trades:
            strat_pnl.setdefault(t["strategy"], 0)
            strat_pnl[t["strategy"]] += t["pnl"]

        best_strat = max(strat_pnl, key=strat_pnl.get) if strat_pnl else "N/A"

        msg = f"""
🕐 1小时总结
------------------
总收益: {total_pnl:.2f}
当前余额: {self.current_balance:.2f}
胜率: {winrate:.2%}
最佳策略: {best_strat}
总交易数: {total}
"""

        self.send(msg)

        self.last_1h = now
