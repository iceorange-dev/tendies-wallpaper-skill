# CAML 與 tendies 格式速查

本檔的片段都抄自實際檔案：我們建置的 `Suzushima-Arisu-Fold.tendies`，以及參考作品。
- 🔶：只在參考作品（LayeredAnimation）裡出現過。
- ✅：我們的 kit 會輸出、而且實機驗證過。

## 1. 封包結構

### 1.1 我們的 ParameterizedCA ✅（由 `tendies_kit.package()` 產生）

```
descriptors/<UUID>/                         ← zip 內每一層目錄都要有明確的 entry（Nugget 會數 descriptors/X/）
  com.apple.posterkit.provider.descriptor.identifier
  com.apple.posterkit.provider.identifierURL.suggestionMetadata.plist
  com.apple.posterkit.role.identifier
  providerInfo.plist
  versions/0/
    com.apple.posterkit.provider.instance.renderingConfiguration.plist      ← iOS 27 修復：開啟景深與動態效果
    com.apple.posterkit.provider.instance.complicationLayout.plist
    com.apple.posterkit.provider.instance.titleStyleConfiguration.plist
    supplements/0/com.apple.posterkit.provider.supplementURL.homescreenConfiguration.plist
    contents/
      .com.apple.posterkit.provider.contents.configurableOptions.plist      ← 隱藏檔，存 preferredRenderingConfiguration
      com.apple.posterkit.provider.contents.otherMetadata.plist
      com.apple.posterkit.provider.contents.userInfo
      7400.WWDC_2022-390w-844h@3x~iphone.wallpaper/
        Wallpaper.plist
        <identity>.Clownfish_Gyro.ca/       ← 名稱裡必須有大小寫完全正確的 "Clownfish"
          index.xml  (rootDocument = main.caml)
          main.caml
          assetManifest.caml
          assets/*.png
```

`Wallpaper.plist`（我們的版本）：
```python
{'assets': {'lockAndHome': {'default': {'assetFileName': '727037.Clownfish_Gyro.ca', 'identifier': 7920,
                                        'name': 'Lavender', 'type': 'ParameterizedCA'}}},
 'family': 'Marble', 'logicalScreenClass': 'any', 'appearanceAware': False, 'identifier': 727037,
 'productTypes': ['iPhone18,3', 'iPhone19,4', 'iPhone18,4'], 'wantsDeviceMotion': True, 'version': 6,
 'contentVersion': 1.07, 'preferredProminentColor': {'default': '#FFFFFF'}, 'preferredTitleColor': ['#FFFFFF02'],
 'name': 'Lavender'}
```

- identity 和兩個 UUID 都從 CAML 加 PNG 的 SHA-256 推算。內容沒變，identity 就不會變，所以 identity 也能拿來快速判斷「重構後輸出有沒有改變」。
- 只改外層檔名或 `family`，對 iOS 27 的景深檢查沒有任何作用。

### 1.2 LayeredAnimation 🔶（CAPlayground 匯出，參考作品幾乎都是）

```python
{'assets': {'lockAndHome': {'default': {'type': 'LayeredAnimation', 'identifier': 7400, 'name': 'WWDC 2022',
    'backgroundAnimationFileName': '7400.WWDC_2022_Background-390w-844h@3x~iphone.ca',
    'floatingAnimationFileNameKey': '7400.WWDC_2022_Floating-390w-844h@3x~iphone.ca',
    'foregroundAnimationFileName': '7400.WWDC_2022_Foreground-390w-844h@3x~iphone.ca'}}},
 'family': 'WWDC22', 'logicalScreenClass': '390w-844h@3x~iphone', 'appearanceAware': False, 'identifier': 7400, 'version': 1}
```

- 三個 `.ca` 各自有完整的圖層樹和狀態，分別是 Background（時鐘下）、Floating（時鐘上）、Foreground。參考作品的 Foreground 一律是空的。
- **在 iOS 27 會失去 gyro，我們不用。** 讀參考時，把它的 Background／Floating 對應到我們 root 底下的 `BACKGROUND`／`FLOATING` 群組即可。
- CAPlayground 的畫布尺寸各不相同：
  - 手機常見 1216×2160、2000×3840、1900×3840，或直接用 390×844 的座標。
  - iPad 版用正方形：3176²、5435²、7680²。
  - root 一律 `geometryFlipped="0"`，y 軸向上，和我們一致。

