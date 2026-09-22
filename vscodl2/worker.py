"""Isolated worker process. Uncaught failures reach stderr and exit nonzero."""

import json
import sys
import threading

from .core import Control, Job, download_media, scan_gallery


def main():
    request = json.loads(sys.stdin.readline())
    job = Job(**request["job"])
    control = Control()

    def commands():
        for line in sys.stdin:
            {"resume": control.resume, "stop": control.stop}[line.strip()]()

    threading.Thread(target=commands, daemon=True).start()
    emit = lambda event: print(json.dumps(event), flush=True)
    if request["operation"] == "scan":
        scan_gallery(job, emit, control)
    else:
        download_media(job, request["items"], emit, control)


if __name__ == "__main__":
    main()
