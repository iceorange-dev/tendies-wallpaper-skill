# 技巧庫

狀態標記：
- ✅ 我們的 ParameterizedCA 管線實機驗證過。
- 🔶 參考作品在用（LayeredAnimation），圖層技巧可搬，但我們尚未實機驗證。
- ⚠️ 推測或未驗證。

程式碼都是 `tendies_kit` 的寫法，座標 y 軸向上，root 為 890×890 pt，`C = 445`。
出處欄的檔名請對照 `reference-catalog.md`。
`build_tendies.py` 是 Manosaba（Duo 分螢幕格式、零循環動畫的範例，座標是裝置像素，見 §F4），`build_arisu.py` 是有栖小劇場。

---

## A. 狀態劇本（Lock／Home／Sleep 的編排）

狀態值依解鎖進度**線性內插**。所以「轉場」等於兩組數值之間的連續滑動：使用者手指拖到一半，畫面就停在一半。設計時要確定每個中間比例都好看，用 `transition_strip` 檢查。

**從主畫面進 AOD 會先經過 Lock 的數值**（實機觀察 ✅）。在主畫面按側邊鍵，畫面會先回到鎖定，再進 AOD。所以只在 Lock 出現、Home 和 Sleep 都藏起來的東西，走這條路時會冒出來又馬上消失，看起來像跳了一下（GBC 移植的人物就是這樣）。狀態值只由「目前在哪」決定，不管從哪個方向來，所以這個現象沒辦法完全避免。兩種處理方式：
- 讓它在 Sleep 也留著。
- 用 E4 的巢狀透明度 `chained(name, (1, 0, 0), 3, ...)`，讓它只在接近 Lock 時才看得見，冒出來的過程就縮成一閃 ✅（GBC 移植，使用者實機確認可接受）。

### A1 卡面切入互換 ✅（`build_tendies.py`）
Lock 是角色甲，Home 是角色乙。兩人隨滑動交錯通過：
```python
hiro = group("Hiro Stage").state("position.x", C, C - OFF, C).state("opacity", 1.0, 0.0, 0.0)
ema  = group("Ema Stage", x=C + OFF, opacity=0.0).state("position.x", C + OFF, C, C + OFF).state("opacity", 0.0, 1.0, 0.0)
```
只用滑動的話，中段會空場，所以一定要同時交叉淡化（OFF = 520）。不要用閃白剪影，使用者不喜歡。

### A2 布景揭幕 ✅（`build_arisu.py`）
Home 的主角**放在 BACKGROUND、布幕之下**。Home 沒有時鐘，所以不需要景深層。
- 布幕左右兩片各有一個 Track 圖層，負責 `position.x` 的狀態（關 ↔ 開）。Track 裡面的 panel 再做輕微的旋轉擺動。
- Lock 時主角就**不透明地站在合上的幕後**，所以揭幕是俐落的露出，不是淡入。
- 主角的腳必須站在幕的下襬**後方**（`SHOOTER_FEET > CURTAIN_HEM`）。否則幕擋住上半身、腳卻露在前面，會穿幫。
- 要做遮擋差分檢查（§E3），確認沒有從流蘇縫隙透出來。
- 留在 FLOATING 的小物件（如前排果凍星）會疊在幕前，像是溢出舞台，可以保留做層次。

### A3 前景小角色「變身」退場 ✅（有栖布偶裝）
Lock 主角放在 FLOATING（時鐘前），Home 時消失：
- 外層 Stage 的狀態：`opacity 1→0`，加上 `transform.scale.xy 1→1.22`，往外「啵」一下。
- 內層再包一個同樣 `1→0` 的 Fade 群組。兩層透明度相乘成 (1-u)²，所以在幕拉開前就大致消失，避免和 Home 主角疊成雙重曝光（§E4）。
- 配合從它中心飛出的爆散星星：每顆星的 `position.x/y` 狀態從布偶中心到外圍目標點，`opacity` 為 0→0.85。

### A4 Sleep／AOD 專屬畫面 ✅
AOD 沒有景深，時鐘在最上層，所以主體要整個放在時鐘下方（頂端 ≤ 410）。
- **我們的做法**：同一個世界裡的「睡著」版本。有栖謝幕後在幕前午睡，Manosaba 是兩人並肩站。
  - 加 `Sleep Dim` 全畫面暗色層，`opacity` 狀態設為 `(0, 0, 0.3–0.42)`。
  - 背景熄掉一部分燈，保持畫面低亮度。
- **參考作品的做法** 🔶（百度 BanG Dream 系列幾乎都是這樣）：Sleep 換成「純色底＋樂團 logo／手寫標語／線稿」的極簡畫面，最省電也最乾淨。
- 換場方式：Sleep 主體 Stage 的 `opacity` 設為 `(0, 0, 1)`，`position.y` 從下方滑上來，即 `(C-120, C-120, C)`。

### A5 背景依狀態平移 ✅（`build_tendies.py`）
背景圖比畫面寬，外包一個 `BG Pan` 群組並設 `.state("position.x", C+140, C-140, C)`。Lock 和 Home 看到的是同一個場景的不同區域，平移本身就成了轉場的一部分。

### A6 依狀態的氛圍染色 ✅
每位角色各一層全畫面色層，用 `opacity` 狀態切換，例如 Hiro 紅、Ema 紫，各 0.24。

### A7 主畫面乾淨化 🔶（ONGEKI 參考幾乎都這樣做）
Unlock 時把整組角色移出畫布，例如 `position.y +2400`，主畫面只留背景與粒子，給 App 圖示空間。在我們的線性內插下，這會變成「隨手指滑走」。
不一定要照做：有栖的 Home 反而是主角登場。重點是 Home 要讓圖示好讀。

### A8 Home 換成 Q 版平鋪圖樣 🔶（ppp／rosalia／ras／morfonica／mygo）
Lock 放團體主視覺，Home 換成一整片 Q 版頭像平鋪的圖樣（像包裝紙），圖示放在上面也不亂。

### A9 標題／logo 的進出場 🔶
- Arisu-Radiance：直書歌名加作曲者的標題圖，Unlock 時往右滑出（x 930→2300），Sleep 時往下滑出。
- CPK：logo 在 Unlock 時往上滑出，Sleep 時移到畫面中段，並縮小放進圓框。
- Destr0yer：Unlock 時角色的 `bounds.size` 縮成 0，標題字放大，畫面只剩標題。

`bounds.size.*` 這個狀態 keyPath 在 ParameterizedCA 中 ⚠️ 未驗證。在我們的管線裡改用 `transform.scale.xy`（✅）。

### A12 招呼 → 飛撲，加背景對焦 ✅（`build_chinatsu.py`）
- Lock：劇情立繪站在原地揮手，放在 FLOATING，頭在時鐘下緣。
- Home：換成另一張官方卡面的飛撲姿勢，放大、貼近鏡頭。同時加一層預先模糊過的背景副本，狀態設為 `(0, 1, 0)`，看起來像鏡頭對焦到她身上；再從她起跳的位置爆出 ☆。
- 交接：Lock 立繪用三層巢狀淡出 `(1-u)³`，在飛撲圖淡入到一半前就大致消失，避免兩個姿勢疊成雙重曝光。
- 模糊副本要用 premultiplied 模糊，並取 `max(模糊後 alpha, 原 alpha)`，邊緣才不會露出清晰的原圖。
- 模糊圖只需要約 0.6 px/pt，很省記憶體。

