# 第6回 解答

## 演習

<!-- [tool call] の行は、表示された行をそのまま貼り付けてください。終わらなかった STEP は、空欄のままでかまいません。 -->

- STEP 1 のツールの名前：[glossary_search_glossary]
- STEP 2 の [tool call]：glossary_search_glossary({'query': '3レベル'})
- STEP 3 の [tool call]： fetch_fetch({'url': 'https://modelcontextprotocol.io/'})
- STEP 4 の [tool call]：
    1. １回目：aws_aws___search_documentation({'search_phrase': 'Amazon S3 バージョニング 概要', 'topics': ['general']})
    2. ２回目：aws_aws___search_documentation({'search_phrase': 'Using versioning S3 developer guide', 'topics': ['general']})
- 気づき・疑問：MCPサーバーとの接続はもっと複雑な作業だと思っていましたが、設定を追加するだけで簡単にツールを利用できるようになったことが印象的でした。また、MCPサーバーを1つ追加するだけで、複数のツールが利用可能になることも分かりました。一方で、接続自体が簡単だからこそ、利用するMCPサーバーが信頼できるものか、公開される各ツールにどのような機能や権限があるのかを確認し、安全性を判断することの方が難しいと感じました。

## 宿題

<!-- 基礎・実装・発展のどれか1つに取り組めば完了です。 -->

### 基礎
- 取り組んだレベル：基礎
- やったこと：`app/mcp_server.py`に`server.tool()(tools.get_lecture_summary)`を追加し、講義の要点を取得する関数をMCPツールとして公開した。
- 結果：
    - `--list-tools`で公開ツール数が7個から8個に増え、`glossary_get_lecture_summary`が追加されたことを確認した。
    - また、第2回の内容を質問したところ、`--trace`で`glossary_get_lecture_summary({'lecture': 2})`が呼び出され、取得した講義要点に基づくサマリーが回答されたことを確認した。
- 気づき・疑問：
    - 既存のPython関数をMCPツールとして公開する作業は1行の追加で済み、想像以上に簡単だった。自作のツールを同じエージェントで利用するだけなら、直接関数を登録する方法との違いはあまり感じなかった。
    - MCPを使うメリットは次の２点にあると考えた。
        1. 他者が作成したツールも共通の仕組みで接続でき、外部の便利な機能を簡単に利用できる。
        2. 自分が作成したツールを他のMCP対応アプリケーションでも再利用・共有しやすくなる。

### 実装
- 取り組んだレベル：実装
- やったこと：
    1. 第3回で作成した`make_quiz`関数を、`app/mcp_server.py`に`server.tool()(tools.make_quiz)`を追加してMCPツールとして公開した。
    2. なお、引数が範囲外の場合については、指定した講義回の用語が未登録の場合に、理由と対処方法を`return`で返すようにした。
    3. 第9回と第99回の確認問題を依頼し、`return`でメッセージを返す場合と、`raise ValueError`で例外を発生させる場合の違いを`--trace`で比較した。
- 結果：
    1. 正常動作の確認（範囲内の質問をした場合）
        - 公開ツール数が8個から9個に増え、`glossary_make_quiz`が追加された。
        - 第2回の確認問題を依頼すると、`glossary_make_quiz({'lecture': 2})`が正常に呼び出され、「学習率」に関する問題が出題された。

    2. 引数が範囲外の場合の`return`と`raise`の比較
        - `return`の場合：`[tool return]`に「第99回の用語が見つかりませんでした。」と表示された。Geminiも、用語が未登録であることを理由に、問題を作成できないと説明した。
        - `raise`の場合：`[tool error]`に`Error executing tool make_quiz`（make_quizツールの実行エラー）と表示された。Python側では詳細なエラー内容が表示されたが、モデルに渡る情報は汎用的なエラーメッセージだった。
        - このため、`return`では問題を作成できない理由がモデルに伝わる一方、`raise`では具体的な原因が伝わらなかった。

    3. `raise`の場合のモデルの回答の違い（第99回・第9回）
        - 第99回：Geminiは「第99回という回は存在しないため、確認問題を作成できない」と回答した。
        - 第9回：Geminiは「ツールのエラーにより正常に取得できなかった」と回答し、用語が未登録であることには言及しなかった。
        - どちらもモデルに渡されたツールのエラー情報は`Error executing tool make_quiz`だったが、最終回答は異なった。モデルが質問内容などから判断した可能性があるものの、判断の根拠までは確認できなかった。

    4. `return`のメッセージの変更後
        - 2・3の結果を踏まえ、モデルの返事をより分かりやすくするため、returnのメッセージを、「f"第{lecture}回の用語が用語集に登録されていないため、確認問題は作成できません。用語が登録されている別の回を指定してください。」に変更した。
        - 変更後、第9回の確認問題を依頼したところ、モデルは「第9回の用語が用語集に登録されていないため」と理由を説明し、別の回を指定するよう案内した。