## 2. 圖層

```xml
<CALayer id="..." name="唯一名稱" bounds="0 0 W H" position="X Y" anchorPoint="0.5 1" zPosition="0"
         geometryFlipped="0" masksToBounds="0" opacity="1" transform.rotation.z="0.1"
         transform="rotate(5.7deg) scale(1.2, 1.2, 1)" backgroundColor="0.02 0.02 0.07" minificationFilter="trilinear"
         allowsEdgeAntialiasing="1" allowsGroupOpacity="1" contentsFormat="RGBA8" cornerCurve="circular">
  <contents><CGImage src="assets/x.png"/></contents>
  <sublayers> ... </sublayers>
  <animations> ... </animations>
</CALayer>
```

- `position` 是錨點在父層座標中的位置。
- CAPlayground 的群組圖層常見 `bounds="0 0 0 0"`。子圖層照常繪製，只是群組本身沒有內容。
- `kind="CATransformLayer"` 的群組不會壓平子層。我們把 gyro 的 parallax 都設在這種群組上。
- `minificationFilter="trilinear"` 讓縮小的大圖不閃爍，用在大面積細紋理上，例如地板和布幕。

## 3. 動畫

### 3.1 我們 kit 的輸出 ✅
```xml
<animations>
  <animation key="animation-0" type="CAKeyframeAnimation" keyPath="transform.rotation.z" autoreverses="1"
             beginTime="1e-100" duration="7" speed="1" removedOnCompletion="0" repeatCount="inf"
             repeatDuration="inf" calculationMode="linear" timingFunction="easeInEaseOut" timeOffset="2.5">
    <keyTimes><real value="0"/> ... </keyTimes>          <!-- 有給 key_times 才會輸出 -->
    <values><real value="-0.02"/><real value="0.02"/></values>
  </animation>
</animations>
```

- `beginTime="1e-100"` 加 `repeatCount/repeatDuration="inf"` 是無限循環的標準寫法。
- `timeOffset` 用來錯開同類物件的相位。
- 值的類型：
  - `position` 用 `<CGPoint value="x y"/>`。
  - `position.x`／`position.y` 用 `<integer>`：kit 會四捨五入，CAPlayground 也是這樣寫。
  - 其他一律用 `<real>`。
- `timingFunction` 對每一段關鍵影格都套用，例如 `easeInEaseOut`、`linear`、`easeOut`。
- kit 已驗證會用到的 keyPath：
  - `position`、`position.x`、`position.y`
  - `transform.rotation.z`、`transform.scale`
  - `opacity`

### 3.2 keyTimes 做「停頓 → 動作」🔶✅
FX-Fighter 的看板 20 秒循環，前 98% 停住，最後 2% 滑動：
```xml
<animation ... keyPath="position.x" autoreverses="0" duration="20" calculationMode="linear" timingFunction="linear">
  <keyTimes><real value="0"/><real value="0.98"/><real value="1"/></keyTimes>
  <values><integer value="232"/><integer value="232"/><integer value="249"/></values>
</animation>
```
kit 的寫法是 `layer.animate("position.x", [232, 232, 249], 20, autoreverses=False, timing="linear", key_times=[0, .98, 1])`。我們的布偶小跳和爪印都用了 keyTimes（✅）。

### 3.3 單一圖層多個動畫 🔶
CAPlayground 把第一個動畫寫成 `<animation key="animation-0">`，**之後的寫成 `<p key="animation-1">`、`<p key="animation-2">`**，屬性完全相同：
```xml
<animations>
  <animation key="animation-0" type="CAKeyframeAnimation" keyPath="position.y" duration="3.6" ...>...</animation>
  <p key="animation-1" type="CAKeyframeAnimation" keyPath="position.x" duration="4.52" ...>...</p>
  <p key="animation-2" type="CAKeyframeAnimation" keyPath="transform.rotation.z" duration="6" ...>...</p>
</animations>
```
- 參考作品大量使用，例如眨眼層同時有位移和透明度兩個動畫。
- kit 目前每層只輸出一個動畫，改用巢狀圖層。要支援的話：把 `Layer.anim` 改成 list，`anim_xml` 對 i ≥ 1 改用 `<p key="animation-{i}">`。第一次使用要請使用者實機確認。

