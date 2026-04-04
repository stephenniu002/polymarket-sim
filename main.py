async def get_balance():
    """
    终极兼容版：自动探测 SDK 余额接口并解析多种返回格式
    """
    try:
        def _get():
            # 1. 探测 SDK 支持哪种方法名
            method_name = None
            for m in ["get_collateral_balance", "get_balance", "get_user_balance"]:
                if hasattr(client, m):
                    method_name = m
                    break
            
            if not method_name:
                raise Exception("SDK 不支持任何已知的余额接口")

            func = getattr(client, method_name)
            
            # 2. 尝试不同的调用方式 (有些版本必须传地址，有些不用)
            try:
                # 优先尝试传参调用 (Funder 模式常用)
                return func(FUNDER)
            except TypeError:
                # 如果报错参数过多，则尝试不带参数调用
                return func()

        # 在线程池中执行同步 SDK 方法，防止阻塞协程
        resp = await asyncio.to_thread(_get)

        # DEBUG 日志，帮助你在 Railway 后台看到原始数据结构
        logging.debug(f"🔍 余额接口原始返回: {resp}")

        # 3. 通用解析逻辑：适配字典返回或直接数值返回
        balance = 0.0
        if isinstance(resp, dict):
            # 尝试所有可能的 key: balance, collateral_balance, available
            val = resp.get("balance") or resp.get("collateral_balance") or resp.get("available") or 0
            balance = float(val)
        elif isinstance(resp, (int, float, str)):
            balance = float(resp)
        else:
            # 如果返回的是特殊对象，尝试读取属性
            balance = float(getattr(resp, "balance", 0))

        logging.info(f"💰 账户可用余额: {balance} USDC")
        return balance

    except Exception as e:
        logging.error(f"❌ 余额读取失败: {e}")
        return 0.0

        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
