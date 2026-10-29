from __future__ import annotations

import os


SERVICE_NAME = "ChinaLifeEShopAssistant"


def _keyring():
    if os.name != "nt":
        raise RuntimeError("凭据保存仅支持 Windows 凭据管理器。")
    import keyring
    backend = keyring.get_keyring()
    if "Windows" not in type(backend).__module__:
        raise RuntimeError("当前系统未启用 Windows 凭据管理器后端，拒绝将秘密保存到普通文件。")
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


def save_secret(account: str, secret: str) -> None:
    if not account.strip() or not secret:
        raise ValueError("秘密名称和内容不能为空。")
    _keyring().set_password(SERVICE_NAME, "secret:" + account.strip(), secret)


def load_secret(account: str) -> str | None:
    if not account.strip():
        return None
    return _keyring().get_password(SERVICE_NAME, "secret:" + account.strip())
