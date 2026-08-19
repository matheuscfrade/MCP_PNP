from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    cache_dir: Path
    extrator_base: str
    max_registros: int

    @classmethod
    def from_env(cls) -> Settings:
        # Horizon/Lambda só deixa gravar em /tmp; data/ no container é read-only.
        if _hosted():
            root = Path("/tmp/pnp")
        else:
            root = Path.cwd() / "data"
        max_reg = int(os.environ.get("PNP_MAX_REGISTROS", "200"))
        if max_reg < 1:
            max_reg = 1
        if max_reg > 500:
            max_reg = 500
        return cls(
            db_path=Path(os.environ.get("PNP_DB_PATH", str(root / "pnp.sqlite"))),
            cache_dir=Path(os.environ.get("PNP_CACHE_DIR", str(root / "cache"))),
            extrator_base=os.environ.get(
                "PNP_EXTRATOR_BASE", "https://moduloextratorpnp.mec.gov.br"
            ).rstrip("/"),
            max_registros=max_reg,
        )


def _hosted() -> bool:
    return bool(
        os.environ.get("FASTMCP_CLOUD_URL")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("LAMBDA_TASK_ROOT")
    )
