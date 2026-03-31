class TailStrategy:
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
