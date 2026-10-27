# 參考作品目錄

**規則**：參考作品只用來學技巧，不抄構圖。這是使用者明確的要求。

這批參考在 2026-10-28 全部拆解過。除了 Manosaba-Gyro 之外都是 CAPlayground 匯出的 LayeredAnimation（見 caml-syntax.md §1.2）。

## 1. 參考來源

參考檔是其他創作者的作品，**不包含在本 repo 裡**。本目錄只記錄從中學到的技巧。

| 來源 | 內容 |
|---|---|
| ONGEKI 系列合集（20 份 `.tendies.zip`） | Akane-the-Angel、Arisu-DDA、Arisu-Radiance、Freedom Dive、Selector、Vocal Party、Territory-Battle、Parad_ox、Horoscope Express、XeleidScope 等 |
| 百度網盤系列（本機放在 `references/baidu/`，已加入 .gitignore） | 25 份 tendies（BanG Dream、Girls Band Cry、孤獨搖滾、超かぐや姫、FX-Fighter），附預覽 PNG／MP4 和版本說明 txt |
| 一份實機驗證過的 CAPlayground gyro 匯出（ParameterizedCA） | 它的 PosterKit metadata 就是 `template/` 的來源 |

## 2. ONGEKI 系列

整個系列的共同套路：
- **Lock**：遊戲背景加卡面角色，配眨眼和單眼眨眼的差分。
- **Home**：角色整組移出畫面，只留背景和粒子。
- **Sleep**：角色同樣移走。
- 背景通常用 AniScale 放大。

| 作品 | 畫布 | 值得學的技巧 |
|---|---|---|
| Akane-the-Angel V1.0／NoLights | 1216×2160 | 星形燈籠吊鍊擺動（錨點在上）；羽毛沿 19–44 點的 Z 字路徑緩慢下落（23–38 秒）；Lights 版多了 4 層斜射光束 |
| Arisu-DDA V1.1 | 1216×2160 | 星燈吊鍊；四個角落的 overlay 漏光從角落錨點旋轉擺動；畫布外的點發射器偶爾飄入羽毛或光點（birthRate 0.05–0.2、lifetime 50）；30% 的整張色調疊層 |
| Arisu-Radiance V1.0 | 1216×2160 | **直書歌名加作曲者的標題圖**（overlay），Unlock 時往右滑出、Sleep 時往下滑出 |
| Freedom Dive V1.0 | 1216×2160 | 天空和太陽光芒；lighten 的中央放射發射器；**嘴型時間軸**（1580 個值、120 秒） |
| Haruna／Rio／Akari Vocal Party | 1216×2160 | 最精簡的範本（約 11 層）；`bgL` 是 lighten 光層的呼吸（0→0.45、4 秒） |
| Selector V1.2／Compressed-Performance／V1.4-iPadOS | 2000×3840；iPad 5435² | 平面設計風；**角色拆成本體加 Arm1／Arm2 做姿勢切換**；同一層掛三個互質週期的動畫；高斯模糊加 multiply 的跟隨陰影；上緣矩形發射器下星雨（additive、speed 3）；用 bounds 做裝飾脈動；Sleep 是極簡的大圓 |
| Territory-Battle V1.0 | 2000×3840 | 漂浮方塊（巢狀兩層，x／y 週期不同）；`shake` 繞 (0.5, 0.35) 晃動；overlay 光層脈動；圓環 |
| Parad_ox V1.1 | 1900×3840 | **閃電腳本**：black、flash、Light 三層各一條 369 值、15 秒的時間軸；Home 只剩雷雨背景 |
| Tsumugi-Supersonic-Generation | 1216×2160 | 兩側畫布外的點發射器；圓環舞台背景 |
| TSUBAKI V1.0 | 1216×2160 | 大標題字用 saturation 混合；multiply 色層；發射器用 outline 模式（35×350 的細長形） |
| XXLB（Majdata） | 1216×2160 | 三個狀態的構圖完全不同：Lock 角色從上方探頭、Home 是 logo 加小 Q 版、Sleep 是大 Q 版 |
| Destr0yer V1.0 | 1216×2160 | 極簡黑底；Unlock 時角色的 `bounds` 縮成 0，標題字放大；彈簧透明度轉場 |
| enchanted love v1.0 | 1216×2160 | 扁平向量風，總共只有 1.8 MB |
| Horoscope Express V1.0 | 7680² | 像素風；**疊層翻頁動畫**（18 層 × 540 值、3 秒）；窗燈閃爍；82 層、57 MB |
| XeleidScope | iPad 810w-1080h@2x，`appearanceAware`，family Chip | **contents 逐幀**：390 張 JPG、6.5 秒、292 MB。反面教材：太重 |

## 3. 百度系列（BanG Dream 等，`references/baidu/`）

