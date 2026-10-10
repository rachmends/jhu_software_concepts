import json
import sys
from pathlib import Path

import pytest
import runpy


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import clean

@pytest.mark.db
def test_load_data_reads_json_list(tmp_path):
    input_file = tmp_path / "input.json"

    input_file.write_text(
        json.dumps(
            [
                {"program": "Computer Science"},
                {"program": "Mathematics"},
            ]
        ),
        encoding="utf-8",
    )

    result = clean.load_data(input_file)

    assert result == [
        {"program": "Computer Science"},
        {"program": "Mathematics"},
    ]


@pytest.mark.db
def test_load_data_rejects_non_list_json(tmp_path):
    input_file = tmp_path / "input.json"

    input_file.write_text(
        json.dumps({"program": "Computer Science"}),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Expected input JSON to contain a list",
    ):
        clean.load_data(input_file)


@pytest.mark.db
def test_save_data_writes_json(tmp_path):
    output_file = tmp_path / "output.json"

    data = [
        {
            "program": "Computer Science",
            "university": "Johns Hopkins University",
        }
    ]

    clean.save_data(data, output_file)

    result = json.loads(
        output_file.read_text(encoding="utf-8")
    )

    assert result == data


@pytest.mark.db
def test_write_json_writes_json(tmp_path):
    output_file = tmp_path / "temporary.json"

    data = [{"url": "https://example.com/1"}]

    clean._write_json(data, output_file)

    result = json.loads(
        output_file.read_text(encoding="utf-8")
    )

    assert result == data
    
@pytest.mark.db
def test_load_jsonl_missing_file(tmp_path):
    missing_file = tmp_path / "missing.jsonl"

    assert clean._load_jsonl(missing_file) == []


@pytest.mark.db
def test_load_jsonl_reads_valid_rows_and_skips_blank_lines(tmp_path):
    jsonl_file = tmp_path / "data.jsonl"

    jsonl_file.write_text(
        '{"id": 1}\n'
        '\n'
        '{"id": 2}\n',
        encoding="utf-8",
    )

    result = clean._load_jsonl(jsonl_file)

    assert result == [
        {"id": 1},
        {"id": 2},
    ]


@pytest.mark.db
def test_load_jsonl_rejects_invalid_json(tmp_path):
    jsonl_file = tmp_path / "bad.jsonl"

    jsonl_file.write_text(
        '{"id": 1}\n'
        'not-json\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid JSONL",
    ):
        clean._load_jsonl(jsonl_file)

@pytest.mark.db
def test_count_complete_jsonl_missing_file(tmp_path):
    missing_file = tmp_path / "missing.jsonl"

    assert clean._count_complete_jsonl(missing_file) == 0


@pytest.mark.db
def test_count_complete_jsonl_stops_at_invalid_line(tmp_path):
    jsonl_file = tmp_path / "data.jsonl"

    jsonl_file.write_text(
        '{"id": 1}\n'
        '\n'
        '{"id": 2}\n'
        'incomplete-json\n'
        '{"id": 3}\n',
        encoding="utf-8",
    )

    assert clean._count_complete_jsonl(jsonl_file) == 2


@pytest.mark.db
def test_repair_jsonl_missing_file(tmp_path):
    missing_file = tmp_path / "missing.jsonl"

    assert clean._repair_jsonl(missing_file) == 0


@pytest.mark.db
def test_repair_jsonl_removes_invalid_tail(tmp_path):
    jsonl_file = tmp_path / "data.jsonl"

    jsonl_file.write_text(
        '{"id": 1}\n'
        '\n'
        '{"id": 2}\n'
        'broken-json\n'
        '{"id": 3}\n',
        encoding="utf-8",
    )

    result = clean._repair_jsonl(jsonl_file)

    assert result == 2

    assert jsonl_file.read_text(
        encoding="utf-8"
    ) == (
        '{"id": 1}\n'
        '{"id": 2}\n'
    )


