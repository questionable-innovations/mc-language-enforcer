"""`python -m langenforcer_sidecar` runs the server; `... download <model>` pre-fetches weights."""
import logging
import os
import sys

import uvicorn


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if len(sys.argv) >= 3 and sys.argv[1] == "download":
        from faster_whisper import download_model

        print(download_model(sys.argv[2], cache_dir=os.environ.get("LE_MODEL_DIR") or None))
        return
    uvicorn.run("langenforcer_sidecar.app:app", host=os.environ.get("LE_HOST", "0.0.0.0"),
                port=int(os.environ.get("LE_PORT", "7860")), log_level="info")


if __name__ == "__main__":
    main()
