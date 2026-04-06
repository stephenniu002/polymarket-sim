from web3 import Web3
from web3.middleware import geth_poa_middleware  # 👈 必须导入这个

RPCS = [
    "https://rpc.ankr.com/polygon",
    "https://polygon.llamarpc.com",
    "https://polygon.publicnode.com"
]

def get_w3():
    for rpc in RPCS:
        try:
            # 增加 User-Agent 伪装，防止被部分 RPC 节点拦截
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={
                "timeout": 5,
                "headers": {'User-Agent': 'Mozilla/5.0'}
            }))
            
            if w3.is_connected():
                # ✅ 关键修正：注入 PoA 中间件
                # 解决报错: The field extraData is 97 bytes, but expected 32.
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                # 打印一下当前胜出的 RPC，方便排查延迟
                # logger.info(f"🔗 已连接至 RPC: {rpc.split('/')[2]}") 
                return w3
        except:
            continue
    raise Exception("❌ 所有 RPC 连接失败，请检查网络或 Railway 出站限制")