同一位作者，三個狀態的套路固定：
- **Lock**：團體主視覺加樂團 logo 或橫幅。
- **Home**：換成 **Q 版頭像平鋪圖樣**，或換另一組角色。
- **Sleep（AOD）**：純色底，加 logo、手寫標語或線稿。

狀態之間的轉場一律用彈簧透明度動畫，或改位置與大小。版本說明（`不同版本的区别….txt`，全部內容相同）：
- `aod`：有息屏版，適用 14 Pro 以後的 Pro 機型和 17 全系列。若某張桌布只提供 aod 版，代表 AOD 和非 AOD 兩種情況都適配了。
- `without aod`：不支援或不開 AOD 時選這版，可避免動畫 bug。實際差異只在 Sleep 狀態的位置與大小。
- `with／without animation`：有沒有循環動畫。差異只是拿掉 BG 的旋轉裝飾。
- `better performance`：降解析度，例如 7680→2456 px、26→6 MB；記憶體 < 8 GB 的機型建議用這版。
- `fix`：修過動畫 bug 的版本。

| 作品 | 值得學的技巧 |
|---|---|
| CPK-aod（超かぐや姫） | 角色依狀態左右互換或讓開；logo 在 Unlock 時滑出、在 Sleep 時縮小放進圓框；道具依狀態旋轉 ±90°；Sleep 用鳥居線稿 |
| FX-Fighter | 「視窗 UI」主題；看板用 keyTimes 停頓再滑動（20 秒）；蠟燭橫移（50 秒）；Sleep 換成另一張暗色全幅插畫 |
| fix-aod／fix-without-aod／fix-better-performance（GBC） | Lock 團體、Home Q 版、Sleep 手寫標語加 logo（紅底）；同一張桌布的 4961 px 版與 720 px 版對照 |
| gbc-v2-aod、gbc-aod-bp | 漫畫格拼貼 |
| GBC-iPad-ver | 3176² 正方形畫布；**深淺色兩套狀態**（6 個狀態） |
| ppp／rosalia／ras（各有 aod／bp 版） | Home 用 Q 版頭像平鋪；Sleep 只放 logo；rosalia 有 `colorHueRotate`（角度 0） |
| morfonica-final／fix、mygo-ipad-v4（11／13 吋）、PPP-IPAD-ver1／2 | iPad 用正方形畫布；Home 用平鋪圖樣 |
| bocchi-in-the-rock-aod | 色塊拼貼；Sleep 用線稿加標題（粉底） |
| with／without AOD × with／without desktop animation（MyGO） | 四個變體並列，正好用來看「AOD 版改了什麼」「無動畫版拿掉了什麼」 |

## 4. 其他

- `template/`：取自一份實機驗證過的 CAPlayground gyro 匯出（ParameterizedCA）。只保留 PosterKit metadata，去掉了它的 `wallpaper.ca`。`package()` 每次打包都會複製這份範本，只替換 CA bundle 和 identity 相關欄位。
- `fix_caplayground_depth_gyro.py`：社群流傳的 iOS 27 景深＋gyro 修復腳本（不包含在本 repo）。kit 已內建同樣的修復；手邊有這支腳本的話，可以拿來當 oracle，交叉驗證輸出。

## 5. 分析新參考檔

使用者給新的 .tendies 時，用 `scripts/` 裡的三支腳本。它們只在記憶體裡讀 zip，不解壓、不執行參考檔中的任何東西。一律用 `python -I` 執行，並把輸出寫到暫存資料夾：

```bash
# 1) 普查：每份一行摘要，加上全體的特徵統計（圖層類型、動畫 keyPath、濾鏡、發射器…）
python -I scripts/ref_scan.py <OUT_DIR> <檔案.tendies | 外層.zip | 資料夾> ...
#    另外輸出 OUT_DIR/<label>.json（plist、圖片尺寸、各 bundle 統計）和 OUT_DIR/<label>/*.caml 副本

# 2) 技巧抽取：每個 keyPath 的實例、眨眼／閃爍類的密集值列表、混合模式、濾鏡、發射器、狀態值、轉場
python -I scripts/ref_techniques.py <OUT_DIR> > report.txt

# 3) 靜態渲染：每份一列，依序是 Locked | Unlock | Sleep（不跑動畫，發射器畫成紅圈，混合模式近似）
python -I scripts/ref_render.py sheet.png 150 a.tendies "outer.zip::inner.tendies.zip" ...
```

注意事項：
- `ref_render.py` 的字型寫死為 `C:\Windows\Fonts\msjh.ttc`。
- 靜態渲染會讓眨眼差分層一直顯示，所以角色看起來都在單眼眨眼。這是正常的。
- 要比較兩個變體（例如 aod 與 without-aod），用 `difflib` 對兩份 CAML 副本做 diff，先去掉 `id` 和 `targetId` 再比。
