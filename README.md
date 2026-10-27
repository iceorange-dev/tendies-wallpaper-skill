# tendies-wallpaper-skill

用 Python 產生 iOS 動態鎖定畫面桌布（`.tendies`，給 Nugget／AirCard 匯入），並附一份給 Claude Code 用的技巧手冊（skill）。

*A Python engine and a Claude Code skill for building animated iOS lock-screen wallpapers (`.tendies`): ParameterizedCA with gyro parallax, the depth effect (iOS 27 "Clownfish" fix built in), Lock / Home / Sleep (AOD) states, and a layout that works on the iPhone Duo foldable in all three postures.*

## 特色

- **ParameterizedCA**：單一 CA bundle，用 `wallpaperParallaxGroups` 做陀螺儀視差，用 `wallpaperPropertyGroups` 定義 Lock／Home／Sleep 三種狀態。
- **iOS 27 景深＋陀螺儀修復已內建**：bundle 命名為 `<id>.Clownfish_Gyro.ca`，並寫入 rendering configuration；identity 由內容雜湊產生。產出的檔案用 **AirCard Depth Test** 匯入。
- **摺疊機版面**：890×890 pt 的正方形 root 會被 PosterBoard 以 aspect-fill 置中，闔上直向、展開直向、展開橫向都能用。時鐘位置依實機截圖量測。
- **場景圖 API**：`Layer`、`group`、`image_layer`、`.animate()`、`.state()`、`.parallax`、粒子發射器。
- **預覽與檢查**：狀態×姿態總覽、動畫 GIF、轉場中間幀分解圖、各狀態亮度量測。
- **技巧手冊**：從約 50 份參考作品和兩張實機驗證過的桌布整理出約 50 項技巧，每項都標了驗證狀態（✅ 實機驗證／🔶 參考作品在用／⚠️ 未驗證）。

## 內容

```
.claude/skills/tendies-wallpaper/   Claude Code skill
  SKILL.md                          硬規則、工作流程、交付前檢查清單、技巧索引
  references/techniques.md          技巧庫（附 kit 寫法與出處）
  references/caml-syntax.md         tendies 封包與 CAML 語法速查
  references/reference-catalog.md   參考作品分析摘要（參考檔本身不在本 repo）
  scripts/ref_*.py                  參考 .tendies 的唯讀分析與靜態渲染工具
tendies_kit.py                      引擎：場景圖 → CAML → 打包，含預覽渲染器與轉場／亮度檢查
tendies_art.py                      共用的程序美術與素材處理（光暈、光束、淡出、切 sprite）
ongeki.py                           從 ONGEKI 解包資料讀卡面、劇情立繪（含表情臉）、章節背景
template/                           打包用的 PosterKit metadata 範本
build_tendies.py                    範例一：Manosaba（Hiro／Ema 切入、法庭、光塵）
build_arisu.py                      範例二：ONGEKI 珠洲島有栖「小劇場」（布幕揭幕、吊線道具、AOD 午睡）
build_chinatsu.py                   範例三：ONGEKI 日向千夏「學園中庭」（官方立繪眨眼、揮手、背景對焦、夜晚 AOD）
```

建置時產生的檔案都放在 `out/`（`<name>.tendies`、`out/preview/<name>/`、`out/build/<name>/`），不進 repo。本機工具（Real-ESRGAN 等）放在 `tools/`，同樣不進 repo。

## 使用方式

需求：Python 3.10 以上，`pip install -r requirements.txt`。

預覽用到兩個 Windows 字型（`bahnschrift.ttf`、`msjh.ttc`），在其他系統上請修改 `tendies_kit.py` 開頭的 `CLOCK_FONT`／`LABEL_FONT`。

1. 照 `SKILL.md` 的骨架寫一支 `build_<name>.py`，或從三支範例改起。
2. 執行 `python build_<name>.py`，會產生 `out/<name>.tendies` 和預覽資料夾 `out/preview/<name>/`（加 `--no-preview` 可跳過預覽）。
3. 打開預覽資料夾，檢查以下檔案和終端機印出的亮度比：
   - `states_x_postures.png`
   - `transition_lock_home.png`
   - `animation_preview.gif`
4. 用 **AirCard Depth Test** 匯入（原版 AirCard 會丟掉隱藏的 options plist，景深就會失效）。

### 搭配 Claude Code

用 Claude Code 打開本 repo，就會自動載入 `.claude/skills/tendies-wallpaper` 這個 skill；也可以輸入 `/tendies-wallpaper` 手動叫出。想在所有專案都能用的話，把這個資料夾複製到 `~/.claude/skills/`。

### 其他機型

`VIEWS`、`CLOCK`、`PRODUCT_TYPES` 是依 iPhone Duo 實測的。單螢幕 iPhone 只需保留一個 view，並用自己的截圖重量時鐘位置，詳見 `SKILL.md`。

## 範例素材

範例會讀取**你自己合法取得**的遊戲素材：
- `build_tendies.py`：遊戲解包資料夾，路徑用環境變數 `MANOSABA_ASSETS` 指定。
- `build_arisu.py`、`build_chinatsu.py`：`sources/<角色>/` 底下放卡面原圖，或用 Real-ESRGAN 放大後的圖；`ongeki.py` 的解包路徑用環境變數 `ONGEKI_EXPORT` 指定。

本 repo **不包含**任何遊戲圖片、建好的 `.tendies`，或其他創作者的桌布。各遊戲與角色的著作權屬於其權利人；技巧手冊只記錄從參考作品學到的做法，不含它們的內容。

## 授權

[MIT](LICENSE)
