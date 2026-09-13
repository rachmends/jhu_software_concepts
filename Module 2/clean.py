import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "applicant_data.json"

LLM_DIR = BASE_DIR / "llm_hosting"
LLM_APP = LLM_DIR / "app.py"

LLM_JSONL = BASE_DIR / "applicant_data_llm.jsonl"
OUTPUT_FILE = BASE_DIR / "llm_extend_applicant_data.json"


def save_data(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_local_llm():
    command = [
        sys.executable,
        str(LLM_APP),
        "--file",
        str(INPUT_FILE),
        "--out",
        str(LLM_JSONL),
    ]

    subprocess.run(
        command,
        cwd=LLM_DIR,
        check=True,
    )


def load_jsonl(path):
    rows = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                rows.append(json.loads(line))

    return rows


def postprocess_program(program):
    if not program:
        return program

    fixes = {
        "Ellectrical Engineering And Computer Science":
            "Electrical Engineering and Computer Science",
    }

    return fixes.get(program, program)


def postprocess_university(university):
    if not university:
        return university

    fixes = {
        "Friedrich-Schiller Universität Jenna":
            "Friedrich-Schiller Universität Jena",
    }

    university = fixes.get(university, university)

    abbreviations = {
        "(Upf)": "(UPF)",
        "(Buet)": "(BUET)",
    }

    for old, new in abbreviations.items():
        university = university.replace(old, new)

    return university


def clean_data():
    print("Running local LLM ...")

    run_local_llm()

    print("Loading LLM output...")

    rows = load_jsonl(LLM_JSONL)

    for row in rows:
        row["llm-generated-program"] = postprocess_program(
            row.get("llm-generated-program")
        )

        row["llm-generated-university"] = postprocess_university(
            row.get("llm-generated-university")
        )

    save_data(rows, OUTPUT_FILE)

    print(f"Cleaned records: {len(rows):,}")
    print(f"Saved to: {OUTPUT_FILE.name}")


def main():
    clean_data()


if __name__ == "__main__":
    main()