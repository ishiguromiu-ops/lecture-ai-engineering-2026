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

from google import genai
from google.genai import errors
from google.genai import types

from app.config import MODEL, TEMPERATURE, api_error_message, get_api_key

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

    return answer


def run_repl(history_mode: bool) -> None:
    """対話入力を受け付け、現在のプロセス内だけ会話履歴を管理する。"""
    history: list[types.Content] = []
    turn_number = 0
    print("質問を入力してください。/history on|off、/clear、/exit が使えます。")
    print(f"[history] {'ON' if history_mode else 'OFF'}")

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

        turn_number += 1
        try:
            answer = ask(
                question,
                history if history_mode else None,
                history_mode=history_mode,
                turn_number=turn_number,
            )
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            continue
        except RuntimeError as e:
            print(f"応答エラー: {e}")
            continue
        print(answer)


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
