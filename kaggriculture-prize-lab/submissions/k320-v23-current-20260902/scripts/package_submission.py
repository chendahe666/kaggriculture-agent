#!/usr/bin/env python3
"""Create and verify the minimal compliant Kaggle submission archive."""

import argparse
import gzip
import io
import tarfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPOSITORY_ROOT / "main.py"
LICENSE = REPOSITORY_ROOT / "LICENSES" / "Apache-2.0.txt"
NOTICE = REPOSITORY_ROOT / "THIRD_PARTY_NOTICES.md"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "dist" / "submission.tar.gz"
SUBMISSION_FILES = (
    (SOURCE, "main.py"),
    (LICENSE, "LICENSE-APACHE-2.0.txt"),
    (NOTICE, "THIRD_PARTY_NOTICES.txt"),
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    return parser.parse_args()


def create_submission(source, output):
    """Build a byte-reproducible archive without host identity metadata."""
    if not source.is_file():
        raise FileNotFoundError(source)

    source_bytes = source.read_bytes()
    compile(source_bytes.decode("utf-8"), str(source), "exec")
    submission_files = (
        (source, "main.py"),
        (LICENSE, "LICENSE-APACHE-2.0.txt"),
        (NOTICE, "THIRD_PARTY_NOTICES.txt"),
    )
    for path, _ in submission_files:
        if not path.is_file():
            raise FileNotFoundError(path)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw_archive:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw_archive,
            compresslevel=9,
            mtime=0,
        ) as compressed_archive:
            with tarfile.open(
                mode="w",
                fileobj=compressed_archive,
                format=tarfile.USTAR_FORMAT,
            ) as archive:
                for path, archive_name in submission_files:
                    payload = path.read_bytes()
                    member = tarfile.TarInfo(archive_name)
                    member.size = len(payload)
                    member.mode = 0o644
                    member.mtime = 0
                    member.uid = 0
                    member.gid = 0
                    member.uname = ""
                    member.gname = ""
                    archive.addfile(member, io.BytesIO(payload))

    with tarfile.open(output, "r:gz") as archive:
        members = archive.getmembers()
    expected_names = [archive_name for _, archive_name in submission_files]
    if [member.name for member in members] != expected_names or not all(
        member.isfile() for member in members
    ):
        raise RuntimeError(
            f"unexpected archive members: {[member.name for member in members]}"
        )

    size = output.stat().st_size
    if size > 100 * 1024 * 1024:
        raise RuntimeError(f"submission exceeds 100 MiB: {size} bytes")
    return size


def main():
    args = parse_args()
    output = args.output if args.output.is_absolute() else Path.cwd() / args.output
    size = create_submission(SOURCE, output)
    print(
        f"{output} ({size} bytes): "
        + ", ".join(archive_name for _, archive_name in SUBMISSION_FILES)
    )


if __name__ == "__main__":
    main()
