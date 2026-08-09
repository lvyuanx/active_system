from fastapi import Header


def get_current_activity_id(x_activity_id: str | None = Header(default=None)) -> str | None:
    """读取当前活动上下文，后续由权限服务校验活动访问权限。"""
    return x_activity_id

