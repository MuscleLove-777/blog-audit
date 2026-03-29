# ブログ監査システム

FANZAアフィリエイトブログ群（全9サイト）の自動監査システム。

## 機能
- HTTP応答・CSS・記事数・画像・リンク・SEO・テーマ・レスポンシブを自動チェック
- GitHub Pagesでダッシュボード公開
- パワポレポート自動生成
- 毎日 JST 10:00 に自動実行

## 使い方

### 監査実行
```bash
python3 scripts/audit.py
```

### パワポレポート生成
```bash
python3 scripts/generate_report.py
```

## ファイル構成
- `scripts/audit.py` - メイン監査スクリプト
- `scripts/generate_report.py` - パワポレポート生成
- `docs/index.html` - オンラインダッシュボード
- `results/latest.json` - 最新監査結果
- `reports/` - パワポレポート出力先