### A13 同一場景的夜晚版當 AOD ✅（`build_chinatsu.py`）
- 天空：日景天空淡出，換成夜空漸層，再疊遊戲的星空貼圖（`glow_alpha`）。
- 建築與樹：各放一層調暗的副本，用 `tint(0.22–0.30, sat 0.7)` 加 `opacity` 狀態切換；夜景副本只需約 1.5 px/pt。
- 局部光源：例如鐘塔的燈，Sleep 時才亮。
- 角色：縮小到時鐘下方，整個人調成月光色，表情換成官方的 ^^ 笑眼（B_00），做法見 §B3 的「依狀態換表情」。
- 手：息屏時靜止舉著。息屏的更新率很低，揮手會一格一格跳。做法是把夜晚版的手放在揮動圖層外面當一個靜態圖層，揮動圖層用狀態在 Sleep 時隱藏。

### A10 角色往兩側讓開 🔶（CPK）
多個角色在 Lock 時集中，Unlock 時沿 `position.x` 往兩側分開，讓出中央。Sleep 則改排成小圖。

### A11 深淺色模式狀態 ⚠️（GBC-iPad）
狀態名稱用 `Locked Light`、`Locked Dark`、`Unlock Light` 之類，共 6 個狀態，亮暗各一套底色。這只見於 LayeredAnimation；ParameterizedCA 是否支援不明。

---

## T. 轉場即動態（待機零循環）✅（`build_tendies.py`，Manosaba Duo 版）

待機時畫面必須完全靜止（§H），所以所有動作都寫成狀態值，靠解鎖滑動和進出 AOD 的內插播出來。每個動作都是「Lock 值 → Home／Sleep 值」的線性內插；用巢狀圖層把幾個線性動作疊起來，轉場就會有層次。實機驗證 ✅，待機量到 4.0%。

- **兩段速滑出**：角色的 Stage 滑 `OFF = 520`，她的刀在裡面再多滑 `RUSH = 260`。刀比人快，看起來有前後景的深度。
  ```python
  rush = group("Hiro Blade Rush").state("position.x", C, C - RUSH, C)
  swing = Layer("Hiro Blade Swing", bw, bh, C + 6, 370).state("transform.rotation.z", 0, rad(18), rad(-10))
  ```
- **碎片炸開、飛入歸位**：每片碎片一個 `Fly` 群組（`position.x`、`position.y` 狀態），裡面再一個 `Spin`（`transform.rotation.z` 狀態）。離場的人，碎片從原位往外飛、邊飛邊轉；進場的人反過來，碎片從外面飛回原位。進 AOD 時碎片往下掉。
- **背景推近與後退**：`BG Lean` 的 `transform.scale.xy` 設成 (1.0, 1.06, 0.95)。解鎖時往前推，進 AOD 時往後退；喚醒（包括打開手機）就倒過來往前推。
- **從腳底沉下**：整組角色放在 `anchor=(0.5, 0)` 的 Zoom 層，縮放 (1.0, 0.94, 0.86)。進 AOD 時她像往後退進場景裡（E5）。
- **AOD 兩人升起**：`Duo Stage` 的 `position.y` 從低 170 pt 的位置升到原位，同時淡入。
- **AOD 不要只剩人物加全黑背景**：仁菜貼紙卡的第一版 AOD 這樣做，使用者說「感覺全黑有點怪怪的」。改成同一個場景的夜晚版（A13）：場景壓成深色但看得出輪廓，留少數配件調暗，人物比周圍亮一點。名字、數字這類文字貼紙使用者要求一起隱藏。
- **先淡出，後淡入**：離場的人多包一層同樣的透明度狀態，變成 (1-u)²（E4）。對方淡入到一半時，她已經幾乎看不見，雙重曝光的時間比較短。
- 光束、光點也跟著狀態微轉、微移，取代原本的循環擺動。
- **依序飛入、一個落定下一個才來** ✅（個人用的 `ports/build_fx_fighter.py`）：一個圖層的位置只能線性走完整段滑動，沒辦法「飛進來然後停住」。做法是每個東西放兩份：
  - 飛行的那份：位置狀態設成在滑動進度 a 時剛好在螢幕外、在 b 時剛好到位（之後它會繼續往前衝）。
  - 落定的那份：一直待在定位。
  - 在 b 交接：飛行那份的透明度設 `1 + K(b − u)`，落定那份設 `1 − K(b − u)`，K 取 150 左右。超過 1 和低於 0 的值會被截斷（E7），所以兩份各自只有「全顯示」和「全隱藏」兩種狀態。
  - 只在慢慢滑的時候看得出每一個；正常速度的滑動裡，每一個只出現幾十毫秒。
  - 先前兩種做法都被使用者退回：各自差一點距離一起滑入（「堆疊在一起划進來」），以及出發點拉遠讓它們先後進畫面但同時到位（「還是會遮擋」）。
- **單向的擺動不像揮手**：千夏的手原本是循環揮動。改成狀態後只能往一個方向轉，使用者說「只有往左揮，沒有左右揮」，最後決定手不要動。需要來回的動作，不要用單一的旋轉狀態硬做。
- **中途鼓起、兩端不變** ✅（個人用的 `ports/build_nina_card.py`）：有些東西在 Lock 和 Home 的位置、大小都一樣，只想讓它在滑動途中動一下。線性內插做不到「去了又回來」，兩層縮放相乘可以：
  ```python
  inner = Layer("X Settle", w, h, px * w, py * h, anchor=pivot).state("transform.scale.xy", 1.0, 1.0 / k, 1.0)
  outer = Layer("X Pop", w, h, x, y, anchor=pivot).state("transform.scale.xy", 1.0, k, 1.0).add(inner)
  ```
  - 兩層用同一個錨點。Lock 和 Home 相乘都是 1，中途是 (1 + (k−1)u)(1 − (1−1/k)u)，在 u = 0.5 最大。
  - 鼓起的幅度是 (1+k)²/4k − 1：k = 2 約 12%，k = 2.6 約 25%。
  - 錨點放在底邊，看起來像往上彈一下。進出 AOD 時兩層都是 1，不會動。

原本的循環動畫（漂浮、呼吸、閃爍、粒子）全部拿掉，改成不會動的版本。光點變成散布的靜態小圖，加上陀螺儀視差。

---

## B. 角色生命感

> ⚡ 本節都是循環動畫。待機時它們會讓系統每一幀都重畫，backboardd 多 26–30% CPU，手機會發燙（§H），所以現在預設禁用（`allow_loops=True` 才能建置）。要用之前先問使用者，或改寫成 §T 的轉場版本。

### B1 漂浮、搖擺、呼吸 ✅
固定的巢狀順序：`Stage（狀態）→ Parallax（CATransformLayer, gyro）→ Float（position.y）→ Sway（rotation.z）→ Body`。
```python
sway = Layer("X Sway", w, h, cx, cy).add(aura, body); sway.animate("transform.rotation.z", [rad(-1.2), rad(1.2)], 7.0)
float_ = group("X Float").add(sway); float_.animate("position.y", [C, C + 10], 5.2)
```
- 各層週期取互質，例如 7.0／5.2，動作就不會明顯重複。
- 呼吸效果：`transform.scale [1, 1.008]`，約 4.8 秒，錨點放在腳底 `anchor=(0.5, 0)`。

