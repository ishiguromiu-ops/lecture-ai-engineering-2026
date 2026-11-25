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