@pytest.mark.db
def test_repair_jsonl_valid_file_unchanged(tmp_path):
    jsonl_file = tmp_path / "data.jsonl"

    original = (
        '{"id": 1}\n'
        '{"id": 2}\n'
    )

    jsonl_file.write_text(
        original,
        encoding="utf-8",
    )

    assert clean._repair_jsonl(jsonl_file) == 2

    assert jsonl_file.read_text(
        encoding="utf-8"
    ) == original

@pytest.mark.db
def test_hash_input_file_is_deterministic(tmp_path):
    input_file = tmp_path / "input.json"

    input_file.write_text(
        "GradCafe test data",
        encoding="utf-8",
    )

    first_hash = clean._hash_input_file(input_file)
    second_hash = clean._hash_input_file(input_file)

    assert first_hash == second_hash
    assert len(first_hash) == 64


@pytest.mark.db
def test_postprocess_program():
    assert clean._postprocess_program(None) is None

    assert clean._postprocess_program(
        "Ellectrical Engineering And Computer Science"
    ) == (
        "Electrical Engineering and Computer Science"
    )

    assert clean._postprocess_program(
        "Mathematics"
    ) == "Mathematics"


@pytest.mark.db
def test_postprocess_university():
    assert clean._postprocess_university(None) is None

    assert clean._postprocess_university(
        "Friedrich-Schiller Universität Jenna"
    ) == (
        "Friedrich-Schiller Universität Jena"
    )

    assert clean._postprocess_university(
        "Universitat Pompeu Fabra (Upf)"
    ) == (
        "Universitat Pompeu Fabra (UPF)"
    )

    assert clean._postprocess_university(
        "Bangladesh University (Buet)"
    ) == (
        "Bangladesh University (BUET)"
    )

    assert clean._postprocess_university(
        "Johns Hopkins University"
    ) == "Johns Hopkins University"
    
# ============================================================
# WORKSPACE / CHUNK HELPERS
# ============================================================


@pytest.mark.db
def test_prepare_workspace_creates_manifest(tmp_path, monkeypatch):
    input_file = tmp_path / "applicant_data.json"
    chunk_dir = tmp_path / ".llm_chunks"
    manifest_file = chunk_dir / "manifest.json"

    input_file.write_text(
        json.dumps([{"url": "one"}, {"url": "two"}]),
        encoding="utf-8",
    )

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)
    monkeypatch.setattr(clean, "MANIFEST_FILE", manifest_file)

    data = [
        {"url": "one"},
        {"url": "two"},
    ]

    clean._prepare_workspace(
        data,
        workers=2,
    )

    assert chunk_dir.exists()
    assert manifest_file.exists()

    manifest = json.loads(
        manifest_file.read_text(encoding="utf-8")
    )

    assert manifest["record_count"] == 2
    assert manifest["workers"] == 2
    assert manifest["input_file"] == str(
        input_file.resolve()
    )
    assert manifest["input_sha256"] == clean._hash_input_file(
        input_file
    )


@pytest.mark.db
def test_prepare_workspace_reuses_matching_manifest(
    tmp_path,
    monkeypatch,
):
    input_file = tmp_path / "applicant_data.json"
    chunk_dir = tmp_path / ".llm_chunks"
    manifest_file = chunk_dir / "manifest.json"

    data = [{"url": "one"}]

    input_file.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)
    monkeypatch.setattr(clean, "MANIFEST_FILE", manifest_file)

    clean._prepare_workspace(data, workers=1)

    keep_file = chunk_dir / "keep.txt"
    keep_file.write_text("keep me", encoding="utf-8")

    clean._prepare_workspace(data, workers=1)

    assert keep_file.exists()


@pytest.mark.db
def test_prepare_workspace_resets_changed_manifest(
    tmp_path,
    monkeypatch,
):
    input_file = tmp_path / "applicant_data.json"
    chunk_dir = tmp_path / ".llm_chunks"
    manifest_file = chunk_dir / "manifest.json"

    data = [{"url": "one"}]

    input_file.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)
    monkeypatch.setattr(clean, "MANIFEST_FILE", manifest_file)

    chunk_dir.mkdir()

    manifest_file.write_text(
        "{bad json",
        encoding="utf-8",
    )

    old_file = chunk_dir / "old.txt"
    old_file.write_text("old", encoding="utf-8")

    clean._prepare_workspace(
        data,
        workers=1,
    )

    assert not old_file.exists()
    assert manifest_file.exists()


