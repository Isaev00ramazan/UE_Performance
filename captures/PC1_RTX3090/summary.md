# PC1 — RTX 3090 / Ryzen 9 5950X / 64 GB (точка отсчёта)

- Билд: Development, UE 5.7.4, D3D12 SM6
- Окно 2560×1360, DLSS Quality (Preset K, transformer) 1708×908 → 2560×1360
- Изменено в консоли: `r.DynamicGlobalIlluminationMethod 0`, `r.ReflectionMethod 0` (Lumen выключен)
- Reflex не загружен (плагин StreamlineReflex выключен), bundled PSO-кэша нет

## stat unit

| Состояние | FPS | Frame | Game | Draw | RHIT | GPU | Input |
|---|---|---|---|---|---|---|---|
| Lumen включён | ~80 | 12.2 | 5.8–6.2 | 12.2 | 7.0–7.4 | 10.4 | ~50 |
| Lumen выключен | ~98–111 | 9.2–10.1 | 4.2–5.6 | 9.2–10.1 | 5.7–6.6 | 8.2 | 46–52 |
| r.ScreenPercentage 100 (Lumen вкл.) | ~64 | 15.2 | 4.6 | 14.9 | 10.4 | 13.7 | 66 |

Вывод: упор в GPU, `Draw ≈ Frame` — render thread ждёт видеокарту (Draw растёт вместе с GPU при росте разрешения).

## ProfileGPU (Lumen выключен), Graphics queue = 7.54 ms

| Проход | ms | % |
|---|---|---|
| SingleLayerWater (SLW::Draw — 3 draw call, пиксельный шейдер Oceanology) | 1.51 | 20.0 |
| PostProcessing, из них DLSS 1.03 | 1.65 | 21.9 |
| ShadowDepths (VSM: Nanite 0.39, Non-Nanite 0.28) | 0.82 | 10.9 |
| Translucency (Rough Refraction 0.29) | 0.42 | 5.6 |
| RenderDeferredLighting | 0.32 | 4.2 |
| Slate (из них 0.24 — оверлей stat) | 0.30 | 4.0 |
| WorldTick (симуляция волн в RenderTarget) | 0.30 | 4.0 |
| Nanite::VisBuffer | 0.29 | 3.8 |
| BasePass | 0.27 | 3.5 |
| UpdateGlobalDistanceField | 0.18 | 2.4 |
| SingleLayerWaterDepthPrepass | 0.17 | 2.2 |
| M_UnderOcean_PostProcess (работает и над водой) | 0.12 | 1.5 |
| M_PP_BoatRace (в выходном разрешении) | 0.11 | 1.5 |
