"""Luu tru ho so xe tren dia, co lich su phien ban.

Cau hinh nay dieu khien mot he thong an toan tren xe dang chay, nen moi lan ghi
deu tao ban luu truoc do. Khong bao gio ghi de mat du lieu cu.

    data/
      profiles/<id>/profile.yaml          <- ban dang dung
      profiles/<id>/versions/<ts>.yaml    <- lich su, moi lan luu them 1 file
      drafts/<id>.json                    <- ban nhap tu dong (chua nghiem thu)
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..domain.schemas import VehicleProfile


class ProfileNotFound(KeyError):
    pass


class ProfileLocked(PermissionError):
    """Ho so da nghiem thu va khoa - can mo khoa truoc khi sua."""


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class ProfileStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.profiles_dir = data_dir / "profiles"
        self.drafts_dir = data_dir / "drafts"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    # -- duong dan -----------------------------------------------------------
    def _dir(self, profile_id: str) -> Path:
        return self.profiles_dir / profile_id

    def _file(self, profile_id: str) -> Path:
        return self._dir(profile_id) / "profile.yaml"

    def _versions_dir(self, profile_id: str) -> Path:
        return self._dir(profile_id) / "versions"

    # -- doc -----------------------------------------------------------------
    def exists(self, profile_id: str) -> bool:
        return self._file(profile_id).is_file()

    def load(self, profile_id: str) -> VehicleProfile:
        path = self._file(profile_id)
        if not path.is_file():
            raise ProfileNotFound(profile_id)
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return VehicleProfile.model_validate(raw)

    def list_profiles(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for directory in sorted(self.profiles_dir.iterdir()):
            if not (directory / "profile.yaml").is_file():
                continue
            try:
                profile = self.load(directory.name)
            except Exception as exc:  # ho so hong khong duoc lam sap danh sach
                out.append(
                    {
                        "profile_id": directory.name,
                        "display_name": directory.name,
                        "broken": True,
                        "error": str(exc),
                    }
                )
                continue
            geometry = profile.geometry()
            out.append(
                {
                    "profile_id": profile.meta.profile_id,
                    "display_name": profile.meta.display_name or profile.meta.profile_id,
                    "plate_number": profile.meta.plate_number,
                    "vehicle_type": profile.meta.vehicle_type,
                    "commissioned": profile.meta.commissioned,
                    "updated_at": profile.meta.updated_at,
                    "total_length": round(geometry.total_length, 2),
                    "cameras_calibrated": sum(
                        1 for c in profile.cameras.values() if c.calibrated_at
                    ),
                    "broken": False,
                }
            )
        return out

    # -- ghi -----------------------------------------------------------------
    def save(self, profile: VehicleProfile, force: bool = False) -> VehicleProfile:
        profile_id = profile.meta.profile_id
        if self.exists(profile_id) and not force:
            current = self.load(profile_id)
            if current.meta.commissioned and not profile.meta.commissioned:
                pass  # cho phep mo khoa
            elif current.meta.commissioned:
                raise ProfileLocked(profile_id)

        directory = self._dir(profile_id)
        directory.mkdir(parents=True, exist_ok=True)
        self._versions_dir(profile_id).mkdir(parents=True, exist_ok=True)

        target = self._file(profile_id)
        if target.is_file():
            shutil.copy2(target, self._versions_dir(profile_id) / f"{_stamp()}.yaml")

        profile.touch()
        payload = profile.model_dump(mode="json")
        target.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
        return profile

    def delete(self, profile_id: str) -> None:
        directory = self._dir(profile_id)
        if not directory.is_dir():
            raise ProfileNotFound(profile_id)
        # Khong xoa han: doi ten thanh .deleted de con duong lui.
        directory.rename(directory.with_name(f"{profile_id}.deleted-{_stamp()}"))

    # -- lich su -------------------------------------------------------------
    def versions(self, profile_id: str) -> list[dict[str, Any]]:
        directory = self._versions_dir(profile_id)
        if not directory.is_dir():
            return []
        rows = []
        for path in sorted(directory.glob("*.yaml"), reverse=True):
            rows.append(
                {
                    "version": path.stem,
                    "size_bytes": path.stat().st_size,
                    "saved_at": datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    ).isoformat(timespec="seconds"),
                }
            )
        return rows

    def restore(self, profile_id: str, version: str) -> VehicleProfile:
        path = self._versions_dir(profile_id) / f"{version}.yaml"
        if not path.is_file():
            raise ProfileNotFound(f"{profile_id}/{version}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        profile = VehicleProfile.model_validate(raw)
        return self.save(profile, force=True)

    # -- ban nhap tu dong ----------------------------------------------------
    def save_draft(self, draft_id: str, payload: dict[str, Any]) -> None:
        safe = "".join(c for c in draft_id if c.isalnum() or c in "-_")[:64] or "unnamed"
        path = self.drafts_dir / f"{safe}.json"
        path.write_text(
            json.dumps(
                {"saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "data": payload},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def load_draft(self, draft_id: str) -> dict[str, Any] | None:
        safe = "".join(c for c in draft_id if c.isalnum() or c in "-_")[:64]
        path = self.drafts_dir / f"{safe}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def delete_draft(self, draft_id: str) -> None:
        safe = "".join(c for c in draft_id if c.isalnum() or c in "-_")[:64]
        path = self.drafts_dir / f"{safe}.json"
        path.unlink(missing_ok=True)