### B2 以腳底為支點搖擺＋小跳 ✅（有栖布偶裝）
```python
wobble = Layer("Mascot Wobble", w, h, C, FEET, anchor=(0.5, 0.0)); wobble.animate("transform.rotation.z", [rad(-3), rad(3)], 2.4)
hop = group("Mascot Hop").add(wobble)
hop.animate("position.y", [C, C, C + 7, C, C], 4.8, autoreverses=False, timing="linear", key_times=[0, .42, .5, .58, 1])
```
用 `key_times` 做「大部分時間靜止，偶爾跳一下」。地上的影子要放在 hop 群組外，跳起來時影子才留在原地。

### B3 眨眼／單眼眨眼 🔶（ONGEKI 參考全系列）
做法：準備和本體**同尺寸、同位置**的「閉眼」與「單眼閉」整張差分圖，疊在本體上，平常 `opacity` 為 0。
- **參考作品的寫法**：
  - `blink`：140 個值、2 秒、autoreverse，只有最後 6 個是 1，約每 4 秒眨一次、每次約 0.17 秒。
  - `wink`：58 個值、6 秒，最後 3 個是 1。
  - 差分層各自複製一份本體的位移動畫，讓動作同步。
- **我們的寫法**：把差分放進和本體**同一個 Sway 群組**，自動繼承動作，不必複製動畫；再用 `key_times` 取代一長串值：
  ```python
  blink = Layer("X Blink", w, h, w / 2, h / 2, img=k_blink, opacity=0.0)
  blink.animate("opacity", [0, 0, 1, 1, 0], 4.1, autoreverses=False, timing="linear", key_times=[0, .955, .96, .995, 1])
  sway.add(aura, body, blink)
  ```
  兩個眨眼層的週期取互質（例如 4.1 和 11.3 秒），偶爾會連眨兩下，比較自然。
- **素材**：必須有同姿勢的閉眼版本，例如遊戲的表情差分、立繪的 expression 圖層，或官方的差分圖。卡面通常沒有。不要自己硬畫眼皮，風險太高，要畫就先問使用者。

**官方劇情立繪自帶眨眼素材** ✅（`build_chinatsu.blink_patch`）：ONGEKI 的劇情立繪是「身體 + 表情臉」分開的。`Face_A_00` 是睜眼，`Face_A_01` 是同一張臉閉眼，正是遊戲自己用來眨眼的素材，對位資料在 `assetbundles/chara2d/ANM_Chara_*.prefab` 的 `PAT_EyeFace` 錨點。其他臉（B–F）有笑、生氣、哭等表情，也可以拿來做狀態切換。

- **陷阱（實機踩過）**：表情臉 sprite 在「睜眼的位置」是透明的，因為遊戲把它畫在沒有臉的身體上。把閉眼臉直接疊在已經合成睜眼的身體上，睜眼會從透明處透出來，變成閉眼線條畫在睜開的眼睛上。
- **正確做法**：
  1. 在原解析度分別合成「身體＋睜眼」和「身體＋閉眼」，用 `ongeki.story_sprite(chara, "A_00"/"A_01")`。
  2. 兩張用同樣的方式放大。
  3. 算出兩張有差異的像素：眼睛、睫毛，還有一點嘴。
  4. 把差異區域膨脹並羽化成遮罩，從閉眼版切出一塊**不透明的補丁**。
  5. 補丁疊在睜眼身體上，再用上面的 key_times 讓它短暫出現。
- **依狀態換表情**（例如息屏換成笑眼）：
  - 把「目標狀態的臉」直接合成在身體上，鎖定時再用「原本的臉」補丁蓋上。
  - 這塊補丁用 5 層巢狀淡出，即 (1-u)⁵（§E4）。舊表情在轉場一開始就幾乎消失，不會出現兩張臉各半的中間幀。
  - 如果反過來，讓新表情線性淡入蓋在舊的上面，一半時就會疊成兩張臉。
- **眨眼中間那格（A_01）不能當固定表情**：眼睛輕閉、嘴巴大開，停著看起來像眨眼眨到一半當機，配揮手更怪。這是使用者回饋。要長時間閉眼就用 ^^ 笑眼（B_00）。

### B4 嘴型時間軸 🔶（Freedom Dive `mouth`）
做法和眨眼相同，只是時間軸很長：1580 個值、120 秒，安排說話或唱歌的片段。改用 `key_times` 會精簡很多。

### B5 姿勢切換 🔶（Selector `Arm1`／`Arm2`）
準備兩張不同手勢的整張差分，互補地交替：一張的 `opacity` 是 1→0，另一張是 0→1，週期 10 秒、autoreverse。切換點要做得陡（用 `key_times` 讓切換在約 0.2 秒內完成），否則會看到兩隻手同時半透明。

### B6 部件綁骨 🔶（Selector、Territory-Battle）
把角色切成本體和手臂、頭、飾品等部件，分別以關節為 `anchorPoint` 旋轉。
- Territory 的 `shake` 用 `anchor (0.5, 0.35)`，旋轉 5°、週期 4 秒，等於繞上半身晃動。
- 切圖時，部件要在關節處預留重疊區，旋轉時才不會露縫。

**從手腕切出揮手** ✅（`build_chinatsu.wave_rig`）：
- 切線：沿袖口下方的深色袖子切一刀，切口用約 3 px 的高斯模糊做軟接縫。
- 補底：在身體那一側、袖口底下的袖子用 `cv2.inpaint` 延伸約 70 px，袖口轉動時才不會露出背景。
- 錨點：手的 Layer 錨點設在切線中點（手腕）。
- 動畫：用 `key_times` 做「靜止 → 揮三下（±7–9°）→ 靜止」，週期約 5.5 秒。
- 檢查：渲染 ±9° 兩個極端確認接縫。手的部件要同時放進白天版和夜晚版（月光色）。

### B7 單層多動畫 🔶
Selector 的 `object` 在同一層同時掛了三個動畫：`position.y`（3.6 秒）、`position.x`（4.52 秒）、`rotation.z`（6 秒），三個週期互質。語法見 caml-syntax.md §3.3。我們的 kit 目前用巢狀圖層達到同樣效果（✅）。

---

## C. 環境動態

> ⚡ 本節都是循環動畫。待機時它們會讓系統每一幀都重畫，backboardd 多 26–30% CPU，手機會發燙（§H），所以現在預設禁用（`allow_loops=True` 才能建置）。要用之前先問使用者，或改寫成 §T 的轉場版本。

### C1 吊線道具（鐘擺）✅（有栖的月亮、熊、漢堡、星星；Akane／Arisu-DDA 的星燈）
線畫在道具圖裡（`cardboard(draw, px, thread_pt)`），`anchor=(0.5, 1.0)` 放在線頂，`rotation.z` 擺幅 ±3–6°，週期 2.8–4.4 秒，每個道具的 `timeOffset` 都要不同。
```python
p = Layer(name, w, h, x, top, img=key, anchor=(0.5, 1.0)); p.animate("transform.rotation.z", [-amp, amp], dur, offset=off)
```
線頂要藏在幕簷（valance）後面。線不夠長時，道具會被幕簷擋住。

### C2 漂浮小物（位移 → 旋轉 → 閃爍）✅（`floating_bit`）
`Drift`（position，三點路徑，5.5–9.5 秒）→ `Spin`（rotation）→ 圖片本身（opacity）。適合碎片、果凍星、光點。