- 気づき・疑問：
    1. ツールからモデルに渡す情報の重要性
        - `return`の場合、用語が未登録であるという原因と、別の回を指定するという対処方法がモデルに伝わり、利用者にも分かりやすい回答になった。
        - 一方、`raise`の場合は具体的な原因がモデルに伝わらないため、回答の内容はモデル側の判断に依存する可能性がある。特に第9回について聞く質問では、利用者にとって何が悪かったのか、どうすればよいのかが分かりにくい回答になった。
        - ツールから必要な情報を適切に渡すことが、モデルの回答の正確性や分かりやすさにつながると感じた。

    2. `return`と`raise`の使い分け
        - 今回のように、指定された回の用語が未登録であることは想定内の状況なので、`return`で理由と対処方法を案内する方が適切だと考えた。
        - 一方、データの破損など、プログラムが正常に処理できない想定外の異常は、例外として扱う方が適切だと理解した。
        - 想定内の「データがない」と、想定外の「処理が失敗した」を区別してツールを設計することが重要だと分かった。

### 発展
- 取り組んだレベル：発展
- やったこと：
    1. MCPクライアントとしてCodexを選び、MCPサーバーの設定方法を公式ドキュメントで調査した。演習で使用した`app/mcp_servers.json`との違いを比較した。
    2. CodespacesにCodex CLIをインストールし、以下のコマンドで演習用の`glossary`サーバーを登録した。

       ```bash
       codex mcp add glossary -- uv run python -m app.mcp_server
       ```

    3. さらに、Windows版Codexアプリをインストールした。演習リポジトリをWindowsにクローンし、Pythonの実行環境を構築した上で、Windows側の`config.toml`にも`glossary`サーバーを登録した。
    4. Codex CLIとWindows版Codexアプリのそれぞれから、MCP経由で`make_quiz`を呼び出せるか検証した。

