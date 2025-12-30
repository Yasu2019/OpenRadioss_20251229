# OpenRadioss 剪断シミュレーション最終プロトコル
# Final Protocol for Google Antigravity Agent

---

## クイックリファレンス

| 項目 | 設定値 |
|------|--------|
| INPファイル | `C:\Users\mhn15\dynamic_20251218\Punch_Die_1Piece_Material_20251229.inp` |
| 単位系 | MM_TON_S (mm, ton, s) |
| 材料硬化 | **等方硬化 (Isotropic)** |
| 要素削除 | **有効** (eps=0.15) |
| クリアランス | ゼロ（対策済み） |
| 計算時間目標 | < 4時間 |
| スレッド数 | 12 |

---

## Phase 1: INP → OpenRadioss 変換

### 1.1 変換対象

| Calculix | OpenRadioss | 備考 |
|----------|-------------|------|
| *Node | /NODE | 直接変換 |
| C3D4要素 | /TETRA4 or /BRICK | Isolid=14推奨 |
| *Material S185 | /MAT/LAW1 | 剛体的扱い |
| *Material 1060_Alloy | /MAT/LAW2 + /FAIL/BIQUAD | 破壊基準付き |
| *Contact pair | /INTER/TYPE7 | Idel=1 |
| *Dynamic | /RUN + Engine設定 | 20-50ms |

### 1.2 材料定義（コピー可）

```plaintext
#---1----|----2----|----3----|----4----|----5----|----6----|----7----|----8----|----9----|---10----|
/MAT/LAW1/1
S185_Steel_Rigid
#              RHO_I
          7.8E-09
#                  E                  NU
           210000.0                0.28
#---1----|----2----|----3----|----4----|----5----|----6----|----7----|----8----|----9----|---10----|
/MAT/LAW2/2
1060_Alloy_Plastic
#              RHO_I
          2.7E-09
#                  E                  NU
            69000.0                0.33
#                  a                   b                   n           EPS_p_max               c
              110.0               150.0                0.20                 0.0                0.0
#---1----|----2----|----3----|----4----|----5----|----6----|----7----|----8----|----9----|---10----|
/FAIL/BIQUAD/1
Aggressive_Element_Deletion
#  Ifail_sh   Ifail_so
         1          1
#          Eps_p_max           Eps_t_max           Eps_m_max               d_max
              0.15                0.20                0.30                 0.0
#     Dadv      Nmax
         1         1
```

### 1.3 接触定義

```plaintext
/INTER/TYPE7/1
Punch_Material_Contact
#   Slave_ID  Master_ID       Istf       Ithe       Igap       Ibag       Idel      Icurv
         101        102          4          0          2          0          1          0
#               Fric            Gap_min            Gapmax            Tstart             Tstop
               0.10              0.001              10.0               0.0             1E30
#              Stfac             Fpenmax              I_BC          Iform
              100.0                 0.0                 0              0
```

### 1.4 パンチ速度（ランプ付き）

```plaintext
/FUNCT/1
Punch_Velocity_Ramp
#                  X                   Y
                 0.0                 0.0
              0.001               333.0
               0.05               333.0

/IMPVEL/1
Punch_Imposed_Velocity
#   Skew_ID        Dir      Isens     Gnod_ID    Icoor     Iframe
         0          Z          0    punch_grp        0          0
#             Scale_x             Scale_y              Fct_ID
                 1.0                 1.0                   1
```

### 1.5 Mass Scaling

```plaintext
/DT/NODA/CST
#               Tmin            Tscale
           5.0E-08               0.9
```

---

## Phase 2: 実行コマンド

### 2.1 Starter実行

```powershell
cd C:\Users\mhn15\dynamic_20251218
OpenRadioss_Starter.exe Punch_Die_0000.rad
```

### 2.2 Engine実行

```powershell
$env:OMP_NUM_THREADS = 12
$env:OMP_STACKSIZE = "64M"
OpenRadioss_Engine.exe -np 12 Punch_Die_0001.rad
```

---

## Phase 3: 確認ポイント

| タイミング | 確認事項 |
|------------|----------|
| Starter後 | エラーなし、要素数確認 |
| Engine 1ms | 接触検出、速度適用 |
| Engine 5ms | 要素削除開始 |
| Engine 20ms | 完了、エネルギーバランス |

---

## Phase 4: ParaView可視化

1. `rad2vtk_robust.py` でA*ファイルをVTK変換
2. ParaViewでVTKシリーズ読込
3. フィルター: WarpByVector, Threshold(塑性ひずみ)
4. アニメーション作成

---

## トラブルシューティング

| 問題 | 対処 |
|------|------|
| NEGATIVE VOLUME | eps_p_maxを0.10に下げる |
| MASS ERROR | Tminを1E-07に緩和 |
| 接触不安定 | stfacを200に増加 |
| 要素削除されない | Nmaxを確認、ログ確認 |
