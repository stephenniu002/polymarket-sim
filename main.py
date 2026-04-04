# --- 3. 稳健余额审计 (全能探测版) ---
async def get_balance_safe():
    """
    探测 SDK 所有可能的余额接口，适配 0.34.x 版本的变动
    """
    methods_to_try = [
        "get_balance",            # 0.34.x 新版最可能的方法
        "get_user_balance",       # 备选
        "get_collateral_balance", # 旧版
        "get_token_balance"       # 某些内测版
    ]
    
    last_error = ""
    for method in methods_to_try:
        if hasattr(client, method):
            try:
                func = getattr(client, method)
                # 尝试带地址调用
                resp = await asyncio.to_thread(func, FUNDER)
                logging.info(f"✅ 使用 {method}(address) 获取到余额: {resp}")
                
                # 解析返回格式
                if isinstance(resp, dict):
                    return float(resp.get("balance") or resp.get("available") or 0)
                return float(resp or 0)
            except Exception as e:
                # 如果带参数失败，尝试不带参数
                try:
                    resp = await asyncio.to_thread(func)
                    logging.info(f"✅ 使用 {method}() 获取到余额: {resp}")
                    if isinstance(resp, dict):
                        return float(resp.get("balance") or 0)
                    return float(resp or 0)
                except:
                    last_error = str(e)
                    continue
                    
    logging.error(f"❌ 所有余额接口探测失败。最后报错: {last_error}")
    return 0.0

# --- 4. 下单逻辑 (保持 V15 的 post_order，这是目前最稳的) ---
async def execute_trade(token_id, title, price=0.2):
    try:
        order_args = OrderArgs(
            price=float(price),
            size=1.0,
            side="buy",
            token_id=str(token_id)
        )
        def _do_post():
            # 注意：如果 client 报错没有 create_order，
            # 那么新版可能在 client.orders.create_order
            order_func = getattr(client, "create_order", None) or getattr(client.orders, "create_order", None)
            post_func = getattr(client, "post_order", None) or getattr(client.orders, "post_order", None)
            
            signed = order_func(order_args)
            return post_func(signed, OrderType.GTC)

        res = await asyncio.to_thread(_do_post)
        return res
    except Exception as e:
        logging.error(f"❌ 下单依然报错: {e}")
        return None
