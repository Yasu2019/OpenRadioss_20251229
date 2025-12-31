# OpenRadioss 開発経験記録 (2025/12/31)

## 概要

このドキュメントは、PrePoMax (Calculix INP) から OpenRadioss への変換プロジェクトで得られた経験と教訓をまとめたものです。
将来の Johnson-Cook 実装やシステム発展に活用するために記録します。

---

## 1. プロジェクト構成

### ファイル構成
```
├── inp2radioss_v5.py       # メイン変換スクリプト（継続的に改良）
├── anim_to_vtk_enhanced.py # 拡張VTK変換（η, Lode, σ1 自動計算）
├── knowledge/openradioss/  # 知識ベース
│   ├── OpenRadioss_Conversion_Guide.md
│   ├── sample_0000.rad     # Starter サンプル
│   └── sample_0001.rad     # Engine サンプル
└── .agent/workflows/
    └── openradioss-check.md # 設定確認プロトコル
```

---

## 2. 成功した設定

### 2.1 材料モデル
```
/MAT/LAW1/1    ← 弾性材料 (Punch/Die用)
/MAT/LAW2/2    ← 弾塑性材料 (Material用) + Xmax で要素削除
```

### 2.2 境界条件
```
/IMPVEL/1      ← Punch に Z 方向速度
/IMPVEL/2,3,4  ← Die に X, Y, Z 方向ゼロ速度 (固定)
```
**注意:** `/BCS` カードは認識されない場合があるため、`/IMPVEL` + ゼロ速度関数で代替

### 2.3 接触定義
```
/INTER/TYPE7/1  ← Punch ↔ Material (Node-to-Surface)
/INTER/TYPE7/2  ← Die ↔ Material
  - Slave: ノードグループ (GRNOD)
  - Master: サーフェス (SURF/PART)
  - Stfac: 100.0 (接触剛性係数)
```

### 2.4 Mass Scaling
```
/DT/NODA/CST
  Tmin = 1.0E-07  ← 計算速度と安定性のバランス
  Tscale = 0.90
```

### 2.5 出力設定 (Engine)
```
/ANIM/ELEM/EPSP     ← 相当塑性ひずみ (PEEQ)
/ANIM/ELEM/VONM     ← ミーゼス応力
/ANIM/ELEM/ENER     ← 内部エネルギー
/ANIM/ELEM/SIGX     ← σxx (応力成分)
/ANIM/ELEM/SIGY     ← σyy
/ANIM/ELEM/SIGZ     ← σzz
/ANIM/ELEM/SIGXY    ← σxy
/ANIM/ELEM/SIGYZ    ← σyz
/ANIM/ELEM/SIGZX    ← σzx
/ANIM/VECT/DISP     ← 変位ベクトル
/ANIM/VECT/VEL      ← 速度ベクトル
```

---

## 3. 失敗した試みと教訓

### 3.1 Johnson-Cook (LAW36) - ERROR 912
**症状:** Starter で `ERROR IN MATERIAL LAW TYPE 36`

**原因:** フォーマット不一致（フィールド幅、行数、パラメータ順序）

**教訓:**
- OpenRadioss のフォーマットは非常に厳格
- 小規模テストモデルで検証してから本番適用
- 公式マニュアルのフォーマット仕様を精読

**代替策:** LAW2 + Xmax で十分な破壊シミュレーションが可能

### 3.2 追加出力指標 - ERROR 73
**症状:** Engine で `ERROR IN SOLVER INPUT DECK CARD: ANIM`

**失敗したキーワード:**
- `/ANIM/ELEM/P`      ← 主応力
- `/ANIM/ELEM/TSTA`   ← 3軸応力度
- `/ANIM/ELEM/DAM`    ← ダメージ
- `/ANIM/BRICK/TENS`  ← 応力テンソル
- `/ANIM/ELEM/EPSD`   ← ひずみ速度

**成功したキーワード:**
- `/ANIM/ELEM/SIGX`, `SIGY`, `SIGZ`, `SIGXY`, `SIGYZ`, `SIGZX`

**教訓:**
- キーワードは1つずつ追加してテスト
- 公式ドキュメントと実際のサポート状況が異なる場合がある

**代替策:** 応力成分を出力し、Pythonでポスト処理

