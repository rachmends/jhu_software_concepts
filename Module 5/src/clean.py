"""Clean and normalize GradCafe applicant data."""

import argparse

import hashlib

import json

import os

import shutil

import subprocess

import sys

import time

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from pathlib import Path


# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "applicant_data.json"

LLM_DIR = BASE_DIR / "llm_hosting"

LLM_APP = LLM_DIR / "app.py"

OUTPUT_FILE = BASE_DIR / "llm_extend_applicant_data.json"

CHUNK_DIR = BASE_DIR / ".llm_chunks"

MANIFEST_FILE = CHUNK_DIR / "manifest.json"

DEFAULT_WORKERS = 2

PROGRESS_INTERVAL_SECONDS = 30


# ============================================================
# PUBLIC JSON FUNCTIONS
# ============================================================

def load_data(path=INPUT_FILE):
    """
    Load applicant records from a JSON file.

    Reads the specified UTF-8 JSON file and verifies that its top-level value
    is a list of applicant records.

    Args:
        path (Path): JSON file to read. By default, the raw GradCafe applicant
            dataset in ``applicant_data.json`` is used.

    Returns:
        list: Applicant records loaded from the JSON file.

    Raises:
        ValueError: If the JSON file does not contain a list.
    """

    with open(path, "r", encoding="utf-8") as file_handle:

        data = json.load(file_handle)

    if not isinstance(data, list):

        raise ValueError(
            "Expected input JSON to contain a list."
        )

    return data


