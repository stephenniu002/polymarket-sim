# trader.py 中的下单函数修改
def execute_trade(token_id, price=0.5, size=1, side="buy"):
    """
    接收动态抓取的 token_id 直接开火
    """
    if not client: return None
    try:
        order_args = client.create_order(
            price=float(price),
            size=float(size),
            side=side,
            token_id=str(token_id)
        )
        signed = client.sign_order(order_args)
        return client.place_order(signed)
    except Exception as e:
        logging.error(f"❌ 执行下单异常: {e}")
        return None
