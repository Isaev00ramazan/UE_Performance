# MadWater — план оптимизации производительности

Основано на замерах в `captures/` (UE 5.7.4, Development-билд, уровень `LVL1_Hollywood/12`, открытый океан).
Цифры — миллисекунды GPU-времени за кадр, если не сказано иное.

---

## 1. Что показали замеры

| | PC1 — RTX 3090 / Ryzen 9 5950X | PC2 — RTX 3050 Laptop 4 GB / Ryzen 5 5600H |
|---|---|---|
| Выход / рендер (DLSS Quality) | 2560×1360 / 1708×908 | 1920×1080 / 1281×721 |
| FPS | ~98–111 (Lumen выкл.) | **58** (1% low 52) |
| GPU | 7.5–8.2 | **16.1** |
| Draw (Render thread) | ≈ Frame — **ожидание GPU** | 17.1, из них 6.8 ожидание, **работа ~10.2** |
| Game thread, работа | 4–6 | 3.8 |
| Во что упирается | **GPU** | **GPU, 100% кадров** |
| VRAM | — (24 GB) | **3.09 из 3.37 GB (92%)** |

**Главный вывод:** игра упирается в видеокарту на обоих ПК. `Draw ≈ Frame` в `stat unit` — это
render thread, который ждёт GPU, а не его собственная нагрузка.

### Куда уходит время GPU

| Проход | PC1 3090 | PC2 3050L | Доля на PC2 | Комментарий |
|---|---|---|---|---|
| Океан: SingleLayerWater + DepthPrepass | 1.68 | **3.67** | 23% | 3 draw call — дорогой пиксельный шейдер Oceanology |
| DLSS (Preset K, transformer) | 1.03 | **2.56** | 16% | transformer на RTX 20/30 ~2× дороже CNN |
| Тени VSM (Depths + MarkPages + Projection) | 1.04 | **~2.0** | 12% | 15 мешей без Nanite = 0.64 на PC2 |
| Unaccounted (мелкие проходы, простои) | — | 1.72 | 11% | |
| Постпроцесс без DLSS | 0.62 | 1.11 | 7% | из них 2 PP-материала: 0.23 / 0.66 |
| Rough Refraction (`r.Refraction.Blur=1`) | 0.29 | 0.52 | 3% | |
| UpdateGlobalDistanceField | 0.18 | 0.48 | 3% | обновляется из-за движущейся лодки |
| Симуляция волн в RenderTarget (WorldTick) | 0.30 | 0.45 | 3% | M_Advection, M_Pressure… |
| MotionBlur | 0.12 | 0.41 | 3% | |
| TranslucencyLightingVolume | 0.08 | 0.41 | 3% | 64³, 2 каскада |
| SSGI (только PC2, `GI Method = 2`) | — | 0.58 | 4% | на PC1 GI был выключен |
| Оверлей `stat` (DrawDebugCanvas) | 0.24 | 0.28 | 2% | только при замерах |

RTX 3050 Laptop медленнее RTX 3090 примерно в **3.2× на пиксель воды** и в **4× на DLSS**:
на слабом железе дороже всего именно вода и апскейлер.

---

## 2. Данные, которые нужно учитывать

### Про замеры

1. **Сцена самая лёгкая.** Открытый океан, 32 примитива, одна лодка, почти без эффектов. В гонке с
   соперниками, ракетами, взрывами и брызгами нагрузка будет выше — нужен замер в самой тяжёлой сцене.
2. **Development-билд.** Включены AI logging, GC verify, PIX-маркеры, Aftermath, логирование PSO.
   Для финальных цифр паковать **Test**: близко к Shipping, но `stat` и `csvprofile` работают.
3. **Оверлеи `stat` сами стоят времени:** ~0.25 ms GPU и заметно CPU. При записи CSV их выключать.
4. **Условия на ПК различались:** на PC1 `r.DynamicGlobalIlluminationMethod 0`, на PC2 — `2` (SSGI).
   Разрешение окна менялось (961 → 908 строк). Сравнивать только при одинаковых настройках.
5. **Ноутбуки:** питание от сети, режим «Производительность», замер **5–10 минут** — за 67 секунд
   не видно перегрева и сброса частот.
6. **Оконный режим.** Игра шла в окне (видна панель задач) — лишняя задержка и накладные расходы DWM.

### Про проект (из логов)

7. **Настройки проекта перекрывают Scalability.** В логе:
   `Setting ... with 'SetByScalability' was ignored as it is lower priority than ... 'SetByProjectSetting'`.
   Всё, что задано в Project Settings (`r.Shadow.Virtual.Enable`, `r.Refraction.Blur`,
   `r.Streaming.PoolSize`, `r.Shadow.MaxResolution`, `r.Shadow.CSM.MaxCascades`…), **пресеты
   качества изменить не смогут**. Такие переключатели надо делать через консольные команды из меню
   настроек (приоритет SetByConsole) или убирать из Project Settings и переносить в `DefaultScalability.ini`.