### C3 紙花下落 ✅（有栖）
三層巢狀：
- `Fall`：`position.y` 從 960 到 -40，linear，不 autoreverse，`timeOffset` 隨機，所以不會同時落下。
- `Sway`：`position.x` ± 振幅。
- `Piece`：`rotation` 轉一整圈 2π，linear。

### C4 羽毛／花瓣沿 Z 字路徑下落 🔶（Akane）
單一 `position` 關鍵影格，19–44 個點左右擺動往下，週期 23–38 秒，linear、不 autoreverse；再另外加 `rotation` 擺動。用 kit 寫就是 `animate("position", [(x, y), ...], dur, autoreverses=False, timing="linear")`。

### C5 Zzz 上升 ✅
`Rise` 群組做 `position.y +44`（easeOut），`z` 本身做 `opacity [0, .85, 0]`（`key_times [0, .3, 1]`）。三個 z 錯開 1.4 秒。

### C6 腳印依序出現 ✅（有栖的爪印）
N 個圖層共用同一條 `opacity` 時間軸（`key_times` 定出「亮—持續—消失」），每個圖層的 `timeOffset = (period - i*step) % period`。整體看起來像有東西一步步走過。

### C7 光塵粒子（CAEmitterLayer）✅（Manosaba）
```python
dust = Layer("Dust Back", S, S, C, C, kind="CAEmitterLayer")
dust.emitter = dict(size=(1150, 1150), mode="surface", render="additive", cells=[dict(name="Mote Warm", img="mote.png",
    birthRate=7, lifetime=16, lifetimeRange=6, velocity=9, velocityRange=7, scale=0.16, scaleRange=0.1,
    alphaSpeed=-0.05, spinRange=0.4, color=(1.0, 0.86, 0.74), alpha=0.75)])
```
kit 寫出的發射器是矩形、中心放射。參考作品還有以下兩種變化 🔶，需要先擴充 kit（屬性見 caml-syntax.md §5）：
- **點發射器放在畫布外**，`birthRate` 0.05–0.2、`lifetime` 50、`velocity` 40–80，`emissionLongitude` 朝向畫面內，再加 `spin`。效果是偶爾飄進來一片花瓣或羽毛（Arisu-DDA、Tsumugi）。
- **矩形發射器沿上緣**，例如 2000×86。`emissionLongitude=-π/2` 讓粒子往下，`velocity` 250–300，`renderMode=additive`，圖層 `speed=3`，再加 `alphaSpeed`。效果是星雨（Selector）。

### C8 疊層翻頁動畫（flipbook）🔶（Horoscope Express）
N 張影格各自一層疊在一起。每層的 `opacity` 時間軸只在自己的時間窗內是 1，例如 18 層、每層 10 個值、總長 540 個值、3 秒，前三分之一播完後停頓。用 `key_times` 寫會精簡很多。適合少量影格的小動畫，例如閃光、跳動的符號。

### C9 contents 逐幀 🔶（XeleidScope，不建議）
在 `contents` keyPath 上放 CGImage 的關鍵影格。XeleidScope 用了 390 張 JPG、6.5 秒、autoreverse，檔案高達 292 MB，記憶體與容量都太重。真的需要時，只用少量小圖。

### C10 窗燈閃爍 🔶（Horoscope `building`）
在 `opacity` 時間軸上不規則地切換 0 和 1，例如 77 個值、4 秒，模擬城市燈光。

---

## D. 光影

### D1 光束／聚光燈 ✅
程序生成一張錐形光的 PNG（`beam()`），錨點放在光源 `anchor=(0.5, 1.0)`，做 ±1.4–2.5° 的緩慢擺動。外層群組再做 `opacity` 脈動（0.45↔0.9，7 秒），或用狀態控制亮度。Manosaba 的 god rays、有栖的中央聚光燈和兩側側燈都是這樣做。

### D2 腳下光圈與幕上光暈 ✅
- `pool()` 橢圓光圈放在角色腳下。
- `soft_glow` 打在布景上，例如有栖的 Curtain Wash：Lock 時 0.9，揭幕後降到 0。
- 這些光源的強度要跟著聚光燈的狀態一起調，亮度才一致。

### D3 輪廓光／氛圍光 ✅（`alpha_glow`）
```python
aura_img, pad = alpha_glow(im.getchannel("A"), AQUA, scale=0.2, dilate=5, blur=10, pad=36, strength=0.9)
aura = Layer("X Aura", (im.width + 2*pad) * ppt, (im.height + 2*pad) * ppt, w/2, h/2, img=asset("x_aura.png", aura_img))
aura.animate("opacity", [0.25, 0.55], 3.0)
```
- 從角色的 alpha 擴張並模糊出光暈，放在本體下方。
- 冷色光（AQUA）適合魔法感，暖色（WARM）適合舞台燈下的輪廓光。
- 計算時用 `scale=0.2` 的小圖，結果再放大，速度快又平滑。

### D4 暗角、睡眠調暗、狀態染色 ✅
- `vignette()` 疊在最上面。
- `Sleep Dim` 是全畫面色層加 `opacity` 狀態。
- 染色見 A6。

### D5 混合模式 🔶（kit 尚未支援，語法見 caml-syntax.md §4）
參考作品中出現的次數：normal 42、multiply 19、lighten 17、overlay 17、colorDodge 3、colorBurn 3、saturation 1、color 1。

| 混合模式 | 用途（參考作品） |
|---|---|
| `lightenBlendMode` | 光的疊層，例如 Vocal Party 的 `bgL`（opacity 0→0.45、4 秒呼吸）、發射器的光點 |
| `overlayBlendMode` | 從角落斜射進來的漏光：Arisu-DDA 的 LB／RB／LF／RF，`anchor (0,1)`，在 −10°～+5° 間旋轉、8 秒。也用在標題字 |
| `multiplyBlendMode` | 陰影：圖形的複製層加高斯模糊 20，opacity 0.4–0.5（Selector） |
| `saturationBlendMode` | 讓大標題字只影響底圖的彩度（TSUBAKI） |

我們目前改用預先合成好的 PNG 達到同樣效果（✅，也比較省）。真要用混合模式，要先擴充 `layer_xml`，並請使用者實機確認。另外，預覽渲染器不模擬混合模式。

### D6 高斯模糊濾鏡 🔶
在圖層上加 `<filters><CAFilter filter="gaussianBlur" inputRadius="20"/></filters>`，用來做會跟著物件移動的柔和陰影。能預先烘焙進 PNG 的話，就不要用即時濾鏡。

### D7 閃電腳本 🔶（Parad_ox）
`black`（壓暗）、`flash`（全白）、`Light`（lighten 的雷光）三層各自有一條 369 個值、15 秒、不 autoreverse 的 `opacity` 時間軸，共同編排：壓暗 → 白閃 → 雷光殘影 → 恢復。我們實作時用同一組 `key_times` 對齊三層，週期要長，大部分時間保持平靜。

---

## E. 景深、陀螺儀、遮擋

### E1 分層與 parallax 量 ✅
`layer.parallax = N` 會讓圖層隨陀螺儀在 ±N pt 範圍內平移。我們慣例上都設在 `CATransformLayer` 群組上（其他圖層類型沒測過）。數字越大，感覺越靠近觀看者。我們的實際取值：

