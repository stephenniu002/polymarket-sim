try:
    yes_size, no_size = calc_size_safe(y_ask, n_ask)

    if yes_size > 0:
        await asyncio.gather(
            asyncio.to_thread(client.post_order, {
                "price": round(y_ask + 0.001, 3),
                "size": yes_size,
                "side": "BUY",
                "token_id": y
            }),
            asyncio.to_thread(client.post_order, {
                "price": round(n_ask + 0.001, 3),
                "size": no_size,
                "side": "BUY",
                "token_id": n
            })
        )

    print(f"💰 强套利 edge={edge:.4f}")  # ✅ 这一行放在 try 外面也可以
except Exception as e:
    print("❌ 强套利报错:", e)
