"""Phu thuoc dung chung cho cac router."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from ..core.settings import settings
from ..services.store import ProfileStore

_store: ProfileStore | None = None


def get_store() -> ProfileStore:
    global _store
    if _store is None:
        _store = ProfileStore(settings.data_dir)
    return _store


def require_pin(x_setup_pin: str | None = Header(default=None)) -> None:
    """Chan ghi cau hinh khi da dat ma PIN.

    Web local chay tren mang Wi-Fi cua xe. Neu khong co lop chan nao thi bat ky ai
    trong tam phu song deu sua duoc cau hinh an toan cua xe dang chay. PIN la lop
    toi thieu; ban trien khai tren xe con phai bat WPA2 va bind dung interface AP.
    """
    if not settings.setup_pin:
        return
    if x_setup_pin != settings.setup_pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ma PIN cai dat khong dung.",
        )
