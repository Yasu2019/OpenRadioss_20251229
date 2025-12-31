---
description: OpenRadioss シミュレーション設定の読み込みと検証
---

# OpenRadioss 設定読み込みプロトコル

このプロトコルは、OpenRadioss の Starter/Engine ファイルからシミュレーション設定を抽出し、ユーザーに分かりやすく提示するためのものです。

## 前提条件
- OpenRadioss の Starter ファイル (`*_0000.rad`) が存在すること
- OpenRadioss の Engine ファイル (`*_0001.rad`) が存在すること

---

## Step 1: ファイルの特定

ユーザーに対象ファイルを確認するか、ディレクトリから自動検出する。

```powershell
Get-ChildItem *.rad | Select-Object Name, Length, LastWriteTime
```

**確認事項:**
- `*_0000.rad` = Starter ファイル
- `*_0001.rad` = Engine ファイル

---

## Step 2: 基本情報の抽出 (Starter)

### 2.1 タイトルと単位系
```powershell
Select-String -Path "*_0000.rad" -Pattern "/TITLE|/UNIT|/BEGIN" -Context 0,3
```

### 2.2 パーツ一覧
```powershell
Select-String -Path "*_0000.rad" -Pattern "/PART/" -Context 0,2
```

**出力フォーマット:**
| パーツID | 名前 | 材料ID | プロパティID |
|----------|------|--------|--------------|

---

## Step 3: 材料特性の抽出 (Starter)

```powershell
Select-String -Path "*_0000.rad" -Pattern "/MAT/" -Context 0,10
```

**抽出すべき情報:**
- 材料ID と名前
- 材料法則 (LAW2 = 弾塑性, LAW1 = 弾性, etc.)
- 密度 (Rho)
- ヤング率 (E)
- ポアソン比 (Nu)
- 降伏応力 (Sigma_y)
- 破壊ひずみ (Xmax) ※ある場合

**単位確認:**
- 密度: g/mm³ (例: 7.85E-9)
- ヤング率: MPa (例: 210000)
- 応力: MPa (例: 235)

---

## Step 4: 境界条件の抽出 (Starter)

### 4.1 固定境界条件 (/BCS)
```powershell
Select-String -Path "*_0000.rad" -Pattern "/BCS/" -Context 0,5
```

**確認事項:**
- Tra_rot フラグ (111111 = 全固定, 111000 = 並進のみ固定)
- 適用されるノードグループ ID (Gnod_ID)

### 4.2 速度境界条件 (/IMPVEL)
```powershell
Select-String -Path "*_0000.rad" -Pattern "/IMPVEL/" -Context 0,8
```

**確認事項:**
- 方向 (X, Y, Z)
- 参照する関数 ID (Funct_ID)
- 適用されるノードグループ ID (Gnod_ID)

### 4.3 荷重/速度関数 (/FUNCT)
```powershell
Select-String -Path "*_0000.rad" -Pattern "/FUNCT/" -Context 0,10
```

**確認事項:**
- 時刻-値のペア
- ランプアップ時間（急すぎると不安定化）

---

## Step 5: 接触定義の抽出 (Starter)

```powershell
Select-String -Path "*_0000.rad" -Pattern "/INTER/" -Context 0,10
```

**確認事項:**
- 接触タイプ (TYPE7 = Node-to-Surface, TYPE25 = Surface-to-Surface)
- Slave ID (通常: 変形する部品)
- Master ID (通常: 剛体または硬い部品)
- 摩擦係数 (Fric)
- 接触剛性係数 (Stfac)

**チェックリスト:**
- [ ] すべての接触ペアが定義されているか
- [ ] Slave/Master の方向は正しいか

---

## Step 6: ノードグループとサーフェスの確認 (Starter)

### 6.1 ノードグループ
```powershell
Select-String -Path "*_0000.rad" -Pattern "/GRNOD/" -Context 0,2
```

### 6.2 サーフェス定義
```powershell
Select-String -Path "*_0000.rad" -Pattern "/SURF/" -Context 0,2
```

**確認事項:**
- 境界条件で参照される ID が存在するか
- 接触定義で参照される ID が存在するか

---

## Step 7: 解析設定の抽出 (Engine)

```powershell
Get-Content "*_0001.rad"
```

**抽出すべき情報:**
| 項目 | キーワード | 例 |
|------|-----------|-----|
| 解析終了時刻 | `/RUN` の2行目 | 0.020 (= 20 ms) |
| アニメーション出力頻度 | `/ANIM/DT` | 5.0E-4 (= 0.5 ms毎) |
| リスタート保存頻度 | `/RFILE` | 5000 (サイクル毎) |

---

## Step 8: 設定サマリの生成

上記の情報を以下のフォーマットでまとめる：

```markdown
# シミュレーション設定サマリ

## 基本情報
- **タイトル:** [タイトル]
- **単位系:** mm-g-ms

## パーツ構成
| ID | 名前 | 材料 | 役割 |
|----|------|------|------|
| 1 | Punch | Steel | 上型 (移動) |
| 2 | Material | Steel | 被加工材 |
| 3 | Die | Steel | 下型 (固定) |

## 材料特性
| 材料ID | 名前 | 密度 | E | Nu | 降伏応力 |
|--------|------|------|---|-----|---------|
| 1 | Steel | 7.85E-9 g/mm³ | 210 GPa | 0.3 | 235 MPa |

## 境界条件
| 対象 | 条件 | 詳細 |
|------|------|------|
| Punch | 速度移動 | Z方向 -0.333 mm/ms (5msでランプアップ) |
| Die | 完全固定 | X, Y, Z = 0 |

## 接触定義
| ID | タイプ | Slave | Master | 摩擦 |
|----|--------|-------|--------|------|
| 1 | TYPE7 | Material面 | Punch面 | 0.1 |
| 2 | TYPE7 | Material面 | Die面 | 0.1 |

## 解析設定
- **終了時刻:** 20 ms
- **アニメーション出力:** 0.5 ms 毎
- **リスタート保存:** 5000 サイクル毎
```

---

## Step 9: 設定の妥当性チェック

以下の項目を自動チェック：

### 9.1 境界条件チェック
- [ ] 固定すべきパーツ (Die) が固定されているか
- [ ] 動かすパーツ (Punch) に速度/荷重が設定されているか
- [ ] ノードグループ ID が実際に存在するか

### 9.2 接触チェック
- [ ] すべての接触ペアが定義されているか
- [ ] Slave/Master の ID が存在するか

### 9.3 材料チェック
- [ ] 密度、ヤング率の単位が mm-g-ms 系に適合しているか
- [ ] 降伏応力が現実的な値か

### 9.4 解析設定チェック
- [ ] 解析時間が十分か（変形完了まで）
- [ ] アニメーション出力頻度が適切か

---

## 使用例

```
/openradioss-check
```

このコマンドで上記のすべてのステップを自動実行し、設定サマリと妥当性チェック結果を出力する。
