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

- 取り組んだレベル：基礎 / 実装 / 発展
- やったこと：
- 結果：
- 気づき・疑問：
