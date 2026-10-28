from __future__ import annotations

import os


SERVICE_NAME = "ChinaLifeEShopAssistant"


def _keyring():
    if os.name != "nt":
        raise RuntimeError("登录密码保存仅支持 Windows 凭据管理器。")
    import keyring
    backend = keyring.get_keyring()
    if "Windows" not in type(backend).__module__:
        raise RuntimeError("当前系统未启用 Windows 凭据管理器后端，拒绝将密码保存到普通文件。")
    return keyring


def save_password(username: str, password: str) -> None:
    if not username.strip() or not password:
        raise ValueError("账号和密码不能为空。")
    _keyring().set_password(SERVICE_NAME, username.strip(), password)


def load_password(username: str) -> str | None:
    if not username.strip():
        return None
    return _keyring().get_password(SERVICE_NAME, username.strip())


def delete_password(username: str) -> None:
    if username.strip():
        try:
            _keyring().delete_password(SERVICE_NAME, username.strip())
        except Exception:
            pass