| 層 | N |
|---|---|
| 遠景布幕、天空 | 6 |
| 燈光 | 7 |
| 吊掛道具 | 9 |
| 地板 | 10 |
| 幕後的主角 | 11 |
| 前幕、幕簷、時鐘前的角色 | 12 |
| Manosaba 寬背景 | 14 |
| 爆散星星 | 26 |
| 前景碎片、果凍星 | 30–44 |
| 前景紙花 | 34 |

- **前後順序和 N 要一致。** 被別的東西擋住的層，N 不要大於擋它的層，不然傾斜時深度會打架。
- 每個 view 的歸屬（Background 或 Floating）由頂層群組名稱自動判定。

### E2 BACKGROUND 與 FLOATING ✅
- BACKGROUND 在時鐘下方，FLOATING 在時鐘上方（景深效果）。
- 鎖定時要蓋住時鐘的角色放 FLOATING。
- 只在 Home 出現的東西不需要景深，可以放 BACKGROUND，去和布景互相遮擋（A2）。
- AOD 沒有景深，Sleep 的東西不論放哪層，都要在時鐘下方。

### E3 遮擋差分檢查 ✅（揭幕類技巧必做）
把被遮擋層的鎖定 `opacity` 分別設成 0 和 1，各渲染一次，在多種傾斜下比較差異：
```python
import build_x as M
from tendies_kit import render, state_values, walk
from PIL import ImageChops
root = M.build_root(); hidden = next(l for l, _ in walk(root) if l.name == "Shooter Stage")
imgs = []
for op in (0.0, 1.0):
    hidden.states["opacity"] = (op,) + hidden.states["opacity"][1:]
    imgs += [render(root, 3.1, state_values(root, {"lock": 1.0}), 2.0, tilt=t) for t in ((0, 0), (1, -1), (-1, 1))]
for a, b in zip(imgs[:3], imgs[3:]):
    print(ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L").getextrema())   # max ≤ ~8 = 看不出
```
有栖第一版從流蘇透出最大 56/255。把幕下襬下移 40 pt 之後降到 6/255。

### E4 巢狀透明度做非線性淡出 ✅
狀態只會線性內插。要讓東西消失得更快，就把同樣的 `opacity` 狀態設在兩層巢狀群組上，相乘得到 (1-u)²；三層則是 (1-u)³。這個方法不依賴超出範圍的數值，安全。kit 的寫法是 `chained(name, (lock, home, sleep), depth, child)`。
（反過來「出現得更快」做不到。要嘛讓它被布景擋住並保持不透明（A2），要嘛接受線性淡入。）

### E5 從腳底縮放 ✅
一個 S×S 的 Stage 圖層，`position` 放在腳的位置，`anchor=(0.5, FEET/S)`，`transform.scale.xy` 依狀態設為 0.9→1。角色就像站穩地往前一步，不會浮起來。

### E6 `hidden` 狀態：轉場一開始就切換 ✅（耗電測試 G）
`hidden` 是布林值，狀態內插出來的中間值只要不是 0，就算隱藏。把值設成 (0, 10000, 10000)，轉場一開始圖層就消失；反方向回到 Lock 時，要到轉場的最後一刻才出現。

### E7 透明度超出 0–1 會被截斷 ✅（超過 1：耗電測試 G；低於 0：FX 的視窗交接）
`opacity` 狀態設成 (0, 10000, 10000) 時，轉場的第一幀就完全不透明，靜止時看起來跟 1 一樣。和 E6 搭配，就能在同一幀把 A 換成 B。只設 50 不夠：第一幀只有約 0.25，實機會看到元素閃一下。

### E8 `speed` 狀態可以暫停循環動畫 ✅，但轉場途中會亂跳
`speed` 設成 (1, 0, 0)，桌面和 AOD 上的循環動畫就停住，耗電跟沒有動畫一樣（3.9%）。問題在於動畫播到哪一格，是用「開機到現在的秒數 × speed」算的：轉場途中 speed 一變，時間點就跳到隨機位置，畫面看起來在亂跳。

要用的話，必須搭配 E6、E7 換成靜止替身。替身要停在動畫第 0 秒的姿勢（`perf_probe.pose()`）；直接停在 model 值的話，所有落葉會排成一條線。這套做法實機可行，量到 6.7%，但使用者否決了：鎖定畫面照樣耗電，下拉回鎖定時還會卡一下。最後改成完全不放循環動畫（§H）。

---

## F. 版面

### F1 正方形 root 適配多姿態 ✅
890×890 的 root 會被 PosterBoard 以 aspect-fill 置中。參考作品的 iPad 版也用正方形畫布（3176²、5435²、7680²）🔶，作法一致。
- 寬背景要超出 root，例如 `base` 群組設成 2800×2800 的純色，傾斜時才不會露底。
- `make_previews` 第二列是陀螺儀極限傾斜的預覽，用來檢查邊緣。

### F3 角色要夠大：半身構圖 ✅（`build_chinatsu.py`）
使用者回饋：全身立繪站在畫面中「人有點太小了，不一定要全身露出來」。

做法：
- 把整張立繪放大（千夏是 830 pt 高），讓螢幕下緣切在膝蓋上方。
- 腳的位置 `FEET` 落在螢幕下方（−249），當作搖擺與縮放的支點，整個人像從腳底輕輕搖擺。
- 永遠不會露出的下半段直接裁掉（`CROP`），省記憶體。
- 確認轉場和陀螺儀傾斜時，裁切線都不會露出。
- 息屏用 `SLEEP_SCALE = (SLEEP_TOP - FEET) / GIRL_H` 以同一支點縮小，讓舉起的手頂端停在時鐘下方。

### F2 時鐘避讓 ✅
- 鎖定時，角色頭頂約在 y≈556，放 FLOATING，時鐘被拉長也沒問題。
- Sleep 時，主體頂端 ≤ 410–415。
- 臉不要放在時鐘的數字範圍裡（`CLOCK` 表）。
- Duo 分螢幕格式用每個螢幕自己的時鐘數字（§F4）。

### F4 Duo 分螢幕格式 ✅
這是 iOS 27 原廠 Duo 桌布（Clownfish-V68）的寫法，匯入的桌布也能用（探測檔和 Manosaba 都在實機驗證過）。
- **結構**：root 的 `<style>` 放 `<wallpapers>` 陣列，每個螢幕一個字典。外螢幕（`Cover Screen`）用 `BACKGROUND TWO`／`FLOATING TWO`，內螢幕（`Inner Display`）用 `ONE`。每個螢幕有自己的 parallax 和 property groups，數值分成 `portrait_*`／`landscape_*`。格式見 caml-syntax.md §6.1。
- **座標**：1 個 root 單位等於 1 個裝置像素，root 中心對齊螢幕中心，y 軸向上。可見範圍是外螢幕 1398×2034、內螢幕直向 2007×2853、橫向 2853×2007（`DUO_VIEWS`）。
- **橫向放大的開關在 `Wallpaper.plist`** ✅（2026-11-12 實機）：
  - 桌布永遠在直向 669×951 pt 的視窗裡排版，橫向時系統把內容轉 90 度。
  - `Wallpaper.plist` 沒有 `requiresLandscapeScaling` 時，系統會把直向版面等比放大 951/669 倍（約 1.42）去蓋滿橫向螢幕，同時還是套用 `landscape_*` 的數值，結果整個橫向版面被放大。
  - 原廠的 Clownfish-V68 寫的是 `requiresLandscapeScaling = false`。`package()` 遇到 Duo 格式會自動加上，並把它算進 identity。
  - **還沒解釋的現象**：沒有這個鍵的檔案，11/8 深夜到 11/12 凌晨之間橫向是 1:1，之後同一個檔案變成 1.42 倍，重開機、重新套用、從直向轉過去都一樣。root 大小（890、3600、6000）、減少動態效果都跟它無關。所以不要用「沒寫這個鍵時的表現」來校正版面。
  - 這個鍵對舊格式（單一正方形 root）的影響沒有測過，`package()` 只在 Duo 格式加。