@pytest.mark.db
def test_prepare_workspace_explicit_reset(
    tmp_path,
    monkeypatch,
):
    input_file = tmp_path / "applicant_data.json"
    chunk_dir = tmp_path / ".llm_chunks"
    manifest_file = chunk_dir / "manifest.json"

    data = [{"url": "one"}]

    input_file.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)
    monkeypatch.setattr(clean, "MANIFEST_FILE", manifest_file)

    clean._prepare_workspace(data, workers=1)

    old_file = chunk_dir / "old.txt"
    old_file.write_text("delete me", encoding="utf-8")

    clean._prepare_workspace(
        data,
        workers=1,
        reset=True,
    )

    assert not old_file.exists()

@pytest.mark.db
def test_build_jobs_splits_data_into_chunks(
    tmp_path,
    monkeypatch,
):
    chunk_dir = tmp_path / ".llm_chunks"
    chunk_dir.mkdir()

    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)

    data = [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]

    jobs = clean._build_jobs(
        data,
        workers=2,
    )

    assert len(jobs) == 2

    assert jobs[0]["chunk_number"] == 0
    assert jobs[0]["rows"] == [
        {"id": 1},
        {"id": 2},
    ]

    assert jobs[1]["chunk_number"] == 1
    assert jobs[1]["rows"] == [
        {"id": 3},
    ]

    assert jobs[0]["input_path"].exists()
    assert jobs[1]["input_path"].exists()


@pytest.mark.db
def test_build_jobs_skips_empty_chunks(
    tmp_path,
    monkeypatch,
):
    chunk_dir = tmp_path / ".llm_chunks"
    chunk_dir.mkdir()

    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)

    jobs = clean._build_jobs(
        [{"id": 1}],
        workers=3,
    )

    assert len(jobs) == 1
    assert jobs[0]["rows"] == [{"id": 1}]
    
@pytest.mark.db
def test_run_chunk_already_complete(
    tmp_path,
):
    output_file = tmp_path / "chunk_00.jsonl"

    output_file.write_text(
        '{"id": 1}\n'
        '{"id": 2}\n',
        encoding="utf-8",
    )

    job = {
        "chunk_number": 0,
        "rows": [
            {"id": 1},
            {"id": 2},
        ],
        "output_path": output_file,
    }

    result = clean._run_chunk(
        job,
        threads_per_worker=2,
    )

    assert result == (0, 2, True)


@pytest.mark.db
def test_run_chunk_rejects_too_many_output_rows(
    tmp_path,
):
    output_file = tmp_path / "chunk_00.jsonl"

    output_file.write_text(
        '{"id": 1}\n'
        '{"id": 2}\n',
        encoding="utf-8",
    )

    job = {
        "chunk_number": 0,
        "rows": [{"id": 1}],
        "output_path": output_file,
    }

    with pytest.raises(
        RuntimeError,
        match="output rows",
    ):
        clean._run_chunk(
            job,
            threads_per_worker=2,
        )
        