def save_data(data, path=OUTPUT_FILE):
    """
    Save cleaned applicant records as formatted JSON.

    Writes the supplied records as UTF-8 JSON while preserving Unicode
    characters.

    Args:
        data (list): Cleaned applicant records to save.
        path (Path): Destination JSON file. By default, records are written
            to ``llm_extend_applicant_data.json``.
    """

    with open(path, "w", encoding="utf-8") as file_handle:

        json.dump(
            data,
            file_handle,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# PRIVATE FILE HELPERS
# ============================================================

def _write_json(data, path):

    with open(path, "w", encoding="utf-8") as file_handle:

        json.dump(
            data,
            file_handle,
            ensure_ascii=False
        )


def _load_jsonl(path):

    rows = []

    if not Path(path).exists():

        return rows

    with open(path, "r", encoding="utf-8") as file_handle:

        for line_number, line in enumerate(file_handle, start=1):

            line = line.strip()

            if not line:

                continue

            try:

                rows.append(json.loads(line))

            except json.JSONDecodeError as error:

                raise ValueError(
                    f"Invalid JSONL in {path} "
                    f"at line {line_number}."
                ) from error

    return rows


def _count_complete_jsonl(path):

    path = Path(path)

    if not path.exists():

        return 0

    count = 0

    with open(path, "r", encoding="utf-8") as file_handle:

        for line in file_handle:

            line = line.strip()

            if not line:

                continue

            try:

                json.loads(line)

            except json.JSONDecodeError:

                break

            count += 1

    return count


def _repair_jsonl(path):

    path = Path(path)

    if not path.exists():

        return 0

    valid_lines = []

    found_invalid_line = False

    with open(path, "r", encoding="utf-8") as file_handle:

        for line in file_handle:

            line = line.strip()

            if not line:

                continue

            try:

                json.loads(line)

            except json.JSONDecodeError:

                found_invalid_line = True

                break

            valid_lines.append(line)

    if found_invalid_line:

        with open(path, "w", encoding="utf-8") as file_handle:

            for line in valid_lines:

                file_handle.write(line)

                file_handle.write("\n")

    return len(valid_lines)


def _hash_input_file(path):

    digest = hashlib.sha256()

    with open(path, "rb") as file_handle:

        while True:

            block = file_handle.read(1024 * 1024)

            if not block:

                break

            digest.update(block)

    return digest.hexdigest()


# ============================================================
# PRIVATE POST-PROCESSING HELPERS
# ============================================================

def _postprocess_program(program):

    if not program:

        return program

    fixes = {

        "Ellectrical Engineering And Computer Science":
            "Electrical Engineering and Computer Science",

    }

    return fixes.get(program, program)


def _postprocess_university(university):

    if not university:

        return university

    fixes = {

        "Friedrich-Schiller Universität Jenna":
            "Friedrich-Schiller Universität Jena",

    }

    university = fixes.get(
        university,
        university
    )

    abbreviations = {

        "(Upf)": "(UPF)",

        "(Buet)": "(BUET)",

    }

    for old, new in abbreviations.items():

        university = university.replace(
            old,
            new
        )

    return university


# ============================================================
# PRIVATE RESUME / CHUNK HELPERS
# ============================================================

def _prepare_workspace(data, workers, reset=False):

    input_hash = _hash_input_file(INPUT_FILE)

    expected_manifest = {

        "input_file": str(INPUT_FILE.resolve()),

        "input_sha256": input_hash,

        "record_count": len(data),

        "workers": workers,

    }

    existing_manifest = None

    if MANIFEST_FILE.exists():

        try:

            with open(MANIFEST_FILE, "r", encoding="utf-8") as file_handle:

                existing_manifest = json.load(file_handle)

        except json.JSONDecodeError:

            existing_manifest = None

    should_reset = (
        reset
        or existing_manifest != expected_manifest
    )

    if should_reset and CHUNK_DIR.exists():

        shutil.rmtree(CHUNK_DIR)

    CHUNK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(MANIFEST_FILE, "w", encoding="utf-8") as file_handle:

        json.dump(
            expected_manifest,
            file_handle,
            indent=2
        )


def _build_jobs(data, workers):

    total = len(data)

    chunk_size = (
        total + workers - 1
    ) // workers

    jobs = []

    for chunk_number in range(workers):

        start = chunk_number * chunk_size

        end = min(
            start + chunk_size,
            total
        )

        chunk_rows = data[start:end]

        if not chunk_rows:

            continue

        input_path = (
            CHUNK_DIR
            / f"chunk_{chunk_number:02d}.json"
        )

        output_path = (
            CHUNK_DIR
            / f"chunk_{chunk_number:02d}.jsonl"
        )

        _write_json(
            chunk_rows,
            input_path
        )

        jobs.append(
            {
                "chunk_number": chunk_number,
                "rows": chunk_rows,
                "input_path": input_path,
                "output_path": output_path,
            }
        )

    return jobs


def _run_chunk(job, threads_per_worker):

    chunk_number = job["chunk_number"]

    rows = job["rows"]

    output_path = job["output_path"]

    completed = _repair_jsonl(
        output_path
    )

    expected = len(rows)

    if completed > expected:

        raise RuntimeError(
            f"Chunk {chunk_number + 1} has "
            f"{completed} output rows but only "
            f"{expected} input rows."
        )

    if completed == expected:

        return (
            chunk_number,
            completed,
            True
        )

    remaining_rows = rows[completed:]

    remaining_input = (
        CHUNK_DIR
        / f"chunk_{chunk_number:02d}_remaining.json"
    )

    _write_json(
        remaining_rows,
        remaining_input
    )

    command = [

        sys.executable,

        str(LLM_APP),

        "--file",

        str(remaining_input),

        "--out",

        str(output_path),

    ]

    if completed > 0:

        command.append(
            "--append"
        )

    environment = os.environ.copy()

    environment["N_THREADS"] = str(
        threads_per_worker
    )

    subprocess.run(
        command,
        cwd=LLM_DIR,
        env=environment,
        check=True
    )

    final_count = _repair_jsonl(
        output_path
    )

    if final_count != expected:

        raise RuntimeError(
            f"Chunk {chunk_number + 1}: "
            f"expected {expected} rows, "
            f"found {final_count}."
        )

    if remaining_input.exists():

        remaining_input.unlink()

    return (
        chunk_number,
        final_count,
        False
    )


def _completed_record_count(jobs):

    return sum(
        _count_complete_jsonl(
            job["output_path"]
        )
        for job in jobs
    )


def _merge_chunks(jobs):

    rows = []

    jobs = sorted(
        jobs,
        key=lambda job: job["chunk_number"]
    )

    for job in jobs:

        rows.extend(
            _load_jsonl(
                job["output_path"]
            )
        )

    return rows


# ============================================================
# PUBLIC CLEANING FUNCTION
# ============================================================

def _report_completed_future(future, job):
    """Report the result of a completed cleaning job."""
    chunk_number = job["chunk_number"]

    try:
        _, count, already_complete = future.result()
    except Exception:
        print(
            f"\nChunk {chunk_number + 1} failed.",
            file=sys.stderr
        )
        raise

    message = "already complete" if already_complete else "finished"

    print(
        f"Chunk {chunk_number + 1}: "
        f"{count:,} records ({message})"
    )


def _run_cleaning_jobs(
    jobs,
    workers,
    threads_per_worker,
    completed_count,
    total
):
    """Run cleaning jobs in parallel and report progress."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_job = {
            executor.submit(
                _run_chunk,
                job,
                threads_per_worker
            ): job
            for job in jobs
        }

        pending = set(future_to_job)

        while pending:
            done, pending = wait(
                pending,
                timeout=PROGRESS_INTERVAL_SECONDS,
                return_when=FIRST_COMPLETED
            )

            for future in done:
                _report_completed_future(
                    future,
                    future_to_job[future]
                )

            newly_completed = _completed_record_count(jobs)
            completed = completed_count + newly_completed
            percent = completed / total * 100

            print(
                time.strftime("%H:%M:%S"),
                f"— {completed:,} / {total:,} "
                f"({percent:.1f}%)"
            )


def _load_cleaning_state():
    """Load and validate raw and previously cleaned applicant data."""
    print("Loading applicant data...")

    data = load_data(INPUT_FILE)
    total = len(data)

    already_cleaned = (
        load_data(OUTPUT_FILE)
        if OUTPUT_FILE.exists()
        else []
    )
    completed_count = len(already_cleaned)

    if completed_count > total:
        raise ValueError(
            "Cleaned output contains more records "
            "than applicant_data.json."
        )

    for index, cleaned_record in enumerate(already_cleaned):
        if data[index].get("url") != cleaned_record.get("url"):
            raise ValueError(
                "Existing cleaned data does not match "
                f"applicant_data.json at record {index + 1}."
            )

    if total == 0:
        raise ValueError(
            "Input file contains no applicant records."
        )

    remaining_data = data[completed_count:]

    print(
        f"Already cleaned: "
        f"{completed_count:,}/{total:,}"
    )
    print(f"Remaining: {len(remaining_data):,}")

    return data, already_cleaned, completed_count, remaining_data


def clean_data(
    workers=DEFAULT_WORKERS,
    reset=False
):
    """
    Clean and enrich the scraped GradCafe applicant dataset.

    Loads records from ``applicant_data.json`` and processes records that have
    not already been cleaned. Existing cleaned output is validated against the
    beginning of the current scraped dataset so that interrupted cleaning runs
    can safely resume without misaligning records.

    Remaining records are divided into chunks and processed using the local
    LLM cleaning pipeline. Work can be distributed across multiple workers,
    and saved chunk progress can be reused on later runs. After processing,
    chunk results are merged, generated program and university fields are
    postprocessed, and the complete cleaned dataset is written to
    ``llm_extend_applicant_data.json``.

    Args:
        workers (int): Number of parallel LLM workers to use. The value is
            constrained by the number of available records and processing
            resources.
        reset (bool): If True, discard saved LLM chunk progress and restart
            cleaning from the beginning.

    Returns:
        list: Complete cleaned and enriched applicant dataset.

    Raises:
        ValueError: If the input dataset is empty, existing cleaned output is
            longer than the raw dataset, or existing cleaned records no longer
            correspond to the raw records.
        RuntimeError: If the cleaning pipeline does not produce the expected
            number of records.
    """

    data, already_cleaned, completed_count, remaining_data = (
        _load_cleaning_state()
    )

    total = len(data)

    workers = max(
        1,
        min(
            workers,
            total
        )
    )

    cpu_count = (
        os.cpu_count()
        or 2
    )

    threads_per_worker = max(
        1,
        cpu_count // workers
    )

    print(f"Applicant records: {total:,}")

    print(f"LLM workers: {workers}")

    print(
        f"CPU threads per worker: "
        f"{threads_per_worker}"
    )

    _prepare_workspace(
        remaining_data,
        workers,
        reset=reset
    )

    jobs = _build_jobs(
        remaining_data,
        workers
    )

    already_done = _completed_record_count(
        jobs
    )

    if already_done:

        percent = (
            already_done
            / total
            * 100
        )

        print(
            f"Resume progress: "
            f"{already_done:,}/{total:,} "
            f"({percent:.1f}%)"
        )

    if completed_count == total:

        print(
            "All records are already cleaned."
        )

        return already_cleaned

    print("\nRunning local LLM...")

    _run_cleaning_jobs(
        jobs,
        workers,
        threads_per_worker,
        completed_count,
        total
    )

    print("\nLoading LLM output...")

    new_rows = _merge_chunks(
        jobs
    )

    rows = (
        already_cleaned
        + new_rows
    )

    if len(rows) != total:

        raise RuntimeError(
            f"Expected {total:,} cleaned records "
            f"but found {len(rows):,}."
        )

    for row in rows:

        row["llm-generated-program"] = _postprocess_program(

            row.get(
                "llm-generated-program"
            )

        )

        row["llm-generated-university"] = _postprocess_university(

            row.get(
                "llm-generated-university"
            )

        )

    save_data(
        rows,
        OUTPUT_FILE
    )

    print(f"Cleaned records: {len(rows):,}")

    print(f"Saved to: {OUTPUT_FILE.name}")

    return rows


# ============================================================
# MAIN
# ============================================================

def main():
    """
    Run the GradCafe cleaning pipeline from the command line.

    Parses the ``--workers`` and ``--reset`` command-line options and passes
    them to :func:`clean_data`.

    ``--workers`` controls the number of parallel local LLM workers.
    ``--reset`` discards previously saved chunk progress before processing.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Clean GradCafe applicant data "
            "using the local LLM."
        )
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=(
            "Number of parallel LLM workers. "
            "Default: 2"
        )
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Discard saved LLM chunk progress "
            "and start over."
        )
    )

    args = parser.parse_args()

    clean_data(
        workers=args.workers,
        reset=args.reset
    )


if __name__ == "__main__":

    main()
## Just Checking GitHub Has Updated Code ##
