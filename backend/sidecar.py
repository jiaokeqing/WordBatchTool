from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="文档工作台本地 API sidecar")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--data-dir", default="")
    args = parser.parse_args()

    if args.data_dir:
        os.environ["WORD_BATCH_DATA_DIR"] = str(Path(args.data_dir).resolve())

    uvicorn.run("app.main:app", host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