@pytest.mark.db
def test_run_chunk_processes_remaining_rows(
    tmp_path,
    monkeypatch,
):
    chunk_dir = tmp_path / ".llm_chunks"
    chunk_dir.mkdir()

    llm_dir = tmp_path / "llm_hosting"
    llm_dir.mkdir()

    llm_app = llm_dir / "app.py"
    llm_app.write_text(
        "# fake LLM",
        encoding="utf-8",
    )

    output_file = chunk_dir / "chunk_00.jsonl"

    output_file.write_text(
        '{"id": 1}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)
    monkeypatch.setattr(clean, "LLM_DIR", llm_dir)
    monkeypatch.setattr(clean, "LLM_APP", llm_app)

    job = {
        "chunk_number": 0,
        "rows": [
            {"id": 1},
            {"id": 2},
        ],
        "output_path": output_file,
    }

    def fake_subprocess_run(
        command,
        cwd,
        env,
        check,
    ):
        assert "--append" in command
        assert env["N_THREADS"] == "4"

        with output_file.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write('{"id": 2}\n')

    monkeypatch.setattr(
        clean.subprocess,
        "run",
        fake_subprocess_run,
    )

    result = clean._run_chunk(
        job,
        threads_per_worker=4,
    )

    assert result == (0, 2, False)

    remaining_file = (
        chunk_dir
        / "chunk_00_remaining.json"
    )

    assert not remaining_file.exists()

@pytest.mark.db
def test_run_chunk_new_chunk_does_not_append(
    tmp_path,
    monkeypatch,
):
    chunk_dir = tmp_path / ".llm_chunks"
    chunk_dir.mkdir()

    llm_dir = tmp_path / "llm_hosting"
    llm_dir.mkdir()

    llm_app = llm_dir / "app.py"
    llm_app.write_text(
        "# fake LLM",
        encoding="utf-8",
    )

    output_file = chunk_dir / "chunk_00.jsonl"

    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)
    monkeypatch.setattr(clean, "LLM_DIR", llm_dir)
    monkeypatch.setattr(clean, "LLM_APP", llm_app)

    job = {
        "chunk_number": 0,
        "rows": [{"id": 1}],
        "output_path": output_file,
    }

    def fake_subprocess_run(
        command,
        cwd,
        env,
        check,
    ):
        assert "--append" not in command

        output_file.write_text(
            '{"id": 1}\n',
            encoding="utf-8",
        )

    monkeypatch.setattr(
        clean.subprocess,
        "run",
        fake_subprocess_run,
    )

    result = clean._run_chunk(
        job,
        threads_per_worker=2,
    )

    assert result == (0, 1, False)

@pytest.mark.db
def test_run_chunk_rejects_incomplete_final_output(
    tmp_path,
    monkeypatch,
):
    chunk_dir = tmp_path / ".llm_chunks"
    chunk_dir.mkdir()

    llm_dir = tmp_path / "llm_hosting"
    llm_dir.mkdir()

    llm_app = llm_dir / "app.py"
    llm_app.write_text(
        "# fake LLM",
        encoding="utf-8",
    )

    output_file = chunk_dir / "chunk_00.jsonl"

    monkeypatch.setattr(clean, "CHUNK_DIR", chunk_dir)
    monkeypatch.setattr(clean, "LLM_DIR", llm_dir)
    monkeypatch.setattr(clean, "LLM_APP", llm_app)

    job = {
        "chunk_number": 0,
        "rows": [
            {"id": 1},
            {"id": 2},
        ],
        "output_path": output_file,
    }

    monkeypatch.setattr(
        clean.subprocess,
        "run",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(
        RuntimeError,
        match="expected 2 rows",
    ):
        clean._run_chunk(
            job,
            threads_per_worker=2,
        )

@pytest.mark.db
def test_completed_record_count(
    tmp_path,
):
    first = tmp_path / "chunk_00.jsonl"
    second = tmp_path / "chunk_01.jsonl"

    first.write_text(
        '{"id": 1}\n'
        '{"id": 2}\n',
        encoding="utf-8",
    )

    second.write_text(
        '{"id": 3}\n',
        encoding="utf-8",
    )

    jobs = [
        {"output_path": first},
        {"output_path": second},
    ]

    assert clean._completed_record_count(jobs) == 3


@pytest.mark.db
def test_merge_chunks_preserves_chunk_order(
    tmp_path,
):
    first = tmp_path / "chunk_00.jsonl"
    second = tmp_path / "chunk_01.jsonl"

    first.write_text(
        '{"id": 1}\n',
        encoding="utf-8",
    )

    second.write_text(
        '{"id": 2}\n',
        encoding="utf-8",
    )

    # Deliberately reversed to prove _merge_chunks sorts them.
    jobs = [
        {
            "chunk_number": 1,
            "output_path": second,
        },
        {
            "chunk_number": 0,
            "output_path": first,
        },
    ]

    result = clean._merge_chunks(jobs)

    assert result == [
        {"id": 1},
        {"id": 2},
    ]

# ============================================================
# clean_data()
# ============================================================


@pytest.mark.db
def test_clean_data_empty_input(monkeypatch, tmp_path):
    input_file = tmp_path / "applicant_data.json"
    output_file = tmp_path / "llm_extend_applicant_data.json"

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "OUTPUT_FILE", output_file)

    monkeypatch.setattr(
        clean,
        "load_data",
        lambda path: [],
    )

    with pytest.raises(
        ValueError,
        match="Input file contains no applicant records",
    ):
        clean.clean_data()