- **root 邊長用 6000**（`DUO_R`，跟原廠一樣）。
- **實機行為**：
  - 每個螢幕顯示自己那組圖層，Lock／Home／Sleep 和直橫向的數值都會跟著切換。
  - 景深（FLOATING 蓋過時鐘）、陀螺儀、AOD（時鐘在最上層）都跟舊格式一樣。
  - 開闔時兩組圖層之間不會變形，各螢幕只顯示自己的；轉動中的那半邊，系統會加上變暗和模糊。
  - 打開手機會把內螢幕從 AOD 喚醒，所以「Sleep → Lock」的轉場就是開闔時看得到的動畫。原廠的開闔縮放推測來自這裡 ⚠️。
- **kit**：
  - `duo_tree(name)` 建頂層樹。
  - `Layer.land(kp, lock, home, sleep)` 設橫向值。
  - `duo_caml(screens)` 輸出。
  - `make_duo_previews(screens, dir, names)` 預覽三種姿態，時鐘照 `DUO_VIEWS` 畫。
- **使用者的時鐘拉高了**。實測底部從螢幕中心算（px）：外螢幕 −24、內螢幕直向 +369、橫向 −57。數字寬度會隨時間變化，x 取看過最寬的。

### F5 同一個構圖，各螢幕取景 ✅（`build_tendies.py`）
使用者否決了「依方向重排元素」：橫向時角色站一側、刀放另一側，AOD 兩人拉開，被說「亂、不整齊、沒有原本好」。改成以下做法：
- **場景只寫一次**：照舊用 S×S 的點座標。
- **每個螢幕一份副本**：`duo_screens(scene, frames, extras)` 替每個螢幕複製一份，所有圖層名稱加上 ` ONE`／` TWO`，放進一個 Frame 圖層。Frame 的 `transform.scale.xy` 是每點幾像素，`position.y` 決定高度。內螢幕的橫向取景用 `.land()` 寫在同一個 Frame 上。
- **取景參數放在 `POSTURES`**：
  - `F`：大小。
  - `head`：角色頭頂的落點，在時鐘底部往上約三分之一。鎖定時靠景深，她在時鐘前面。
  - `duo_head`、`duo_h`：AOD 兩人的頭頂和全身高度。
  `framing()` 用這些算出 Frame 的位移，以及 AOD 兩人的縮放。
- **暗角跟著螢幕形狀**：每種姿態一個橢圓暗角。內螢幕放直、橫兩個，用 opacity 狀態加 `.land()` 依方向切換。只用一個正方形暗角的話，橫向會露出它的邊（實機看到 ✅）。
- **背景要蓋滿最寬的範圍**：背景圖和光束都要涵蓋每種姿態最寬的範圍。光束圖左右兩側做淡出，橫向才看不到圖的邊。橫向比較寬，平移距離改短（`LAND_PAN`）。
- **外螢幕取景比內螢幕緊**，打開手機時看起來就像鏡頭拉遠。

### F6 AOD 人物半身 ✅
使用者要求「把人放大往下放，半身那種感覺」。做法：
- 兩人並排站在 y = 0，整體高 `DUO_H`。
- 每種姿態用錨點在腳底的 `Duo Zoom` 放大，再抬到頭頂剛好在時鐘下緣下方約 60–80 px，身體由螢幕底邊裁掉。
- 只有上面 72%（`DUO_KEEP`）可能露出，其餘直接裁掉省記憶體。
- 立繪用原圖（約 3800 px 高），縮到最大的顯示尺寸。

### F7 卡片式版面：內容掛在四個角 ✅（個人用的 `ports/build_nina_card.py`）
素材是一張有外框的直式卡片（白框、灰色面板、四周貼紙）時，橫向不能只放大裁切，否則只剩一張臉。做法是讓卡片跟著螢幕變寬、變高：
- **卡片維持原比例**：縮放 `s = min(螢幕寬 / 卡寬, 螢幕高 / 卡高)`。直向剛好滿寬，橫向剛好滿高。
- **每樣東西掛在卡片的一個角上**：四個「角群組」的錨點各在卡片的一角，位置設在螢幕對應的角，縮放是 `s`。裡面的圖層直接用原圖的像素座標，不用再管姿態。內螢幕的直、橫兩組數值用 `.state()` 加 `.land()` 寫在角群組上。
- **外框不用圖**：面板是一塊很大的灰色色塊，四邊各一條很大的白色色塊，掛在對應的角群組裡；圓角用四張小圖補。螢幕變寬時，面板自然跟著變寬。
- **橫向把東西分到兩邊的角落**：原圖左半邊的貼紙掛左下角，角色和右半邊的掛右下角。直向時卡片剛好滿寬，兩個角算出來的位置一樣，所以只有橫向會分開。第一版讓名字貼紙橫向仍貼在角色旁邊，使用者說「怪怪的」，要它移到左下角才協調，並希望多利用 Duo 的分螢幕格式。
- **貼紙移走後，角色被它遮住的部分會露出來**。那一塊是補繪的（G5），不能靜態露出。橫向時把角色放大、站低一點，讓外框下緣擋住那一段：`POSE` 的 `home` 給放大倍率，以及外框切在原圖的哪一列。
- **角色被外框切掉的邊**（原圖就是這樣畫的）：外框的下緣放在 FLOATING、疊在角色上面當遮擋。角色的錨點放在面板的右下角，縮放和升降都繞著這一點，被切的那一邊就一直貼著框。角色的陀螺儀量要跟外框一樣，否則切邊會跟框分開。
- 這仍然是同一個構圖（F5）：每個角落的東西都還在同一個角落，只有中間的面板變大。

---

## G. 素材管線

### G1 遊戲資料 ✅
以 ONGEKI 為例（素材來自自行合法取得的遊戲資料，AssetRipper 匯出）：
- 角色資料：`StreamingAssets/GameData/A000/chara/charaXXXXXX/Chara.xml`，內含名字、簡介、台詞、生日。
- 卡片資料：`card/*/Card.xml`，對應 CharaID。
- 卡面去背圖在 `ui_card_chara/UI_Card_Chara_<id>.png`，尺寸 768×1052。
- 劇情立繪在 Sprite atlas 裡，依 `m_Rect` 裁切；注意 Unity 的 y 軸是由下往上。
- 遇到官網圖時，先去掉投影：把 alpha < 32 的像素清掉。

**`ongeki.py`：直接讀官方素材** ✅（repo 內的模組，路徑可用環境變數 `ONGEKI_EXPORT` 改）：
- `card(id, full=False)`：卡面去背圖或完整插圖，768×1052。
- `story_sprite(chara, face)`／`story_face(chara, face)`：劇情立繪，依 prefab 的 RectTransform 錨點組合身體與表情臉。
  - 資料流：`Sprite/*.asset` 裡的 `textureRect` 指向 atlas 上的像素（y 軸由下往上），`texture` 的 guid 再對應到 `Texture2D/*.png.meta`。
  - 劇情立繪原尺寸約 509×1449。用 Real-ESRGAN 放大 4 倍後，545 pt 高時約 10 px/pt。
