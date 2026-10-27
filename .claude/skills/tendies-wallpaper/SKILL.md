---
name: tendies-wallpaper
description: 製作與修改 iOS AirCard / Nugget「.tendies」動態鎖定畫面桌布的完整流程與技巧庫，涵蓋 ParameterizedCA、陀螺儀、景深、iOS 27 Clownfish 修復，以及 iPhone Duo 摺疊機的三種姿態。適用情境：做新的 tendies 桌布、修改 build_*.py 或 tendies_kit.py、分析別人的 .tendies 參考、討論 CAML 動畫或 PosterBoard 行為。Use for any .tendies / CAML / PosterBoard wallpaper work.
---

# Tendies 桌布製作手冊

這份 skill 收錄三個來源的知識：
- 我們做 Manosaba（Hiro／Ema）與珠洲島有栖時，在實機上驗證過的作法。
- 使用者提供的約 50 份參考 tendies，全部拆解分析過。
- 使用者的偏好與回饋。

做新桌布時，先讀完本檔，再依需要查 `references/`：

| 檔案 | 什麼時候讀 |
|---|---|
| `references/techniques.md` | 構思與實作時。技巧庫：動態、角色生命感、光影、粒子、狀態劇本、素材管線、效能；每項都標了驗證狀態 |
| `references/caml-syntax.md` | 要寫 kit 尚未支援的 CAML（混合模式、濾鏡、多動畫、逐幀），或要讀懂別人的 CAML 時 |
| `references/reference-catalog.md` | 想看參考作品怎麼做某件事，或要分析新的參考檔時。內有每份參考的重點和分析腳本的用法 |

驗證狀態標記（所有 references 檔通用）：
- ✅ 我們的 ParameterizedCA 管線在 iPhone 實機驗證過。
- 🔶 參考作品實際在用，但它們走 CAPlayground 的 LayeredAnimation 格式。圖層層級的技巧通常可以直接搬，第一次用在我們的管線時要請使用者實機確認。
- ⚠️ 推測或未驗證。

**適用裝置**：版面常數（`VIEWS`、`CLOCK`、`PRODUCT_TYPES`）是依 iPhone Duo（摺疊機：外螢幕 466×678 pt，內螢幕 626×890 pt，可直可橫）實測的。單螢幕 iPhone 的做法：
- 只保留一個 view。
- `S` 可以改成符合螢幕比例的長方形。
- 用自己的鎖定畫面截圖重量時鐘位置。
- 把機型加進 `PRODUCT_TYPES`。

---

## 1. 硬規則（違反就會壞，或使用者明確不要）

**格式**
- 一律用 **ParameterizedCA**：單一 CA bundle，root 的 `<style>` 裡放 `wallpaperParallaxGroups`（陀螺儀）和 `wallpaperPropertyGroups`（Lock／Home／Sleep 數值）。
- LayeredAnimation（Background／Floating／Foreground 三個 .ca）在 iOS 27 會失去 gyro，不要用。參考作品幾乎都是這個格式，只能學它的圖層技巧。
- **iOS 27 景深加 gyro 修復**已內建在 `tendies_kit.package()`：
  - bundle 名為 `<id>.Clownfish_Gyro.ca`。
  - 寫入兩份 rendering configuration archive。
  - identity 由內容雜湊產生。
  - productTypes 為 iPhone19,4 與 iPhone18,4。
- 匯入一定要用 **AirCard Depth Test**。原版 AirCard 會丟掉隱藏的 options plist，景深就失效。

**座標與裝置**
- root 是 `S×S = 890×890 pt` 的正方形，`geometryFlipped=0`，y 軸向上。
- PosterBoard 會把 root 以 aspect-fill 置中，三種姿態各顯示一塊中央裁切區域：
  - 闔上直向：x 139–751
  - 展開直向：x 132–758
  - 展開橫向：y 132–758
- **安全區是 x 139–751、y 132–758**，重要內容都放在裡面。
- 使用者的時鐘是實測值，存在 `tendies_kit.CLOCK`，時鐘底部約在：闔上 root y≈434、展開直向 y≈561、展開橫向 y≈479。時鐘可以被拉長。
- 鎖定時角色的頭頂約在 `CHAR_TOP ≈ 556`，放在 FLOATING，讓景深把時鐘蓋住。
- **AOD（Sleep）沒有景深**，時鐘永遠在最上層，所以 Sleep 的主體必須整個放在時鐘下方（頂端 ≤ 約 410–415）。