@pytest.mark.db
def test_clean_data_rejects_output_larger_than_input(
    monkeypatch,
    tmp_path,
):
    input_file = tmp_path / "applicant_data.json"
    output_file = tmp_path / "llm_extend_applicant_data.json"

    input_file.write_text("[]", encoding="utf-8")
    output_file.write_text("[]", encoding="utf-8")

    raw_data = [
        {"url": "one"},
    ]

    cleaned_data = [
        {"url": "one"},
        {"url": "two"},
    ]

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "OUTPUT_FILE", output_file)

    def fake_load(path):
        if path == input_file:
            return raw_data

        return cleaned_data

    monkeypatch.setattr(
        clean,
        "load_data",
        fake_load,
    )

    with pytest.raises(
        ValueError,
        match="more records",
    ):
        clean.clean_data()


@pytest.mark.db
def test_clean_data_rejects_mismatched_existing_output(
    monkeypatch,
    tmp_path,
):
    input_file = tmp_path / "applicant_data.json"
    output_file = tmp_path / "llm_extend_applicant_data.json"

    input_file.write_text("[]", encoding="utf-8")
    output_file.write_text("[]", encoding="utf-8")

    raw_data = [
        {"url": "raw-url"},
        {"url": "second-url"},
    ]

    cleaned_data = [
        {"url": "different-url"},
    ]

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "OUTPUT_FILE", output_file)

    def fake_load(path):
        if path == input_file:
            return raw_data

        return cleaned_data

    monkeypatch.setattr(
        clean,
        "load_data",
        fake_load,
    )

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        clean.clean_data()

@pytest.mark.db
def test_clean_data_all_records_already_cleaned(
    monkeypatch,
    tmp_path,
    capsys,
):
    input_file = tmp_path / "applicant_data.json"
    output_file = tmp_path / "llm_extend_applicant_data.json"

    input_file.write_text("[]", encoding="utf-8")
    output_file.write_text("[]", encoding="utf-8")

    data = [
        {"url": "one"},
        {"url": "two"},
    ]

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "OUTPUT_FILE", output_file)

    monkeypatch.setattr(
        clean,
        "load_data",
        lambda path: data,
    )

    monkeypatch.setattr(
        clean,
        "_prepare_workspace",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        clean,
        "_build_jobs",
        lambda *args, **kwargs: [],
    )

    monkeypatch.setattr(
        clean,
        "_completed_record_count",
        lambda jobs: 0,
    )

    result = clean.clean_data(workers=5)

    assert result == data

    output = capsys.readouterr().out

    assert "Already cleaned: 2/2" in output
    assert "Remaining: 0" in output
    assert "All records are already cleaned." in output
    
class FakeFuture:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    def result(self):
        if self._error is not None:
            raise self._error

        return self._result


class FakeExecutor:
    future = None

    def __init__(self, max_workers):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False

    def submit(self, function, job, threads):
        return self.future

