# PC2 — RTX 3050 Laptop 4 GB / Ryzen 5 5600H / 36 GB

- Билд: Development, UE 5.7.4, D3D12 SM6, рендер на RTX 3050 Laptop (адаптер 0)
- 1920×1080, DLSS Quality (Preset K, transformer) 1281×721 → 1920×1080
- Изменено в консоли: `r.ReflectionMethod 2` (SSR), `r.DynamicGlobalIlluminationMethod 2` (**SSGI**, не «выкл»)
- CSV: 3913 кадров / 67 с, `-csvGpuStats`; ProfileGPU — кадр 17603. Полный разбор — `report.md`

## Итог

| | Среднее | P50 | P95 | P99 |
|---|---|---|---|---|
| FPS | 58.4 | 58.1 | — | 1% low 51.9 |
| Frame, ms | 17.11 | 17.21 | 18.72 | 19.26 |
| GPU, ms | 16.13 | 16.24 | 17.18 | 17.55 |
| Draw (Render), ms | 17.09 | 17.11 | 19.07 | 20.14 |
| Game, ms | 4.34 | 4.15 | 5.83 | 7.06 |

**Упор в GPU в 100% кадров** (GPU занят 94% кадра). Фризов > 2× медианы нет.

Draw ≈ Frame — это ожидание: из 17.1 ms render thread 6.8 ms стоит в `EventWait/Visibility`,
реальная работа ≈ 10.2 ms (P95 12.1). Game thread работает 3.8 ms, остальное ждёт.
→ После оптимизации GPU следующий потолок на этом CPU — render thread, около 85–95 FPS.

## GPU по проходам (CSV, среднее за 67 с)

| Проход | ms | % от 16.1 | PC1 (RTX 3090), ms |
|---|---|---|---|
| SingleLayerWater + DepthPrepass | 3.67 | 23% | 1.68 |
| DLSS (Preset K) | 2.56 | 16% | 1.03 |
| ShadowDepths (VSM, из них Non-Nanite 0.64) | 1.74 | 11% | 0.82 |
| Unaccounted | 1.72 | 11% | — |
| Postprocessing (без DLSS; 2 PP-материала 0.66) | 1.11 | 7% | 0.62 |
| RenderDeferredLighting (SSGI+AO 0.58, TranslucencyLightingVolume 0.41) | 0.53–1.51 | — | 0.32 |
| UpdateGlobalDistanceField (ProfileGPU) | 0.48 | 3% | 0.18 |
| Rough Refraction (ProfileGPU) | 0.52 | 3% | 0.29 |
| MotionBlur | 0.41 | 3% | 0.12 |
| WorldTick — симуляция волн (ProfileGPU) | 0.45 | 3% | 0.30 |

Масштаб: на пиксель RTX 3050 Laptop в ~3.2× медленнее на воде и в ~4× на DLSS, чем RTX 3090.

## Видеопамять

- Использовано 3090 MB из бюджета 3370 MB (**92%**).
- `NonStreamingMips` = **947 MB** — текстуры, которые не стримятся (всегда целиком в VRAM).
- В проекте `r.Streaming.PoolSize=8000` и `r.Streaming.LimitPoolSizeToVRAM=0` — на 4 GB это
  пул больше видеопамяти; при более тяжёлой сцене будут фризы от вытеснения в системную память.
