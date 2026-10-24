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

from google import genai
from google.genai import errors
from google.genai import types

from app.config import MODEL, TEMPERATURE, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def get_initial_history_mode() -> bool:
    """環境変数から起動時の履歴モードを取得する。"""
    value = os.getenv("AIE_HISTORY_MODE")
    if value is None:
        return False

    mode = value.strip().upper()
    if mode not in {"ON", "OFF"}:
        raise ValueError("AIE_HISTORY_MODE は ON または OFF を指定してください。")
    return mode == "ON"


def ask(question: str, history: list[types.Content] | None = None) -> str:
    """質問を送り、成功した場合だけ質問と回答を会話履歴に追加する。"""
    client = genai.Client(api_key=get_api_key())
    if history is None:
        contents: str | list[types.Content] = question
    else:
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=question)],
        )
        contents = [*history, user_message]

    if TEMPERATURE is None:
        response = client.models.generate_content(model=MODEL, contents=contents)
    else:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(temperature=TEMPERATURE),
        )

    answer = response.text
    if answer is None:
        raise RuntimeError("モデルからテキスト応答がありませんでした。")

    usage = response.usage_metadata
    input_tokens = usage.prompt_token_count if usage else None
    output_tokens = usage.candidates_token_count if usage else None
    print(f"[tokens] input={input_tokens if input_tokens is not None else '不明'} "
          f"output={output_tokens if output_tokens is not None else '不明'}")

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

        try:
            answer = ask(question, history if history_mode else None)
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
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
