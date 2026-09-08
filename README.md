# `.spass` to `.csv` コンバーター

Samsung Passのエクスポートファイル（`.spass`）をローカルで復号し、Bitwardenにインポート可能なCSV形式に変換します。

## 特徴

- **ローカル**: 処理はデバイスのみで行われます
- **プライバシー**: パスワードは一切外部に送信されません

## 必要条件

- Python 3.9以上
- pycryptodome

```bash
pip install pycryptodome
```

## 使い方

### 1. Samsung Passからエクスポート

1. Samsung Pass(またはSamsung Wallet)アプリを開く
2. 右上三点マーク→「設定」→「Samsung Passデータをインポート/エクスポート」→「データのエクスポート」を選択
3. パスワードを設定
4. `.spass`ファイルをPCに転送

### 2. CSVに変換

```bash
python main.py backup.spass bitwarden_import.csv
```

実行時にエクスポート用パスワードの入力が求められます。入力はターミナルに表示されません。

出力ファイル名を省略した場合、デフォルトで `bw_password.csv` が生成されます。

```bash
python main.py backup.spass
```

### 3. Bitwardenにインポート

1. [Bitwarden Web版](https://vault.bitwarden.com) にログイン
2. 「ツール」→「インポート」を開く
3. ファイル形式は **「Bitwarden (csv)」** を選択
4. 生成されたCSVファイルをアップロード

## debug

復号後の生データを確認したい場合は、環境変数 `SPASS_DEBUG` を設定して実行してください。

```bash
# macOS / Linux
SPASS_DEBUG=1 python main.py backup.spass

# Windows PowerShell
$env:SPASS_DEBUG=1; python main.py backup.spass
```

`debug_payload.txt` に復号後のペイロードが出力されます。

## 注意

- 生成したCSVファイルには、パスワードが平文で含まれます。ご自身のもとで厳重に保管してください。使用後は速やかに破棄してください。
- 開発者はこのツールの使用によって生じた損害について、開発者の重大な過失を除き、一切の責任を負いません。ご自身の責任において使用してください。

## トラブルシューティング

| 症状 | 原因と対処 |
| --- | --- |
| `Decoded data is too short` | `.spass`ファイルが破損しているか、転送が不完全です。再度エクスポート・転送してください |
| `Padding is incorrect` | エクスポート用パスワードが間違っています |
| Bitwardenへのインポートが失敗する | インポート形式に「Bitwarden (csv)」を選択してください。「Chrome (csv)」等では失敗する可能性があります。また、生成したファイルの破損等によってインポートできない場合があります。 |
| CSV内に`&&&NULL&&&` が残る | バージョンを確認してください。起動時に `spass_decryptor 2026-06-13-4` と表示されます。古いバージョンの場合は更新してください |

## ライセンス

MIT License
