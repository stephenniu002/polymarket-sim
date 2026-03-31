[31/3/2026 下午3:45] No one Newton: class TailStrategy:
    def init(self):
        self.prices = []

    def update(self, price):
        self.prices.append(price)
        if len(self.prices) > 300:
            self.prices.pop(0)

    def signal(self):
        if len(self.prices) < 300:
            return False

        window = self.prices[-300:]
        last_60 = self.prices[-60:]

        low = min(window)
        current = self.prices[-1]

        distance = (current - low) / low
        rebound = (max(last_60) - low) / low

        # 👉 可调核心参数
        if distance < 0.003 and rebound > 0.006:
            return True

        return False
[31/3/2026 下午3:46] No one Newton: class Stats:
    def init(self):
        self.trades = 0
        self.wins = 0
        self.balance = 0

    def record(self, win, bet=10, multiplier=100):
        self.trades += 1

        if win:
            self.wins += 1
            self.balance += bet * multiplier
        else:
            self.balance -= bet

    def summary(self):
        if self.trades == 0:
            return {}

        return {
            "trades": self.trades,
            "win_rate": self.wins / self.trades,
            "balance": self.balance,
            "roi": self.balance / (self.trades * 10)
        }