- `chapter_bg(id, layer)`：章節背景，1080×1080 的正方形，剛好對上我們的 root。部分背景還有分層版，例如 `9903401` 的天空 `_01`、大樹 `_02`、學校廣場 `_03`、樹冠閃光 `_04`，可以分層做視差與日夜版。
- `texture(name)`：任意 Texture2D。可用的有：
  - 樹葉 `FX_mm_leaf_01`、`st_2030_leaf`，用 `cut_sprites` 切開。
  - 星星 `Star_001`、`st_2015_star_df`、星空 `st_2000_sky_df`。
  - 雲 `st_*_cloud_df`、各種 glare。
- 黑底的加亮貼圖（glare、星芒、閃光）要轉成「alpha = 亮度」再用，即 `build_chinatsu.glow_alpha`。

**分層背景的對位** ✅：官方合成圖和分層圖比例不同時，用 `cv2.matchTemplate`（mask = 分層 alpha）在 0.4–1.3 倍間搜尋縮放與位置，找到後在合成圖上半透明疊一次確認。學校層和合成圖差異大（合成圖額外加了光效），就改以「底部對齊、滿版寬」排列，依我們的版面重新安排各層。

### G2 放大 ✅
Real-ESRGAN `realesrgan-x4plus-anime`（ncnn-vulkan，在 RTX 5080 上約 3 秒一張；本機放在 `tools/realesrgan/`，不進 repo），放大後存進 `sources/<角色>/*_x4.png`。參考作者的背景則用 AniScale 這類工具放大。

### G3 進場處理 ✅（`build_arisu.source()`）
1. `trim`
2. `clean_alpha`：清掉放大後 alpha < 8 的雜訊
3. `edge_fade`：讓卡面被切掉的邊溶掉
4. `radial_fade`：用聚光燈形狀溶掉被裁切的配角或道具
5. `resize_premul`：縮到剛好 pt×3

另外兩個工具：`lum_to_alpha` 把黑底上的光效轉成 alpha；`extract_shards` 從碎片圖用連通區塊切出一片片碎片。

### G4 程序生成布景 ✅（有栖；**只限抽象元素**）
**禁止**用程式畫具體的有機物件（花、植物、帳篷、望遠鏡、動物），也不要用 AI 生成素材。千夏第一版因此被整個退回，詳見 SKILL.md 的設計原則。可以程式畫的只有：光束、光暈、漸層、暗角、粒子、紙片，以及布幕、舞台地板這類規則的人造布景。
`velvet_panel`（絨布、褶皺、金邊、流蘇）、`valance`、`stage_floor`、`backdrop`、`beam`、`pool`、`soft_glow`、`vignette`、`jelly_star`、`sparkle`、`confetti`、`paw`、`glyph_z`、`cardboard`（紙板道具，含 INK 描邊和吊線）、`playbill`（放入歌曲封面）。
- 細節先在 4 倍尺寸畫，再縮到 @3x。
- 點狀紋理要用另一層疊上去，不要在 alpha 上打洞。
- 平移陰影不要用 `np.roll`，它會把陰影捲到另一側。

### G5 把一張平塗插畫用程式拆成圖層 ✅（個人用的 `ports/nina_cutout.py`；疊回去和原圖平均差 0.15/255）
適用於底色是純色、貼紙邊緣銳利的插畫（貼紙卡、拼貼海報）。不靠模型猜，全部用顏色和形狀判斷：
1. **背景**：卡片的白和面板的灰都是單一顏色。灰色只算面板內、白色只算面板外，連到大片底色的就是背景。面板內同色的小塊要逐一確認：髮絲之間的是鏤空，裙子上的是陰影。
2. **獨立的貼紙**：扣掉背景後，每個連通區塊就是一張貼紙。
3. **疊在一起的貼紙**用各自的外框分開：
   - 有描邊線的：線內的白邊和內容是一個封閉區域，往外長一個線寬就是整張貼紙。
   - 純黑外框加偏移陰影的：貼紙外框是純黑（0），角色的線稿是近黑（約 20），用門檻就能分開。填滿外框，再加上右下方那一圈陰影色。
   - 照片、標籤：量出四條邊線，用四邊形切。
4. **被遮住的部分要補**，因為圖層之間會相對移動：
   - 白邊和描邊線：從內容的外形往外擴，重畫出來。
   - 照片：沿著照片自己的方向，重複最近的可見像素。
   - 角色：`cv2.inpaint`，顏色只取她自己的像素。
   - 補出來的只撐得住幾個像素的位移，所以壓在角色身上的貼紙要少給陀螺儀量。
5. **邊緣**：貼紙碰到底色的那一圈，原圖的像素是貼紙色和底色的混合。底色 B 已知，取 3 px 內離 B 最遠的顏色當貼紙色 F，alpha 就是這個像素從 B 往 F 走了多遠。這樣拿到的是原圖本來的抗鋸齒，換到深色底也沒有白邊。
6. **驗證**：把所有圖層照原本的前後順序疊回去，跟原圖逐像素比對。

---

## H. 效能與版本變體

### H1 待機零循環動畫（硬規則）✅
使用者回報手機待機會發燙。用 `scripts/measure_backboardd.py` 從電腦讀 backboardd（負責畫面合成的系統行程）的 CPU，停在桌面閒置 60 秒：

| 桌布 | 平均 CPU |
|---|---|
| 靜態桌布 | 5.7% |
| Manosaba、千夏、FX、有栖（舊版，有循環動畫） | 32–38% |
| 千夏拿掉所有循環動畫 | 5.2% |
| 千夏只留一顆 29 pt 的旋轉星星 | 26.3% |
| Manosaba Duo 版（零循環，動態都在轉場） | **4.0%** |
| 仁菜貼紙卡（零循環；量的時候沒有確認停在哪個畫面） | 2.9% ⚠️ |

耗電跟動畫多寡幾乎無關，關鍵是「有沒有任何東西在動」：只要有一樣在動，整個畫面每一幀都要重畫。所以規則是待機零循環，動態放進轉場（§T）。

其他試過的做法（都以千夏為底）：

| 做法 | 平均 CPU | 結果 |
|---|---|---|
| 動畫層在桌面時透明度設 0 | 34.7% | 照樣耗電，看不到也在重畫 |
| `speed` 狀態暫停（E8） | 3.9% | 省電，但轉場途中亂跳 |
| 動畫加上限制幀率的設定（`frameInterval`、`discretizesTime`、`preferredFramesPerSecond`） | 18.5% | 只省一半；三個裡是哪一個生效還不知道 ⚠️ |
| 只在鎖定畫面動，桌面和 AOD 換成靜止替身（E6＋E7＋E8） | 6.7% | 桌面省電，但鎖定畫面照樣耗電，下拉回鎖定時還會卡一下，使用者否決 |

量測時手機要平放在桌上不動，停在主畫面。前景 App（例如 Discord）會把數字拉高到 20% 以上，手持時陀螺儀感應到的微小晃動也會。

### H2 記憶體與版本變體