@pytest.mark.db
def test_clean_data_successful_processing(
    monkeypatch,
    tmp_path,
    capsys,
):
    input_file = tmp_path / "applicant_data.json"
    output_file = tmp_path / "llm_extend_applicant_data.json"

    input_file.write_text("[]", encoding="utf-8")

    raw_data = [
        {
            "url": "one",
            "program": "Raw Program 1",
        },
        {
            "url": "two",
            "program": "Raw Program 2",
        },
    ]

    cleaned_rows = [
        {
            "url": "one",
            "llm-generated-program":
                "Ellectrical Engineering And Computer Science",
            "llm-generated-university":
                "Friedrich-Schiller Universität Jenna",
        },
        {
            "url": "two",
            "llm-generated-program": "Mathematics",
            "llm-generated-university":
                "Universitat Pompeu Fabra (Upf)",
        },
    ]

    jobs = [
        {
            "chunk_number": 0,
            "rows": raw_data,
            "output_path": tmp_path / "chunk.jsonl",
        }
    ]

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "OUTPUT_FILE", output_file)

    monkeypatch.setattr(
        clean,
        "load_data",
        lambda path: raw_data,
    )

    monkeypatch.setattr(
        clean,
        "_prepare_workspace",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        clean,
        "_build_jobs",
        lambda *args, **kwargs: jobs,
    )

    counts = iter([1, 2])

    monkeypatch.setattr(
        clean,
        "_completed_record_count",
        lambda jobs: next(counts),
    )

    monkeypatch.setattr(
        clean,
        "_merge_chunks",
        lambda jobs: cleaned_rows,
    )

    monkeypatch.setattr(
        clean.os,
        "cpu_count",
        lambda: 4,
    )

    saved = {}

    def fake_save_data(data, path):
        saved["data"] = data
        saved["path"] = path

    monkeypatch.setattr(
        clean,
        "save_data",
        fake_save_data,
    )

    FakeExecutor.future = FakeFuture(
        result=(0, 2, False)
    )

    monkeypatch.setattr(
        clean,
        "ThreadPoolExecutor",
        FakeExecutor,
    )

    monkeypatch.setattr(
        clean,
        "wait",
        lambda pending, timeout, return_when: (
            set(pending),
            set(),
        ),
    )

    result = clean.clean_data(workers=1)

    assert len(result) == 2

    assert result[0]["llm-generated-program"] == (
        "Electrical Engineering and Computer Science"
    )

    assert result[0]["llm-generated-university"] == (
        "Friedrich-Schiller Universität Jena"
    )

    assert result[1]["llm-generated-program"] == (
        "Mathematics"
    )

    assert result[1]["llm-generated-university"] == (
        "Universitat Pompeu Fabra (UPF)"
    )

    assert saved["data"] == result
    assert saved["path"] == output_file

    output = capsys.readouterr().out

    assert "Resume progress:" in output
    assert "Running local LLM" in output
    assert "finished" in output
    assert "Loading LLM output" in output
    assert "Cleaned records: 2" in output
    
@pytest.mark.db
def test_clean_data_future_already_complete(
    monkeypatch,
    tmp_path,
    capsys,
):
    input_file = tmp_path / "applicant_data.json"
    output_file = tmp_path / "llm_extend_applicant_data.json"

    input_file.write_text("[]", encoding="utf-8")

    raw_data = [
        {"url": "one"},
    ]

    cleaned_rows = [
        {
            "url": "one",
            "llm-generated-program": "Mathematics",
            "llm-generated-university":
                "Johns Hopkins University",
        }
    ]

    jobs = [
        {
            "chunk_number": 0,
            "rows": raw_data,
            "output_path": tmp_path / "chunk.jsonl",
        }
    ]

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)
    monkeypatch.setattr(clean, "OUTPUT_FILE", output_file)

    monkeypatch.setattr(
        clean,
        "load_data",
        lambda path: raw_data,
    )

    monkeypatch.setattr(
        clean,
        "_prepare_workspace",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        clean,
        "_build_jobs",
        lambda *args, **kwargs: jobs,
    )

    monkeypatch.setattr(
        clean,
        "_completed_record_count",
        lambda jobs: 1,
    )

    monkeypatch.setattr(
        clean,
        "_merge_chunks",
        lambda jobs: cleaned_rows,
    )

    monkeypatch.setattr(
        clean,
        "save_data",
        lambda *args, **kwargs: None,
    )

    FakeExecutor.future = FakeFuture(
        result=(0, 1, True)
    )

    monkeypatch.setattr(
        clean,
        "ThreadPoolExecutor",
        FakeExecutor,
    )

    monkeypatch.setattr(
        clean,
        "wait",
        lambda pending, timeout, return_when: (
            set(pending),
            set(),
        ),
    )

    result = clean.clean_data()

    assert result == cleaned_rows

    output = capsys.readouterr().out
    assert "already complete" in output

