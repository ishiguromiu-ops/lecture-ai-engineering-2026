"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 対話形式

ツールを持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse
import os
import time
from datetime import datetime
from typing import Callable

from google import genai
from google.genai import errors
from google.genai import types

from app.config import MODEL, TEMPERATURE, api_error_message, get_api_key
from app.experiment_recorder import ExperimentMeasurement, ExperimentRecorder

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def _display_value(value: int | None) -> str:
    """数値が取得できない場合は「不明」と表示する。"""
    return str(value) if value is not None else "不明"


def get_initial_history_mode() -> bool:
    """環境変数から起動時の履歴モードを取得する。"""
    value = os.getenv("AIE_HISTORY_MODE")
    if value is None:
        return False

    mode = value.strip().upper()
    if mode not in {"ON", "OFF"}:
        raise ValueError("AIE_HISTORY_MODE は ON または OFF を指定してください。")
    return mode == "ON"


def ask(
    question: str,
    history: list[types.Content] | None = None,
    *,
    history_mode: bool | None = None,
    turn_number: int = 1,
    on_measurement: Callable[[ExperimentMeasurement], None] | None = None,
) -> str:
    """質問を送り、成功時に測定値を表示してから履歴を更新する。"""
    client = genai.Client(api_key=get_api_key())
    if history_mode is None:
        history_mode = history is not None

    history_turns = (
        len(history or []) // 2
        if history_mode
        else None
    )
    if history is None:
        contents: str | list[types.Content] = question
    else:
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=question)],
        )
        contents = [*history, user_message]

    started_at = time.perf_counter()
    try:
        if TEMPERATURE is None:
            response = client.models.generate_content(model=MODEL, contents=contents)
        else:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(temperature=TEMPERATURE),
            )
    except errors.APIError as e:
        elapsed_seconds = time.perf_counter() - started_at
        history_label = "ON" if history_mode else "OFF"
        turns_label = str(history_turns) if history_turns is not None else "対象外"
        temperature_label = str(TEMPERATURE) if TEMPERATURE is not None else "default"
        print(
            "[measurement] status=error "
            f"model={MODEL} temperature={temperature_label} "
            f"history_mode={history_label} turn={turn_number} "
            f"history_turns={turns_label} elapsed_seconds={elapsed_seconds:.3f} "
            f"error_code={_display_value(e.code)}"
        )
        if on_measurement is not None:
            on_measurement(
                ExperimentMeasurement(
                    status="error",
                    model=MODEL,
                    temperature=temperature_label,
                    history_mode=history_label,
                    history_turns=history_turns or 0,
                    turn_number=turn_number,
                    question=question,
                    answer=None,
                    input_tokens=None,
                    output_tokens=None,
                    thoughts_tokens=None,
                    total_tokens=None,
                    api_response_seconds=elapsed_seconds,
                    executed_at=datetime.now().astimezone().isoformat(),
                    error_code=e.code,
                )
            )
        raise

    elapsed_seconds = time.perf_counter() - started_at
    answer = response.text
    if answer is None:
        raise RuntimeError("モデルからテキスト応答がありませんでした。")

    usage = response.usage_metadata
    input_tokens = getattr(usage, "prompt_token_count", None)
    output_tokens = getattr(usage, "candidates_token_count", None)
    thoughts_tokens = getattr(usage, "thoughts_token_count", None)
    total_tokens = getattr(usage, "total_token_count", None)
    history_label = "ON" if history_mode else "OFF"
    turns_label = str(history_turns) if history_turns is not None else "対象外"
    temperature_label = str(TEMPERATURE) if TEMPERATURE is not None else "default"
    print(
        "[measurement] status=success "
        f"model={MODEL} temperature={temperature_label} "
        f"history_mode={history_label} turn={turn_number} "
        f"history_turns={turns_label} elapsed_seconds={elapsed_seconds:.3f} "
        f"input_tokens={_display_value(input_tokens)} "
        f"output_tokens={_display_value(output_tokens)} "
        f"thoughts_tokens={_display_value(thoughts_tokens)} "
        f"total_tokens={_display_value(total_tokens)}"
    )

    if history is not None:
        history.extend(
            [
                user_message,
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=answer)],
                ),
            ]
        )

    if on_measurement is not None:
        on_measurement(
            ExperimentMeasurement(
                status="success",
                model=MODEL,
                temperature=temperature_label,
                history_mode=history_label,
                history_turns=history_turns or 0,
                turn_number=turn_number,
                question=question,
                answer=answer,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                thoughts_tokens=thoughts_tokens,
                total_tokens=total_tokens,
                api_response_seconds=elapsed_seconds,
                executed_at=datetime.now().astimezone().isoformat(),
            )
        )

    return answer