### 3.4 contents 逐幀 🔶
```xml
<contents><CGImage src="assets/0.jpg"/></contents>
<animations>
  <animation type="CAKeyframeAnimation" calculationMode="linear" keyPath="contents" beginTime="1e-100" duration="6.5"
             removedOnCompletion="0" repeatCount="inf" autoreverses="1">
    <values><CGImage src="assets/0.jpg"/><CGImage src="assets/1.jpg"/> ... </values>
  </animation>
</animations>
```
XeleidScope 用了 390 張影格，檔案 292 MB，太重了。少量影格的動畫可以改用疊層翻頁（techniques C8）。

### 3.5 密集值列表模擬步進 🔶
參考作品沒有用 keyTimes，而是用「很多個 0 加幾個 1」配 linear 來做眨眼或閃電，例如 `blink` 是 140 個值、2 秒、autoreverse，只有最後 6 個是 1。效果相同但檔案冗長；我們改用 keyTimes。

## 4. 混合模式與濾鏡 🔶（kit 尚未支援）

```xml
<CALayer name="Light Leak" ...>
  <compositingFilter type="CAFilter" filter="overlayBlendMode" name="overlayBlendMode"/>
  <filters>
    <CAFilter filter="gaussianBlur" name="Gaussian Blur 1" enabled="true" inputRadius="20"/>
  </filters>
  <contents><CGImage src="assets/light.png"/></contents>
</CALayer>
```

- 出現過的 `filter` 值：
  - `normalBlendMode`、`lightenBlendMode`、`overlayBlendMode`、`multiplyBlendMode`
  - `colorDodgeBlendMode`、`colorBurnBlendMode`、`saturationBlendMode`、`colorBlendMode`
- 出現過的 `filters`：
  - `gaussianBlur`（`inputRadius`）
  - `colorHueRotate`（`inputAngle`，參考作品裡只見過 0）
- 這兩個元素都放在 `<contents>` 前面。
- kit 擴充方式：在 `Layer` 加 `blend` 和 `blur` 欄位，`layer_xml` 依欄位輸出上面兩段。預覽渲染器（`render`）不模擬混合模式，看預覽時要記得這一點。

## 5. 粒子發射器

### 5.1 kit 的輸出 ✅
- 發射器是矩形，`emitterPosition` 在圖層中心，`emissionRange` 為 2π。
- cell 屬性取自 `Layer.emitter["cells"]`，欄位包括：`name`、`img`、`birthRate`、`lifetime`、`lifetimeRange`、`velocity`、`velocityRange`、`scale`、`scaleRange`、`alphaSpeed`、`spinRange`、`color`、`alpha`。

### 5.2 參考作品的完整寫法 🔶
Selector 的星雨：
```xml
<CAEmitterLayer name="Emitter" bounds="0 0 2000 3840" position="850 1920" speed="3"
                emitterPosition="1150 4000" emitterSize="2000 86" emitterShape="rectangle" emitterMode="volume"
                renderMode="additive" birthRate="1" ...>
  <emitterCells>
    <CAEmitterCell name="Cell 1" color="1 1 1" contentsScale="1.2" birthRate="0.65" lifetime="20" velocity="250"
                   emissionRange="0" emissionLongitude="-1.5707963267948966" emissionLatitude="0" scale="1" scaleRange="0"
                   scaleSpeed="0" alphaRange="0" alphaSpeed="0.1" spin="0" spinRange="0" xAcceleration="0" yAcceleration="0"
                   redRange="0" greenRange="0" blueRange="0" redSpeed="0" greenSpeed="0" blueSpeed="0">
      <contents><CGImage src="assets/star.png"/></contents>
    </CAEmitterCell>
  </emitterCells>
</CAEmitterLayer>
```
- 可選的值：`emitterShape` 有 `point`、`rectangle`；`emitterMode` 有 `volume`、`surface`、`outline`；`renderMode` 有 `unordered`、`additive`。
- 圖層的 `speed` 會加快整個發射器的時間。
- `emissionLongitude` 是在 xy 平面上的角度，-π/2 表示往下（y 軸向上）。

## 6. ParameterizedCA 的 root `<style>` ✅

