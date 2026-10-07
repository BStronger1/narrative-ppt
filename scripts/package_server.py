"""打包已构建的前端与 Python 源码；模型配置另存，不进入代码包。"""

import json
import tarfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backend/var/deploy"


def main():
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise SystemExit("Build frontend before packaging")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    members = [
        "backend/app",
        "backend/alembic",
        "backend/alembic.ini",
        "backend/scripts",
        "backend/pyproject.toml",
        "backend/uv.lock",
        "shared",
        "frontend/dist",
        "scripts/server_service.py",
        "README.md",
        "docs/DESIGN.md",
        "docs/DEPLOYMENT.md",
        "docs/NOTICE.md",
        "docs/UPSTREAM_README.md",
        "docs/VALIDATION.md",
        "docs/NARRATIVE_DESIGN.md",
        "docs/PAGE_COUNT_VALIDATION.md",
        "docs/GEMINI_PAGE_COUNT_VALIDATION.md",
        "docs/LONG_OUTLINE_FIX.md",
        "examples",
    ]

    def exclude_private(info):
        parts = Path(info.name).parts
        if "__pycache__" in parts or any(part.startswith(".env") for part in parts):
            return None
        return info

    with tarfile.open(OUTPUT / "app.tar.gz", "w:gz") as archive:
        for member in members:
            archive.add(ROOT / member, arcname=member, filter=exclude_private)
    environment = dotenv_values(ROOT / "backend/.env")
    model = {
        key: value
        for key, value in environment.items()
        if value
        and (key.startswith(("LLM_", "IMAGE_")) or key == "UNSPLASH_ACCESS_KEY")
    }
    if not model.get("LLM_API_KEY"):
        raise SystemExit("Configure LLM_API_KEY before deployment")
    config = OUTPUT / "model-config.json"
    config.write_text(json.dumps(model), encoding="utf-8")
    config.chmod(0o600)
    print(
        "Created code bundle and separate private model configuration in backend/var/deploy"
    )


if __name__ == "__main__":
    main()