8. **Видеопамять на 4 GB почти кончилась:** 92% бюджета, ~947 MB текстур не стримятся вообще,
   а в проекте `r.Streaming.PoolSize=8000` + `r.Streaming.LimitPoolSizeToVRAM=0`.
9. **DLSS — только на RTX.** На GTX и AMD работает TSR, а его настройки в AntiAliasingQuality@3 тяжёлые
   (`r.TSR.History.ScreenPercentage 200`). Слабые не-RTX карты пока **не тестировались**.
10. **Reflex не работает:** плагин StreamlineReflex выключен (`t.Streamline.Reflex.Enable=0`).
    Задержка ввода по `stat unit` — 46–66 ms.
11. **Нет bundled PSO-кэша.** 100+ новых PSO прямо в геймплее (выстрел ракетой → новые PSO) — микрофризы
    при первом появлении эффектов.
12. **Substrate с тяжёлыми настройками:** `BytesPerPixel=170`, `ClosuresPerPixel=4`, Glints, Sheen —
    толстый GBuffer, нагрузка на память видеокарты.
13. **Следующий потолок — render thread:** на Ryzen 5 5600H его реальная работа ~10 ms (P95 12).
    После разгрузки GPU потолок этого ноутбука ~85–95 FPS; для цели 60 FPS запас есть.

---

## 3. Цели и бюджет кадра

**Целевое железо (минимум):** RTX 3050 Laptop 4 GB, 1080p, пресет Medium, DLSS Quality.
**Цель:** стабильные 60 FPS в самой тяжёлой сцене → GPU ≤ **12 ms** в лёгкой сцене (запас 4 ms на бои).

| Статья | Сейчас PC2 | Бюджет PC2 |
|---|---|---|
| Океан (SLW + prepass) | 3.67 | ≤ 2.2 |
| Апскейлер | 2.56 | ≤ 1.3 |
| Тени | ~2.0 | ≤ 1.0 |
| Постпроцесс без апскейлера | 1.11 | ≤ 0.7 |
| Освещение + прозрачность + рефракция | ~2.0 | ≤ 1.2 |
| Прочее (GDF, волны, Nanite, BasePass…) | ~4.8 | ≤ 4.0 |
| **Итого GPU** | **16.1** | **≤ 12** |
| Game thread (работа) | 3.8 | ≤ 8 |
| Render thread (работа) | 10.2 | ≤ 12 |
| VRAM | 92% | ≤ 80% бюджета |

---

## 4. Задачи

Оценки экономии — для PC2 (RTX 3050 Laptop). Перед правкой контента эффект почти любой задачи можно
проверить консольной командой из колонки «Быстрая проверка».

### P0 — настройки, без правки контента (≈ 3 ms)

| # | Задача | Экономия | Быстрая проверка |
|---|---|---|---|
| T1 | DLSS: для режимов Quality/Balanced/Performance выставить **Preset E (CNN)** вместо K. Project Settings → NVIDIA DLSS. Сравнить качество картинки | 1.0–1.5 | замер до/после |
| T2 | Выключить матовое преломление: `r.Refraction.Blur=0` в Project Settings, если нигде не нужно размытие сквозь прозрачное | 0.4–0.5 | `r.Refraction.Blur 0` |
| T3 | `M_UnderOcean_PostProcess` включать **только когда камера под водой** (Blend Weight / Enabled у PP-volume или blendable) | 0.35 | отключить volume в редакторе |
| T4 | `M_PP_BoatRace`: Blendable Location → *Before Tonemapping*, тогда материал считается в разрешении рендера (в 2.25× меньше пикселей). Проверить, что картинка не меняется | 0.15 | — |
| T5 | Видеопамять: убрать `r.Streaming.PoolSize=8000` из Project Settings, `r.Streaming.LimitPoolSizeToVRAM=1` | фризы на 4 GB | `stat streaming` |
| T6 | MotionBlur выключить на Low/Medium | 0.3–0.4 | `r.MotionBlurQuality 0` |
| T7 | Включить плагин **StreamlineReflex**, `t.Streamline.Reflex.Enable=1`, `t.Streamline.Reflex.Mode=1`, пункт в меню | задержка −20…30 ms | PresentMon / FrameView |

### P1 — контент и пресеты (≈ 2.5–3.5 ms)

