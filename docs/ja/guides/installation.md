# インストールガイド

このガイドでは、Pythonの環境にmtaioをインストールする方法を説明します。

## 動作要件

- Python 3.11以降
- 追加の依存関係なし

## インストール方法

### pipを使用する場合

最も簡単なインストール方法はpipを使用することです:

```bash
pip install mtaio
```

### Poetryを使用する場合

Poetryを使用している場合:

```bash
poetry add mtaio
```

### pipenvを使用する場合

Pipenvを使用している場合:

```bash
pipenv install mtaio
```

## インストールの確認

以下のようにPythonを実行してmtaioをインポートすることで、インストールを確認できます:

```python
import mtaio
print(mtaio.__version__)  # 現在のバージョンが表示されます
```

## バージョンの確認

mtaioはPython 3.11以降が必要です。Pythonのバージョンは以下のコマンドで確認できます:

```bash
python --version
```

古いバージョンのPythonを使用している場合は、mtaioをインストールする前にアップグレードする必要があります。

## 機能

mtaioには以下のモジュールがすべて同梱されています:

- コア機能(`mtaio.core`)
- キャッシュシステム(`mtaio.cache`)
- イベント処理(`mtaio.events`)
- データ処理(`mtaio.data`)
- プロトコル実装(`mtaio.protocols`)
- リソース管理(`mtaio.resources`)
- モニタリングツール(`mtaio.monitoring`)
- ロギングユーティリティ(`mtaio.logging`)
- 型定義(`mtaio.typing`)
- デコレータユーティリティ(`mtaio.decorators`)
- 例外処理(`mtaio.exceptions`)

すべての機能が基本パッケージに含まれているため、追加のパッケージをインストールする必要はありません。

## 開発用インストール

開発目的の場合、ソースから直接インストールすることができます:

```bash
git clone https://github.com/t3tra-dev/mtaio.git
cd mtaio
pip install -e .
```

## アンインストール

mtaioをアンインストールする必要がある場合:

```bash
pip uninstall mtaio
```

## 次のステップ

インストール後は:

1. [はじめに](getting-started.md)を読んでmtaioの概要を理解する
2. [基本的な使い方](basic-usage.md)で一般的な使用パターンを確認する
3. [APIリファレンス](../api/index.md)で詳細なドキュメントを参照する

## トラブルシューティング

インストールで問題が発生した場合:

1. Python 3.11以降を使用していることを確認する
2. pipが最新であることを確認する: `pip install --upgrade pip`
3. ソースからインストールする場合は、Gitがインストールされていることを確認する

問題が解決しない場合は、[トラブルシューティングガイド](troubleshooting.md)を確認するか、GitHubで[issue](https://github.com/t3tra-dev/mtaio/issues)を作成してください。