@pytest.mark.db
def test_clean_data_worker_failure(
    monkeypatch,
    tmp_path,
    capsys,
):
    input_file = tmp_path / "applicant_data.json"

    input_file.write_text("[]", encoding="utf-8")

    raw_data = [
        {"url": "one"},
    ]

    jobs = [
        {
            "chunk_number": 0,
            "rows": raw_data,
            "output_path": tmp_path / "chunk.jsonl",
        }
    ]

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)

    monkeypatch.setattr(
        clean,
        "load_data",
        lambda path: raw_data,
    )

    monkeypatch.setattr(
        clean,
        "_prepare_workspace",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        clean,
        "_build_jobs",
        lambda *args, **kwargs: jobs,
    )

    monkeypatch.setattr(
        clean,
        "_completed_record_count",
        lambda jobs: 0,
    )

    FakeExecutor.future = FakeFuture(
        error=RuntimeError("fake worker failure")
    )

    monkeypatch.setattr(
        clean,
        "ThreadPoolExecutor",
        FakeExecutor,
    )

    monkeypatch.setattr(
        clean,
        "wait",
        lambda pending, timeout, return_when: (
            set(pending),
            set(),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="fake worker failure",
    ):
        clean.clean_data()

    captured = capsys.readouterr()

    assert "Chunk 1 failed." in captured.err

@pytest.mark.db
def test_clean_data_rejects_wrong_merged_count(
    monkeypatch,
    tmp_path,
):
    input_file = tmp_path / "applicant_data.json"

    input_file.write_text("[]", encoding="utf-8")

    raw_data = [
        {"url": "one"},
        {"url": "two"},
    ]

    jobs = [
        {
            "chunk_number": 0,
            "rows": raw_data,
            "output_path": tmp_path / "chunk.jsonl",
        }
    ]

    monkeypatch.setattr(clean, "INPUT_FILE", input_file)

    monkeypatch.setattr(
        clean,
        "load_data",
        lambda path: raw_data,
    )

    monkeypatch.setattr(
        clean,
        "_prepare_workspace",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        clean,
        "_build_jobs",
        lambda *args, **kwargs: jobs,
    )

    monkeypatch.setattr(
        clean,
        "_completed_record_count",
        lambda jobs: 0,
    )

    monkeypatch.setattr(
        clean,
        "_merge_chunks",
        lambda jobs: [{"url": "one"}],
    )

    FakeExecutor.future = FakeFuture(
        result=(0, 1, False)
    )

    monkeypatch.setattr(
        clean,
        "ThreadPoolExecutor",
        FakeExecutor,
    )

    monkeypatch.setattr(
        clean,
        "wait",
        lambda pending, timeout, return_when: (
            set(pending),
            set(),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Expected 2 cleaned records",
    ):
        clean.clean_data()

@pytest.mark.db
def test_main_parses_arguments(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clean.py",
            "--workers",
            "3",
            "--reset",
        ],
    )

    received = {}

    def fake_clean_data(workers, reset):
        received["workers"] = workers
        received["reset"] = reset

    monkeypatch.setattr(
        clean,
        "clean_data",
        fake_clean_data,
    )

    clean.main()

    assert received == {
        "workers": 3,
        "reset": True,
    }

@pytest.mark.db
def test_clean_script_entry_point(
    monkeypatch,
):
    def fake_parse_args(self):
        raise SystemExit

    monkeypatch.setattr(
        "argparse.ArgumentParser.parse_args",
        fake_parse_args,
    )

    with pytest.raises(SystemExit):
        runpy.run_path(
            str(SRC_DIR / "clean.py"),
            run_name="__main__",
        )