| # | Задача | Экономия | Как |
|---|---|---|---|
| T8 | **Упрощённый материал океана** для Low/Medium | 1.0–1.5 | По одной отключать фичи Oceanology (пена, каустика, слои нормалей, SSS, детализация) и смотреть `GPU/SingleLayerWater`. Собрать Material Instance / Quality Switch на пресет. Проверка «пиксели или геометрия»: при `r.ScreenPercentage 50` SLW должен упасть почти вдвое |
| T9 | **Тени:** Nanite для мешей лодки (15 non-Nanite draw call), `Cast Shadow = off` у Water Body, на Low — CSM (`r.Shadow.Virtual.Enable 0`) с небольшим `Dynamic Shadow Distance`. Помнить про пункт 7 раздела 2: переключать из кода/меню | 0.5–1.0 | `r.Shadow.Virtual.Enable 0`, `stat shadowrendering` |
| T10 | **Global Distance Field:** выяснить, кто его использует (DFAO, `DistanceToNearestSurface` в материале воды, Niagara). Если никто — отключить на Low | 0.3–0.5 | `r.DistanceFieldAO 0`, `r.AOGlobalDistanceField 0`, проверить пену у бортов |
| T11 | **TranslucencyLightingVolume:** 32³ на Low/Medium или выключить, если нет освещённых прозрачных материалов | 0.2–0.4 | `r.TranslucencyLightingVolume.Dim 32` / `r.TranslucentLightingVolume 0` |
| T12 | **Симуляция волн в RenderTarget:** на Low уменьшить разрешение RT и/или обновлять через кадр | 0.2 | — |
| T13 | **SSGI** — только на High+; на Low/Medium `GI = none` | 0.6 | `r.DynamicGlobalIlluminationMethod 0` |
| T14 | **Lumen** — только High/Epic (на PC1 давал +2.2 ms). Проверить, что Low/Medium его отключают (Scalability GI/Reflections Quality ≤ 1) | 2+ на High | `r.DynamicGlobalIlluminationMethod 0`, `r.ReflectionMethod 2` |
| T15 | **Текстуры без стриминга (~947 MB):** `listtextures nonstreaming` → лог; включить mip-уровни и стриминг, ужать UI-текстуры | VRAM | `stat streaming` |

### P2 — к релизу

| # | Задача | Зачем |
|---|---|---|
| T16 | **Bundled PSO-кэш:** запуск с `-logPSO`, пройти игру со всеми эффектами, конвертировать `.rec.upipelinecache` → `.stablepc.csv`, положить в `Build/Windows/PipelineCaches`, перепаковать | убрать микрофризы при первом выстреле / эффекте |
| T17 | **Пресеты качества** Low / Medium / High / Epic в меню: собрать все пункты выше в `DefaultScalability.ini` + команды из меню для того, что задано в Project Settings | управляемая производительность |
| T18 | **Тест на не-RTX картах** (GTX 1060/1660, Radeon RX 5500/6600): TSR вместо DLSS, облегчить `AntiAliasingQuality` (`r.TSR.History.ScreenPercentage 100`) или FSR | минимальные требования |
| T19 | **Substrate:** снизить `r.Substrate.BytesPerPixel` / `ClosuresPerPixel`, выключить Glints / Sheen, если не используются; замерить BasePass + Lighting | GBuffer, пропускная способность памяти |
| T20 | **VRS ContrastAdaptiveShading** (0.24 ms async compute на PC2): замерить с `r.VRS.ContrastAdaptiveShading 0` — окупается ли | возможно −0.2 |
| T21 | **Ultra Dynamic Sky:** объёмные облака / туман / light function на Low; посмотреть, что сидит в `Unaccounted` (1.7 ms) через `stats.MaxPerGroup 60` + `stat gpu` | 0.3–1.0 |
| T22 | **Полноэкранный режим по умолчанию** + проверка `r.GTSyncType` | задержка, стабильность кадра |

### P3 — CPU, когда GPU станет ≤ 10 ms

| # | Задача |
|---|---|
| T23 | Render thread (~10 ms на 5600H): `RenderThreadOther` 2.45, `RenderOther` 1.61, `RDG_CollectResources` 1.19, `RenderShadows` 0.8 — разбирать в Unreal Insights (`-trace=default,gpu`) |
| T24 | Game thread: `TickActors` 1.1 (P95 2.1), UI 0.76 — проверить тики виджетов и Blueprint-акторов, перевести на события/таймеры |

---

## 5. Ожидаемый результат на PC2 (RTX 3050 Laptop, 1080p)

| Этап | GPU, ms | FPS |
|---|---|---|
| Сейчас | 16.1 | 58 |
| После P0 (T1–T6) | ~13 | ~75 |
| После P1 (T8–T13) | ~10–11 | ~85–95 (упор в render thread) |

---

## 6. Как проверять каждую задачу

1. Билд **Test**, полноэкранный режим, одно разрешение, `stat`-оверлеи выключены, одинаковые
   GI/Reflection методы на всех ПК.
2. Один и тот же маршрут, 60 секунд (на ноутбуке — 5 минут):
   ```
   csvprofile start
   … маршрут …
   csvprofile stop
   ```
3. Один раз `ProfileGPU` (`r.ProfileGPU.Root *`, `r.ProfileGPU.ThresholdPercent 1`).
4. Файлы в `captures/<ПК>_<дата>_<что менялось>/`, отчёт:
   ```
   python tools/ue_perf_report.py captures/<папка-до> captures/<папка-после> -o report.md
   ```
5. Задача закрыта, если целевой проход в `Топ GPU` уменьшился, а `Frame P95` не вырос.
   Визуальные изменения — скриншоты до/после из одной точки.
