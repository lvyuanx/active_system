import asyncio


# 抽奖状态变更统一串行化，保证轮次、名单配置和开奖事务不会交叉执行。
lottery_operation_lock = asyncio.Lock()
