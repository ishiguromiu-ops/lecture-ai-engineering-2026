import csv

from app.experiment_recorder import ExperimentMeasurement, ExperimentRecorder


def _measurement(**changes):
    values = {
        "status": "success",
        "model": "test-model",
        "temperature": "0.2",
        "history_mode": "ON",
        "history_turns": 1,
        "turn_number": 1,
        "question": "質問, 1行目\n2行目",
        "answer": "回答\n続き",
        "input_tokens": 10,
        "output_tokens": 5,
        "thoughts_tokens": 0,
        "total_tokens": 15,
        "api_response_seconds": 1.234,
        "executed_at": "2026-10-24T09:00:00+00:00",
        "error_code": None,
    }
    values.update(changes)
    return ExperimentMeasurement(**values)


def test_recorder_writes_complete_csv_and_readable_text(tmp_path):
    recorder = ExperimentRecorder.start("test-model", "0.2", tmp_path)
    recorder.record(
        _measurement(
            input_tokens=None,
            output_tokens=0,
            thoughts_tokens=None,
            total_tokens=15,
        )
    )
    recorder.record(
        _measurement(
            status="error",
            turn_number=2,
            answer=None,
            input_tokens=None,
            output_tokens=None,
            thoughts_tokens=None,
            total_tokens=None,
            error_code=429,
        )
    )
    recorder.close()

    with recorder.csv_path.open(encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 2
    assert rows[0]["experiment_id"] == recorder.experiment_id
    assert rows[0]["status"] == "success"
    assert rows[0]["question"] == "質問, 1行目\n2行目"
    assert rows[0]["answer"] == "回答\n続き"
    assert rows[0]["input_tokens"] == ""
    assert rows[0]["output_tokens"] == "0"
    assert rows[0]["thoughts_tokens"] == ""
    assert rows[0]["total_tokens"] == "15"
    assert rows[0]["api_response_seconds"] == "1.234"
    assert rows[1]["status"] == "error"
    assert rows[1]["turn_number"] == "2"
    assert rows[1]["answer"] == ""
    assert rows[1]["error_code"] == "429"

    text = recorder.txt_path.read_text(encoding="utf-8")
    assert recorder.experiment_id in text
    assert "質問, 1行目\n2行目" in text
    assert "回答:\n回答\n続き" in text
    assert "思考トークン数: 不明" in text
    assert "出力トークン数: 0" in text
    assert "エラーコード: 429" in text


def test_new_recording_creates_distinct_files(tmp_path):
    first = ExperimentRecorder.start("test-model", "default", tmp_path)
    first.close()
    second = ExperimentRecorder.start("test-model", "default", tmp_path)
    second.close()

    assert first.experiment_id != second.experiment_id
    assert first.csv_path != second.csv_path
    assert first.txt_path != second.txt_path
    assert first.csv_path.exists()
    assert first.txt_path.exists()
    assert second.csv_path.exists()
    assert second.txt_path.exists()
    assert set(tmp_path.glob("*.csv")) == {first.csv_path, second.csv_path}
    assert set(tmp_path.glob("*.txt")) == {first.txt_path, second.txt_path}
