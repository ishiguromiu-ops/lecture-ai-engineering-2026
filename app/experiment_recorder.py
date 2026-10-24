"""CSV/TXT 記録をユーザーデータ領域へ保存する。"""

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO
from uuid import uuid4

DEFAULT_OUTPUT_DIR = Path.home() / ".local" / "share" / "aie-experiments"
CSV_FIELDS = (
    "experiment_id",
    "status",
    "model",
    "temperature",
    "history_mode",
    "history_turns",
    "turn_number",
    "question",
    "answer",
    "input_tokens",
    "output_tokens",
    "thoughts_tokens",
    "total_tokens",
    "api_response_seconds",
    "executed_at",
    "error_code",
)


@dataclass(frozen=True)
class ExperimentMeasurement:
    status: str
    model: str
    temperature: str
    history_mode: str
    history_turns: int
    turn_number: int
    question: str
    answer: str | None
    input_tokens: int | None
    output_tokens: int | None
    thoughts_tokens: int | None
    total_tokens: int | None
    api_response_seconds: float
    executed_at: str
    error_code: int | None = None


class ExperimentRecorder:
    """1回の記録セッションに対応するCSV/TXTファイルを管理する。"""

    def __init__(
        self,
        experiment_id: str,
        csv_path: Path,
        txt_path: Path,
        csv_file: TextIO,
        txt_file: TextIO,
        model: str,
        temperature: str,
    ) -> None:
        self.experiment_id = experiment_id
        self.csv_path = csv_path
        self.txt_path = txt_path
        self._csv_file = csv_file
        self._txt_file = txt_file
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=CSV_FIELDS)
        self._model = model
        self._temperature = temperature
        self.failure: OSError | None = None

    @classmethod
    def start(
        cls,
        model: str,
        temperature: str,
        output_dir: Path | None = None,
    ) -> "ExperimentRecorder":
        """新しい一意なIDのファイルを作成する。既存ファイルは上書きしない。"""
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        experiment_id = f"{timestamp}-{uuid4().hex}"
        csv_path = output_dir / f"{experiment_id}.csv"
        txt_path = output_dir / f"{experiment_id}.txt"
        csv_file = csv_path.open("x", newline="", encoding="utf-8")
        try:
            txt_file = txt_path.open("x", encoding="utf-8")
        except OSError:
            csv_file.close()
            csv_path.unlink(missing_ok=True)
            raise

        try:
            recorder = cls(
                experiment_id,
                csv_path,
                txt_path,
                csv_file,
                txt_file,
                model,
                temperature,
            )
            recorder._csv_writer.writeheader()
            recorder._csv_file.flush()
            recorder._txt_file.write(
                f"実験ID: {experiment_id}\n"
                f"モデル: {model}\n"
                f"temperature: {temperature}\n\n"
            )
            recorder._txt_file.flush()
            return recorder
        except OSError:
            csv_file.close()
            txt_file.close()
            csv_path.unlink(missing_ok=True)
            txt_path.unlink(missing_ok=True)
            raise

    def record(self, measurement: ExperimentMeasurement) -> None:
        """測定結果を両ファイルへ追記し、各ターンをすぐに保存する。"""
        if self.failure is not None:
            return

        row = {
            "experiment_id": self.experiment_id,
            "status": measurement.status,
            "model": measurement.model,
            "temperature": measurement.temperature,
            "history_mode": measurement.history_mode,
            "history_turns": measurement.history_turns,
            "turn_number": measurement.turn_number,
            "question": measurement.question,
            "answer": measurement.answer or "",
            "input_tokens": _csv_value(measurement.input_tokens),
            "output_tokens": _csv_value(measurement.output_tokens),
            "thoughts_tokens": _csv_value(measurement.thoughts_tokens),
            "total_tokens": _csv_value(measurement.total_tokens),
            "api_response_seconds": f"{measurement.api_response_seconds:.3f}",
            "executed_at": measurement.executed_at,
            "error_code": _csv_value(measurement.error_code),
        }
        try:
            self._csv_writer.writerow(row)
            self._csv_file.flush()
            self._write_text(measurement)
            self._txt_file.flush()
        except OSError as error:
            self.failure = error

    def _write_text(self, measurement: ExperimentMeasurement) -> None:
        self._txt_file.write(
            f"--- ターン {measurement.turn_number} "
            f"({measurement.status}) ---\n"
            f"日時: {measurement.executed_at}\n"
            f"モデル: {measurement.model}\n"
            f"temperature: {measurement.temperature}\n"
            f"履歴モード: {measurement.history_mode}\n"
            f"過去の会話ターン数: {measurement.history_turns}\n"
            f"API応答時間: {measurement.api_response_seconds:.3f} 秒\n"
            f"入力トークン数: {_text_value(measurement.input_tokens)}\n"
            f"出力トークン数: {_text_value(measurement.output_tokens)}\n"
            f"思考トークン数: {_text_value(measurement.thoughts_tokens)}\n"
            f"合計トークン数: {_text_value(measurement.total_tokens)}\n"
        )
        if measurement.status == "error":
            self._txt_file.write(
                f"エラーコード: {_text_value(measurement.error_code)}\n"
            )
        self._txt_file.write(
            f"質問:\n{measurement.question}\n\n回答:\n"
            f"{measurement.answer or ''}\n\n"
        )

    def close(self) -> None:
        """両方のファイルを閉じ、発生したI/Oエラーを呼び出し元へ返す。"""
        first_error: OSError | None = None
        for file in (self._csv_file, self._txt_file):
            try:
                file.close()
            except OSError as error:
                if first_error is None:
                    first_error = error
        if first_error is not None:
            raise first_error


def _csv_value(value: int | None) -> int | str:
    return "" if value is None else value


def _text_value(value: int | None) -> str:
    return "不明" if value is None else str(value)