**圖層與狀態**
- 圖層名稱必須全域唯一（`build_caml` 會 assert），因為 property／parallax group 是用名字找圖層。
- **同一圖層、同一 keyPath 上，動畫會蓋掉狀態值。** 狀態（`.state`）和動畫（`.animate`）要分開放在巢狀的不同圖層。慣例是外層 Stage 負責狀態，往內依序是 Parallax、Float、Sway 等動畫層。
- kit 每個圖層只輸出一個動畫，需要多軸運動就巢狀多層。參考作品用 `<p key="animation-1">` 在同一圖層掛多個動畫（見 caml-syntax.md），我們尚未驗證。
- 狀態值依解鎖進度**線性內插**，沒有彈簧，也沒有 easing。

**品質**
- 圖片圖層 ≥ 3 px/pt（@3x），用 premultiplied Lanczos（`resize_premul`）縮放，PNG 無損。
- 純平滑的程序生成圖（漸層、光束）可以放寬到 ≥ 1.5 px/pt。
- 素材解析度不夠時，先找更好的來源（遊戲資料、官網），最後才用 Real-ESRGAN x4plus-anime 放大，並告訴使用者哪些素材低於 @3x。

**設計原則（來自實際使用者回饋）**
- **原創、跟角色背景故事掛鉤。** 不要做成換皮模板。例如「夜空＋月亮＋泡泡」被評為「太像模板桌布」。場景要從角色的設定、台詞、口頭禪、喜好物長出來。
- **三個狀態要在同一個光照世界裡。** 各狀態平均亮度差不要太大，home／lock 的線性亮度比 ≤ 約 1.5（`state_luminance` 會印出來）。
- **轉場要是場景裡的事件，不要只是淡入淡出。** 不要閃白轉場，使用者覺得「不和諧」。
- **入場要符合物理。** 角色從幕後出來，就讓她在幕後被布景遮住，再被拉開的布景露出來，不要淡入疊在布景上面。
- **角色背後的布景不要有像她身體或服裝一部分的形狀與顏色。** 有栖背後的波浪色帶曾被誤認成尾巴。
- **參考作品只學技巧，不抄構圖。** 「不需要因為我給你參考你就強配自己去照抄他的設計」。

---

## 2. 工作流程

1. **研究角色**：讀官方設定、台詞、卡面、代表曲。ONGEKI 的角色資料在遊戲 dump 的 `GameData/A000/chara/*/Chara.xml` 和 `card/*/Card.xml`（見 techniques.md §G1）。把可用的 motif 列成清單，例如有栖的浣熊布偶裝、漢堡、繪本裡的熊、「じゃーん。驚いた？」。
2. **寫三狀態劇本**：決定 Lock、Home、Sleep 各自是「什麼場面」，以及 Lock→Home 解鎖時發生的「事件」。範例是有栖小劇場：
   - Lock：合上的幕前，一隻可疑的布偶裝。
   - 解鎖：布偶裝爆成果凍星，幕拉開，有栖本人在幕後。
   - Sleep：謝幕後在幕前午睡。

   常見的狀態模式見 `techniques.md` §A。
3. **找素材**：先用遊戲資料或官方原圖；放大後存進 `sources/<角色>/`。程序生成的布景（布幕、光束、地板等）在建置腳本裡畫，確保解析度與一致性。
4. **寫建置腳本** `build_<name>.py`，骨架如下：
   ```python
   from tendies_kit import *   # Layer, group, image_layer, asset, S, C, PPT, VIEWS, CLOCK, package, make_previews...
   OUT_NAME, BUILD, PREVIEW = "Name-Fold", os.path.join(HERE, "build_x"), os.path.join(HERE, "preview_x")
   rng = random.Random(<角色生日之類的固定種子>)     # 固定種子，重建結果穩定

   def build_background():            # 時鐘下方
       root_bg = group("BACKGROUND"); root_bg.id = "background"; ...; return root_bg
   def build_floating():              # 時鐘上方（景深）
       root_fl = group("FLOATING"); root_fl.id = "floating"; ...; return root_fl
   def build_root():                  # 也給臨時檢查腳本用
       return Layer("Root Layer", S, S, C, C).add(build_background(), build_floating())
   def main():
       root = build_root(); caml = build_caml(root)
       package(caml, os.path.join(HERE, f"{OUT_NAME}.tendies"), BUILD)
       make_previews(root, PREVIEW, {"lock": "...", "home": "...", "sleep": "..."})
   ```
   新增元素時，要保持既有的 `rng` 消耗順序，不然會把整個場景的隨機佈局洗掉。有栖的 `build_root` 就是為此，先建好再把圖層插進背景。