### 3.3 過熱シャットダウン
**症状:** 計算途中でPCが強制シャットダウン

**原因:** 12スレッドのフルロードでCPU温度が臨界点 (103°C) に到達

**対策:**
- スレッド数を 8 に削減
- ノートPC使用時は冷却台を使用

---

## 4. ポスト処理による派生指標計算

応力成分 (SIGX, SIGY, SIGZ, SIGXY, SIGYZ, SIGZX) から以下を計算可能：

### 4.1 応力3軸度 (Triaxiality) η
```python
sigma_m = (sxx + syy + szz) / 3.0  # 静水圧応力
sigma_vm = sqrt(0.5 * ((sxx-syy)**2 + (syy-szz)**2 + (szz-sxx)**2 + 6*(sxy**2 + syz**2 + szx**2)))
eta = sigma_m / sigma_vm
```

**解釈:**
- η > 0.33: 引張支配 → 延性ボイド成長
- η ≈ 0: 純粋せん断
- η < 0: 圧縮支配

### 4.2 Lode パラメータ
```python
# 主応力を固有値計算で取得
s1, s2, s3 = sorted(eigenvalues, reverse=True)
lode = (2*s2 - s1 - s3) / (s1 - s3)
```

**解釈:**
- θ = -1: 軸対称引張
- θ = 0: 純粋せん断
- θ = +1: 軸対称圧縮

### 4.3 主応力 σ1, σ2, σ3
```python
stress_tensor = [[sxx, sxy, szx], [sxy, syy, syz], [szx, syz, szz]]
eigenvalues = np.linalg.eigvalsh(stress_tensor)
s1, s2, s3 = sorted(eigenvalues, reverse=True)
```

---

## 5. 今後の発展に向けて

### 5.1 Johnson-Cook 実装へのロードマップ
1. **公式マニュアルの精読** - LAW36 のフォーマット仕様を完全理解
2. **1要素テストモデル** - 最小構成で LAW36 を検証
3. **段階的パラメータ追加** - 1パラメータずつ追加してエラーを特定
4. **温度連成** - 必要に応じて熱-構造連成を追加

### 5.2 ダメージモデルのオプション
| モデル | OpenRadioss キーワード | 複雑度 |
|--------|----------------------|--------|
| 塑性ひずみ基準 | LAW2 + Xmax | 低 ✅ |
| BIQUAD | /FAIL/BIQUAD | 中 |
| Johnson-Cook Failure | /FAIL/JOHNSON | 中 |
| GTN | LAW52 (Gurson) | 高 |

### 5.3 推奨ワークフロー
```
1. 安定版でまず計算を成功させる（LAW2 + Xmax）
2. 応力成分を出力（SIGX, SIGY, SIGZ, etc.）
3. anim_to_vtk_enhanced.py で η, Lode, σ1 を計算
4. ParaView で可視化・評価
5. 必要に応じて材料モデルを高度化
```

---

## 6. 重要なコマンド集

### シミュレーション実行
```powershell
# Starter
D:\OpenRadioss\exec\starter_win64.exe -i Punch_Die_Shearing_v5_0000.rad

# Engine (8スレッド推奨)
$env:OMP_NUM_THREADS=8
D:\OpenRadioss\exec\engine_win64.exe -i Punch_Die_Shearing_v5_0001.rad -nt 8
```

### VTK変換
```powershell
# 基本変換
D:\OpenRadioss\exec\anim_to_vtk_win64.exe Punch_Die_Shearing_v5A001 > output.vtk

# 拡張変換（η, Lode, σ1 計算付き）
python anim_to_vtk_enhanced.py --batch Punch_Die_Shearing_v5
```

### Git バックアップ
```powershell
git add .
git commit -m "説明メッセージ"
git push origin master
```

### 設定確認
```powershell
# Gemini で実行
/openradioss-check
```

---

## 7. 参考リンク

- [OpenRadioss GitHub](https://github.com/OpenRadioss/OpenRadioss)
- [OpenRadioss Documentation](https://openradioss.atlassian.net/wiki/spaces/OPENRADIOSS/overview)
- [Altair Radioss Reference Guide](https://altair.com/radioss)

---

## 8. 更新履歴

| 日付 | 内容 |
|------|------|
| 2025/12/31 | 初版作成 - 基本設定、失敗事例、ポスト処理手法を記録 |