- **記憶體**：建置時會印出解碼後大小（寬×高×4）。有栖約 77 MB、36 張圖。
  參考作品中，rosalia 有一張 7680×3268 的圖，光它就約 100 MB。作者也註明：記憶體 < 8 GB 的機型要用「better performance」版。
- **效能版** 🔶：把同一套素材降解析度，例如 7680→2456 px（26 MB→6 MB）、4961→1966 px（48 MB→6 MB）。在我們的管線裡，等於把 `PPT` 調成 2。使用者回報卡頓或閃退時再提供。
- **無 AOD 版** 🔶：只改 Sleep 的排版（位置／尺寸）。作者說明不開 AOD 的使用者選這版可以避免動畫 bug。
- 我們目前只出一個版本。使用者有需要時再加變體開關，例如 `--perf` 參數改用 `PPT=2`。

---

## P. 移植別人的桌布到 Duo ✅（`ports/`，僅限個人使用，不放進 repo）

使用者回饋：第一版移植是我照自己的想法重新排版，被說「原本的特色都沒了」，還出現人物互相遮擋、橫向畫面露出被切掉的字、息屏的交錯層次消失等問題。原則如下：

1. **作者有 iPad 版就移植 iPad 版。** iPad 版本來就是正方形畫布，直橫兩用，跟我們的正方形 root 同一個思路，整張等比縮放即可（`ports/build_gbc_ipad.py`）。
   - 縮放比例要略小於填滿：Duo 直向比 iPad 窄（0.69 對 0.75），填滿時主標題會貼到外螢幕邊緣。先量出主要文字的範圍，再選比例，至少留 20 pt 邊距。
   - iPad 的 Sleep 只是熄螢幕的一瞬間，iPad 沒有 AOD；在 Duo 上 Sleep 會變成長時間顯示的 AOD，所以要套用「頭在時鐘下」的規則。做法是保留原作的錯落動作，整組往下移。
   - 原作有亮色／暗色兩套狀態時，不要拆成兩個檔（使用者要求）。鎖定和主畫面用亮色，息屏改用暗色。
     - 做法：只讓純色底交叉淡出。暗色底在下，亮色底在上，亮色設 opacity 狀態 (1, 1, 0)。兩套主題共用的文字和圖案只放一層透明圖，疊在兩個底上面。
     - 不要把兩張不透明面板疊起來淡出。GBC 原作的亮色面板比暗色的大約 0.75 pt，淡出到一半時，多出來的那圈邊會變成白框（實機看到 ✅）。
     - 兩張面板是同一份墨色疊在不同底色上時，可以用差分去背一次算出透明度：`a = 1 - (亮版 - 暗版) / (亮底 - 暗底)` ✅。
     - 原作在面板邊緣切掉的描邊重複字，可以從實心字重建，延伸到整個畫面寬度（使用者要求）✅。GBC 的描邊是實心字約 1.45 px 的內描邊，每列有固定間距。
     - 人物在主畫面和息屏都往下藏到畫面外，連陀螺儀抬起後也看不到。主畫面進 AOD 時人物會冒出來一下，原因與處理見 §A 開頭。
     - AOD 沒有景深，主標題要整組移到時鐘下方，在「最低的時鐘底」和「最高的畫面底」之間置中（`tendies_kit.clock_floor()`）✅。
2. **只有手機版時，忠實對應原作座標，不要自己重排。**
   - 每個元素的位置都從原作座標換算：直向拉寬（例如 ×1.3～1.43）、高度 ×0.93，尺寸維持等比例。
   - 互相依附的元素以群組為單位，保持原作的相對距離，例如角色和她的標題（`rel()`）。
   - 原作的疊放順序和招牌元素都要保留，例如 FX 的條紋視窗框：視窗的左右邊收在直向畫面內側，上下邊放在橫向裁切區外，這樣直向看到上下條紋、橫向看到左右條紋。
   - 原作刻意安排的銜接也要保留，例如鎖定和息屏的 Kurumi 在同一個位置，進入息屏時才有接續感。這種情況下時鐘可能蓋到臉，要回報給使用者，讓他決定。
3. **文字必須在每個裁切範圍內完整顯示或完全藏起來**，三種狀態、三種姿態和陀螺儀極限傾斜都要檢查，用 `port_util.text_check()`。裝飾性的出血文字（例如邊緣的描邊字）除外。
4. **原作的狀態切換是彈簧動畫，我們的是隨手指線性內插。** 停放位置要放在剛好出畫面的地方（短程），不然中途會整個空掉。大面積的色塊改成原地淡入，不要用滑的。
5. **記憶體**：用 `place_trim()` 裁掉透明邊，位置不變。放在縮放群組裡的圖用 `PPT × 縮放比例` 就夠。

## I. 驗證工具

| 工具 | 用途 |
|---|---|
| `make_previews(root, dir, names)` | 狀態×姿態總覽、GIF、兩張轉場分解圖，並印出亮度 |
| `transition_strip(root, a, b, path)` | 任意兩狀態間 6 個進度點 × 姿態 |
| `state_luminance(root)` | 各狀態的 Y 與 L*，看 home／lock 比 |
| E3 差分檢查 | 遮擋有沒有漏 |
| 使用者的修復腳本（oracle） | `python -I tools/fix_caplayground_depth_gyro.py out/X.tendies -o <暫存>/check.tendies`：結構被接受且 CA 資源逐位元組相同。腳本若不在本機，就跳過 |
| `scripts/ref_*.py` | 分析參考檔，見 reference-catalog.md |
| `make_duo_previews(screens, dir, names)` | Duo 分螢幕格式的總覽和轉場分解圖 |
| `scripts/measure_backboardd.py LABEL` | 從電腦量手機 backboardd 的 CPU：60 秒，印出平均、中位數、記憶體，並記到 `out/perf/measurements.csv`。需要：開發者模式、`pymobiledevice3`、以管理員身分執行的 `pymobiledevice3 remote tunneld`（iOS 17 以後需要；iOS 27 會自己掛好開發者映像檔） |
| 推進 AirCard | `pymobiledevice3 apps push --documents com.mak5er.aircard X.tendies /Documents/Tendies/X.tendies`（AirCard Depth Test 的 bundle id）。Windows 要先裝 Apple Devices；在 Git Bash 下要加 `MSYS_NO_PATHCONV=1`，否則手機端路徑會被改寫 |
| 從電腦截手機畫面 | `pymobiledevice3 developer core-device get-display-info` 列出螢幕和 `uniqueId`；`... core-device screen-capture screenshot --display-unique-id <內螢幕的 id> out.png` 截內螢幕。`developer dvt screenshot` 只截得到外螢幕。畫面細節多（PNG 約 15 MB 以上）時服務會斷線，改請使用者在手機上截圖，再用 `pymobiledevice3 afc pull /DCIM/100APPLE/<檔名> <本機路徑>` 取回（先徵得同意，只拿指定的那幾張） |
| 看系統怎麼載入桌布 | `pymobiledevice3 syslog live` 存成檔案後搜尋 `CollectionsPoster{WallpaperKit}`。有用的訊息：`Parsed variant`（每個螢幕的 idealSize、refBounds）、`Switching variant`、`Initial orientation of poster`、`CAML warning`。切換桌布或鎖屏再喚醒時才會出現 |
| 不需要管理員通道 | DVT 和 CoreDevice 指令加 `--userspace` 就能用，不必先開 `remote tunneld`。`measure_backboardd.py` 找不到 tunneld 時會自動改用它 |