- 結果：
    1. CodexのMCP設定方法と演習のJSONファイルの比較

       | 比較項目 | CodexのTOML | 演習のJSON |
       |---|---|---|
       | 設定を書く場所 | ユーザー単位の場合は`~/.codex/config.toml`、プロジェクト単位の場合は`.codex/config.toml`。`codex mcp add`コマンドでも登録できる。 | 講義用エージェントの`app/mcp_servers.json` |
       | コマンドで起動する書き方 | `[mcp_servers.サーバー名]`の下に`command`と`args`を指定する。 | サーバー名をキーとするオブジェクト内に`command`と`args`を指定する。 |
       | URLで接続する書き方 | `[mcp_servers.サーバー名]`の下に`url`を指定する。 | サーバー名をキーとするオブジェクト内に`url`を指定する。 |
       | 有効になる範囲 | ユーザー単位またはプロジェクト単位で設定可能。プロジェクト設定は信頼済みプロジェクトで有効になる。 | 演習用エージェントが参照する設定として有効になる。 |

       設定例は以下のとおり。
       - Codex（TOML）

       ```toml
       [mcp_servers.glossary]
       command = "uv"
       args = ["run", "python", "-m", "app.mcp_server"]

       [mcp_servers.aws]
       url = "https://knowledge-mcp.global.api.aws"
       ```

       - 演習用エージェント（JSON）

       ```json
       {
         "glossary": {
           "command": "uv",
           "args": ["run", "python", "-m", "app.mcp_server"]
         },
         "aws": {
           "url": "https://knowledge-mcp.global.api.aws"
         }
       }
       ```

    2. Codespaces上のCodex CLIでの動作確認

       - `codex mcp add glossary -- uv run python -m app.mcp_server`を実行して、`glossary`サーバーを登録した。
       - `codex mcp list`で登録を確認したところ、`glossary`が`enabled`と表示された。
       - Codespaces内の`~/.codex/config.toml`には、以下の設定が追加されていた。

         ```toml
         [mcp_servers.glossary]
         command = "uv"
         args = ["run", "python", "-m", "app.mcp_server"]
         ```

       - Codex CLIから第2回の確認問題を1問作成するよう依頼したところ、`glossary.make_quiz`が呼び出され、「QLoRA」に関する問題が出題された。
       - これにより、講義のGeminiエージェントで利用していたMCPサーバーを、Codex CLIからも利用できることを確認した。

    3. Windows版Codexアプリでの動作確認

       - Windows PCに演習リポジトリをクローンし、`uv sync`でPythonの実行環境を構築した。
       - Windows上でも`make_quiz`関数を直接実行できることを確認した。
       - Windows側の`~/.codex/config.toml`に、`glossary`サーバーの起動設定を追記した。
       - 当初は`command = "uv"`としていたため、Codexアプリからサーバーを起動できず、`MCP startup failed: program not found`というエラーが発生した。
       - そこで、`command`に`uv.exe`の絶対パスを指定し、Codexアプリを完全終了して再起動した。その結果、`make_quiz`がMCP経由で正常に呼び出され、「LoRA」に関する問題が出題された。
       - Windows版では、uv.exeの絶対パスと--directoryによる演習リポジトリの指定を行った。Codespacesとは異なり、Windows側の実行環境に合わせて設定を調整することで接続できた。

- 気づいたこと・疑問：
    1. MCPサーバーの設定形式の共通点
       - 演習のJSONとCodexのTOMLでは、ファイル形式や階層の書き方は異なるものの、接続に必要な基本情報は共通している。
       - ローカルの`glossary`サーバーは`command`と`args`で起動方法を指定し、AWSのMCPサーバーは`url`で接続先を指定する。この考え方は演習とCodexで共通している。

    2. Codexの特徴＝設定の適用範囲や接続方法の柔軟な管理
       - 演習の`app/mcp_servers.json`は講義用エージェントが参照する設定であり、ユーザー単位・プロジェクト単位を切り替える仕組みは設けられていないのに対し、Codexではユーザー単位とプロジェクト単位の設定を使い分けられる。
       - また、環境変数、認証情報、HTTPヘッダー、タイムアウト、利用可能なツールの制限など、演習よりも多くの設定項目が用意されている。さまざまな環境やセキュリティ要件に対応するためだと考えた。

    3. MCPの共通化と実行環境の共通化は別である
       - Codex CLIとWindows版Codexアプリは、同じCodexの設定ファイルを参照する環境であれば、MCP設定を共有できるが、今回は、Codex CLIをCodespaces上で、デスクトップアプリをWindows上で利用したため、設定ファイルが別々に存在していた。
       - そのため、Codespacesでは`codex mcp add`コマンドで、Windowsでは`config.toml`への直接追記によって、それぞれMCPサーバーを登録する必要があった。
       - さらに、Windows版では、`uv`の実行ファイルを見つけられずにエラーが発生した。MCPという共通規格を使っていても、サーバーを動かす環境に応じた設定や調整は必要だと分かった。

    4. 自作MCPツールの再利用性
       - 第3回で作成した`make_quiz`関数を変更することなく、講義のGeminiエージェント、Codespaces上のCodex CLI、Windows版Codexアプリのいずれからも利用できた。
       - MCPを使うことで、AIクライアントごとにツールの処理を作り直さずに済むことを実感した。

- 調べた日付と参照した公式ドキュメント：
    - 調査日：2026年11月27日
    - 参照した公式ドキュメント：
        - CodexのMCP設定：https://learn.chatgpt.com/ja-JP/docs/extend/mcp
        - Codexの構成リファレンス：https://learn.chatgpt.com/ja-JP/docs/config-file/config-reference
        - Codexの設定の基本：https://learn.chatgpt.com/ja-JP/docs/config-file/config-basic