def run_repl(history_mode: bool) -> None:
    """対話入力を受け付け、現在のプロセス内だけ会話履歴を管理する。"""
    history: list[types.Content] = []
    request_number = 0
    recorder: ExperimentRecorder | None = None
    record_turn_number = 0
    print(
        "質問を入力してください。/history on|off、/clear、"
        "/record on|off、/exit が使えます。"
    )
    print(f"[history] {'ON' if history_mode else 'OFF'}")

    def report_recording_failure() -> None:
        nonlocal recorder
        if recorder is None or recorder.failure is None:
            return
        failed_recorder = recorder
        recorder = None
        print(f"記録に失敗したため停止します: {failed_recorder.failure}")
        _close_recorder(failed_recorder)

    try:
        while True:
            try:
                question = input("質問> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n終了します。")
                return

            if not question:
                continue

            command = question.lower()
            if command == "/exit":
                print("終了します。")
                return
            if command == "/clear":
                history.clear()
                print("会話履歴を初期化しました。")
                continue
            if command == "/history on":
                history_mode = True
                print("[history] ON")
                continue
            if command == "/history off":
                history_mode = False
                history.clear()
                print("[history] OFF（会話履歴を消去しました）")
                continue
            if command.startswith("/history"):
                print("使い方: /history on または /history off")
                continue
            if command == "/record on":
                if recorder is not None:
                    print(
                        "[record] すでに記録中です: "
                        f"{recorder.csv_path} / {recorder.txt_path}"
                    )
                    continue
                temperature_label = (
                    str(TEMPERATURE) if TEMPERATURE is not None else "default"
                )
                try:
                    recorder = ExperimentRecorder.start(MODEL, temperature_label)
                except OSError as e:
                    print(f"記録ファイルを作成できませんでした: {e}")
                    continue
                record_turn_number = 0
                print(f"[record] ON id={recorder.experiment_id}")
                print(f"[record] CSV: {recorder.csv_path}")
                print(f"[record] TXT: {recorder.txt_path}")
                continue
            if command == "/record off":
                if recorder is None:
                    print("[record] すでに停止しています。")
                    continue
                stopped_recorder = recorder
                recorder = None
                _stop_recorder(stopped_recorder)
                continue
            if command.startswith("/record"):
                print("使い方: /record on または /record off")
                continue

            request_number += 1
            if recorder is not None:
                record_turn_number += 1
                turn_number = record_turn_number
                measurement_callback = recorder.record
            else:
                turn_number = request_number
                measurement_callback = None
            try:
                answer = ask(
                    question,
                    history if history_mode else None,
                    history_mode=history_mode,
                    turn_number=turn_number,
                    on_measurement=measurement_callback,
                )
            except errors.APIError as e:
                print(api_error_message(e.code, e.message))
                report_recording_failure()
                continue
            except RuntimeError as e:
                print(f"応答エラー: {e}")
                report_recording_failure()
                continue
            report_recording_failure()
            print(answer)
    finally:
        if recorder is not None:
            _stop_recorder(recorder)


def _close_recorder(recorder: ExperimentRecorder) -> None:
    try:
        recorder.close()
    except OSError as error:
        print(f"記録ファイルを閉じられませんでした: {error}")


def _stop_recorder(recorder: ExperimentRecorder) -> None:
    _close_recorder(recorder)
    print("[record] OFF")
    print(f"[record] CSV: {recorder.csv_path}")
    print(f"[record] TXT: {recorder.txt_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?")
    args = parser.parse_args()

    try:
        history_mode = get_initial_history_mode()
    except ValueError as e:
        parser.error(str(e))

    print(f"[model] {MODEL}")
    if TEMPERATURE is None:
        print("[temperature] モデルのデフォルト（AIE_TEMPERATURE 未設定）")
    else:
        print(f"[temperature] {TEMPERATURE}")

    if args.question is None:
        run_repl(history_mode)
        return

    print(f"[質問] {args.question}\n")
    try:
        print(ask(args.question, history_mode=history_mode, turn_number=1))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
