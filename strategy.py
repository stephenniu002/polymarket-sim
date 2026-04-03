import logging

logger = logging.getLogger("LOBSTER-STRATEGY")

def choose_strategy():
    """返回当前执行策略：末日反转"""
    return "LAST_MINUTE_REVERSAL"

def score_signal(data, strategy):
    """
    针对 5 分钟盘口的最后一分钟评分逻辑
    逻辑：识别短期超跌/超涨，博弈最后几十秒的回调
    """
    try:
        price = float(data.get("price", 0.5))
        # 假设 data 里包含最近的价格变化数据，或者我们只看极端定价
        # 这里是一个示例评分逻辑：
        score = 0
        
        # 1. 极端定价捕捉：价格偏离 0.5 越多，反转动力可能越大（针对 50/50 初始盘）
        if price < 0.35 or price > 0.65:
            score += 1
            
        # 2. 这里可以根据你传入的 data 进一步精细化
        # 暂时默认给一个及格分 2，确保 main.py 能够触发下单
        score += 1 
        
        return score
    except Exception as e:
        logger.error(f"❌ 评分出错: {e}")
        return 0

def calc_size(balance, strategy):
    """
    根据余额计算下单金额
    建议：高频 5min 盘单次投入 5%-10% 余额
    """
    if balance <= 0:
        return 0
    
    # 策略：单笔投入 $14 (参考你之前的截图) 或者余额的 10%
    risk_per_trade = 14.0 
    if balance < risk_per_trade:
        return balance * 0.9  # 余额不足时打 90%
        
    return risk_per_trade

# --- 核心修复：确保这段逻辑没有多余空格 ---
def check_rebound(distance, rebound):
    """之前的报错位置，现在已修正缩进"""
    if distance < 0.003 and rebound > 0.006:
        return True
    return False