5. **預覽與自動檢查**：`make_previews` 會輸出以下檔案，並印出各狀態亮度。逐一打開看：
   - `states_x_postures.png`：狀態 × 姿態，含陀螺儀極限傾斜。
   - `animation_preview.gif`
   - `transition_lock_home.png`、`transition_lock_sleep.png`：**轉場中間幀**。結束狀態的預覽看不出中途穿幫。
6. **驗證封包**（每次建置都做）：
   - 層數、唯一名稱、資源數量、解碼後記憶體大小（建置會印出來，一般控制在 ~80 MB 以內）。
   - 若有使用者的修復腳本，可以拿來當 oracle：結構被接受，且 CA 資源逐位元組相同。
   - 遮擋類技巧要做差分檢查，寫法見 techniques.md §E。
7. **交付**：給使用者 `.tendies` 路徑、identity、預覽路徑，說明哪些部分還沒實機驗證，請他用 AirCard Depth Test 實測。

## 3. 交付前檢查清單

- [ ] 三種姿態的安全區內，重要內容都沒被裁掉；陀螺儀極限傾斜時邊緣不露底。
- [ ] Lock：角色頭部在時鐘下緣附近，放在 FLOATING；把時鐘拉長時仍正常。
- [ ] Sleep：主體完全在時鐘下方（沒有景深）；畫面夠暗夠簡潔，適合 AOD。
- [ ] Home：給 App 圖示留呼吸空間。主體不必很大，但要有完整的場面感。
- [ ] 轉場中間幀：沒有雙重曝光、沒有「上半身被擋、腳露在前面」之類的穿幫、沒有空場。
- [ ] 各狀態亮度比 ≤ ~1.5，而且是同一個光照世界。
- [ ] 素材 ≥ @3x，沒有 Real-ESRGAN 留下的 alpha 雜訊（用 `clean_alpha`），卡面裁切的邊緣有淡出處理。
- [ ] 角色背後沒有會被誤認成身體一部分的形狀。
- [ ] 回報時誠實列出未經實機驗證的新技巧。

## 4. 技巧速查（細節在 `references/techniques.md`）

| 類別 | 技巧 |
|---|---|
| A 狀態劇本 | 卡面切入互換 ✅、布幕揭幕 ✅、AOD 午睡 ✅、背景依狀態平移 ✅、依狀態染色 ✅、主畫面乾淨化 🔶、Q 版平鋪圖樣當主畫面 🔶、AOD 只留 logo／標語 🔶、標題滑出 🔶、角色往兩側讓開 🔶、深淺色模式狀態 ⚠️ |
| B 角色生命感 | 漂浮與呼吸 ✅、腳底錨點搖擺 ✅、眨眼／單眼眨眼差分 🔶、嘴型時間軸 🔶、姿勢切換 🔶、部件綁骨 🔶、上半身錨點晃動 🔶 |
| C 環境動態 | 吊線道具鐘擺 ✅、紙花下落 ✅、果凍星漂浮 ✅、Zzz 上升 ✅、光塵粒子 ✅、羽毛 Z 字路徑 🔶、邊緣矩形發射器 🔶、疊層翻頁動畫 🔶、`contents` 逐幀 🔶、窗燈閃爍 🔶 |
| D 光影 | 聚光燈與光束擺動 ✅、腳下光圈 ✅、輪廓光／氛圍光（alpha_glow）✅、暗角 ✅、睡眠調暗 ✅、混合模式（lighten／overlay／multiply／saturation）🔶、高斯模糊陰影 🔶、閃電腳本 🔶 |
| E 景深陀螺儀 | 前後景分層與 parallax 量 ✅、布景遮擋揭露 ✅、巢狀透明度平方淡出 ✅、從腳底縮放彈出 ✅ |
| F 版面 | 正方形 root 適配多姿態 ✅（參考作品的 iPad 版也用正方形畫布 🔶）、時鐘避讓 ✅ |
| G 素材 | 遊戲資料裁切 ✅、ESRGAN 放大 ✅、trim／clean_alpha／邊緣與圓形淡出 ✅、程序生成布景 ✅ |
| H 效能／變體 | 記憶體預算、效能版（降 PPT）🔶、無 AOD 版 🔶、無動畫版 🔶 |
