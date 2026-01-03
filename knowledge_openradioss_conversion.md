# OpenRadioss INP変換ノウハウ
**最終更新: 2026-01-03**

## 正しいOpenRadioss Starterフォーマット

```
#RADIOSS STARTER
/BEGIN
Run_Name
      2022         0
                  kg                   m                   s   ← Input Units
                  kg                   m                   s   ← Work Units
/TITLE
Title Text
/NODE
...
```

## 重要なポイント

### 1. /BEGIN ブロック
- `#RADIOSS STARTER` が最初の行に必須
- Run Name, Ivers/Irun, 単位行2行の順番が必須
- 単位は実数値（乗算係数）または文字表記

### 2. 座標変換
- PrePoMax INP: mm単位
- OpenRadioss: m単位（SI）
- 変換: `x/1000.0` を使用

### 3. 境界条件 (BC)
| パーツ | 役割 | BC設定 |
|--------|------|--------|
| Die | 固定 | IMPVEL/2-4 (Zero Velocity X,Y,Z) |
| Punch | 移動 | IMPVEL/1 (Velocity Ramp Z) |
| Stripper | 移動 | IMPVEL/5 (Velocity Ramp Z) |
| Material | フリー | BCなし |

### 4. Elset名のマッピング
INPファイルのElset名は様々なパターンがある:
- `Solid_part-XXX`
- `From_parts-XXX`
- 両方をチェックする必要あり

### 5. 働くスクリプトの場所
- `C:\Users\mhn15\dynamic_20251218\inp2radioss_v6.py` (AMS対応版)
- `C:\Users\mhn15\dynamic_20251218\Backup_20251230_Contact_Success\inp2radioss_v5.py`

## レッスン・ラーンド

1. **過去の成功例を必ず確認する** - ローカルに蓄積されたナレッジを活用
2. **フォーマットはバイト単位で正確に** - スペース数、改行がすべて重要
3. **エラーログ(.out)を必ず確認** - 具体的なエラー行がわかる
4. `/UNIT/MM/Mg/s` のような略記は無効 - 必ず変換係数を使用
5. Material (被加工材) には BC を設定しない - 自由に変形させる