```xml
<style>
  <wallpaperBackgroundAssetNames type="NSArray"/>
  <wallpaperFloatingAssetNames type="NSArray"/>
  <wallpaperParallaxGroups type="NSArray">
    <NSDictionary>                                   <!-- 每個圖層的 x、y 各一筆 -->
      <axis type="string" value="x"/>
      <image type="string" value="null"/>
      <keyPath type="string" value="transform.translation.x"/>
      <layerName type="string" value="Backdrop Parallax"/>
      <mapMaxTo type="integer" value="6"/><mapMinTo type="integer" value="-6"/>
      <title type="string" value="Gyro"/>
      <view type="string" value="Background"/>       <!-- Background 或 Floating，依所屬頂層群組 -->
    </NSDictionary>
  </wallpaperParallaxGroups>
  <wallpaperPropertyGroups type="NSArray">
    <NSDictionary>                                   <!-- 每個 (圖層, keyPath) 狀態一筆 -->
      <image type="null"/>
      <keyPath type="string" value="opacity"/>
      <layerName type="string" value="Set Glow"/>
      <v_home type="real" value="0.35"/><v_lock type="real" value="0"/><v_sleep type="real" value="0"/>
      <view type="string" value="Background"/>
    </NSDictionary>
  </wallpaperPropertyGroups>
</style>
```

- 圖層是**用名稱比對**的，所以名稱必須唯一。
- 已實機驗證的狀態 keyPath：`opacity`、`position.x`、`position.y`、`transform.scale.xy`、`transform.rotation.z`（千夏的手、FX 的漩渦）。
- 參考作品（LayeredAnimation）還用過以下 keyPath，在 ParameterizedCA 中 ⚠️ 未驗證：
  - `bounds.size.width`／`bounds.size.height`
  - `zPosition`
  - `backgroundColor`
  - `cornerRadius`

## 7. LayeredAnimation 的狀態機 🔶（只為了讀懂參考作品）

```xml
<states>
  <LKState name="Locked"><elements>
    <LKStateSetValue targetId="<圖層 id>" keyPath="position.y"><value type="integer" value="0"/></LKStateSetValue>
  </elements></LKState>
  <LKState name="Unlock"> ... </LKState>
  <LKState name="Sleep"> ... </LKState>
</states>
<stateTransitions>
  <LKStateTransition fromState="*" toState="Unlock"><elements>
    <LKStateTransitionElement targetId="<圖層 id>" key="opacity">
      <animation type="CASpringAnimation" damping="50" mass="2" stiffness="300" velocity="0" duration="0.8"
                 fillMode="backwards" keyPath="opacity" mica_autorecalculatesDuration="1"/>
    </LKStateTransitionElement>
  </elements></LKStateTransition>
  ...                                                <!-- 每個狀態一組 *→X 與 X→* -->
</stateTransitions>
```

- 狀態用 `targetId`（圖層 id）指定圖層，不是用名稱。
- 狀態名稱為 `Locked`／`Unlock`／`Sleep`。GBC-iPad 另有 `Locked Light`、`Locked Dark` 等深淺色版本。
- 轉場是到達狀態後播放的彈簧動畫（CAPlayground 預設為 mass 2、stiffness 300、damping 50、0.8 秒），**不會**跟著手指的滑動進度走。這和 ParameterizedCA 的線性內插本質上不同。把參考作品的設計搬過來時，要重新檢查中間幀。

## 8. `tendies_kit` API 對照

| kit | 輸出 |
|---|---|
| `Layer(name, w, h, x, y, kind, img, color, opacity, rot, scale, anchor, trilinear)` | 圖層的各屬性、`<contents>` |
| `.add(*children)` | `<sublayers>` |
| `.animate(kp, values, dur, autoreverses=True, timing="easeInEaseOut", key_times=None, offset=0)` | 一個 `<animation>` |
| `.state(kp, lock, home, sleep)` | `wallpaperPropertyGroups` 的一筆 |
| `.parallax = N` | `wallpaperParallaxGroups` 的 x、y 各一筆 |
| `.emitter = dict(size, mode, render, cells=[...])` | CAEmitterLayer 的屬性與 cells（`kind="CAEmitterLayer"`） |
| `group(name, kind, w=S, h=S, x=C, y=C)` | 預設是滿版的 S×S 群組 |
| `image_layer(name, key, h=None, w=None, x, y)` | 依圖片長寬比補齊另一邊 |
| `asset(name, PIL.Image)` | 登記 `assets/name` |
| `build_caml(root)` → `package(caml, out, build_dir)` | 輸出 `(out, ident, desc_uuid, ca_name)` |
