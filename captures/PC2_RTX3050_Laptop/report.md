# Отчёт по производительности

## Лог: `MadWater.log`

| Параметр | Значение |
|---|---|
| Видеопамять | 3965MB |
| Exe | MODWATER_Build.exe |
| Версия движка | 5.7.4-51494982+++UE5+Release-5.7 |
| ОС / CPU / GPU | Windows 11 (25H2) [10.0.26200.8655] (), CPU: AMD Ryzen 5 5600H with Radeon Graphics         , GPU: AMD Radeon(TM) Graphics |
| Конфигурация сборки | Development |
| Оперативная память | 35.9GB |
| Драйвер GPU | 610.62 (internal:32.0.16.1062, unified:610.62) |
| Профиль устройства | Windows |
| Выбранная видеокарта (рендер) | NVIDIA GeForce RTX 3050 Laptop GPU |
| Мониторы | 1920x1080 |
| DLSS (последний) | 1281x721 → 1920x1080 |

**Замечания:**

- NVIDIA Reflex не загружен (плагин StreamlineReflex выключен).
- Нет bundled PSO-кэша (`.stable.upipelinecache` не найден).
- Новых PSO во время работы: 112 (возможные микрофризы при первом показе эффектов).
- Блокирующие ожидания загрузки шейдеров: 2 шт., всего 478 ms.

**CVar, изменённые во время игры (последнее значение):** `r.LumenScene.PropagateGlobalLightingChange=0`, `r.SkyLight.RealTimeReflectionCapture.TimeSlice.SkyCloudCubeFacePerFrame=1`, `r.VolumetricCloud.ApplyFogLate=-1`, `r.LightFunctionAtlas.SlotResolution=512`, `r.OIT.SortedPixels.PassType=2`, `r.SkyAtmosphere.EditorNotifications=0`, `r.LightFunctionQuality=2`, `r.EyeAdaptation.BlackHistogramBucketInfluence=0.5`, `r.ScreenPercentage=66.7`, `r.TSR.ShadingRejection.Flickering=0`, `r.TSR.ShadingRejection.Flickering.Period=0`, `r.ReflectionMethod=2`, `r.DynamicGlobalIlluminationMethod=2`, `r.ProfileGPU.ThresholdPercent=1`, `r.NGX.DLSS.DenoiserMode=0`

### ProfileGPU, кадр 17603, очередь Compute 0: 0.38 ms

```
Inclusive    Excl  Draws     Prims  Событие
    0.380   0.000      0         0    Frame 17472
    0.353   0.001      0         0      SceneRender - ViewFamilies
    0.352   0.002      0         0        RenderGraphExecute - /ViewFamilies
    0.351   0.005      0         0          Scene
    0.254   0.017      0         0            PrepareImageBasedVRS
    0.237   0.237      0         0              ContrastAdaptiveShading
    0.076   0.001      0         0            Substrate
    0.075   0.075      0         0              Substrate::MaterialClassification
```

Самые дорогие проходы (собственное время, без вложенных):

| Проход | Excl, ms | % кадра |
|---|---|---|
| ContrastAdaptiveShading | 0.237 | 62.4% |
| Substrate::MaterialClassification | 0.075 | 19.7% |
| PrepareImageBasedVRS | 0.017 | 4.5% |
| Scene | 0.005 | 1.3% |
| CaptureConvolveSkyEnvMap | 0.005 | 1.3% |
| M_Pressure | 0.004 | 1.1% |
| DeferredDecals BeforeBasePass | 0.004 | 1.1% |
| Capture Face=2 | 0.003 | 0.8% |
| RenderGraphExecute - /ViewFamilies | 0.002 | 0.5% |
| RenderGraphExecute - CanvasRenderThreadScope | 0.001 | 0.3% |
| SceneRender - ViewFamilies | 0.001 | 0.3% |
| Substrate | 0.001 | 0.3% |

### ProfileGPU, кадр 17603, очередь Graphics 0: 15.65 ms

```
Inclusive    Excl  Draws     Prims  Событие
   15.643   0.029    251   1780937    Frame 17472
    0.446   0.013      8        16      WorldTick
   14.785   0.092    181   1774523      SceneRender - ViewFamilies
   14.689   0.173    181   1774523        RenderGraphExecute - /ViewFamilies
    0.481   0.004      0         0          UpdateGlobalDistanceField
    0.477   0.141      0         0            Update Movable
    0.336   0.336      0         0              Coarse Clipmap
    0.313   0.001      0         0          Nanite::Streaming
    0.311   0.311      0         0            Nanite::Readback
   13.630   0.282    181   1774523          Scene
    0.213   0.001      0         0            VisibilityCommands
    0.289   0.078     16    492387            PrePass DDM_AllOpaque (Forced by Nanite)
    0.211   0.211     16    492387              ParallelDraw (Index: 0, Num: 1)
    0.350   0.001     12         0            Nanite::VisBuffer
    0.349   0.037     12         0              Nanite::DrawGeometry
    0.166   0.098      6         0                MainPass
    0.344   0.171      5    143426            SingleLayerWaterDepthPrepass
    0.173   0.173      3    143424              ParallelDraw (Index: 0, Num: 1)
    0.615   0.071     17    497123            BasePass
    0.270   0.270     16    492387              ParallelDraw (Index: 0, Num: 1)
    0.184   0.184      1      4736              ParallelDraw (Index: 0, Num: 1)
    0.163   0.001      0         0            VirtualShadowMapMarkPages
    0.162   0.000      0         0              ShadowDepths
    0.162   0.162      0         0                FVirtualShadowMapArray::BeginMarkPages
    1.315   0.009     27         0            ShadowDepths
    0.397   0.035     12         0              RenderVirtualShadowMaps(Nanite)
    0.362   0.053     12         0                Nanite::DrawGeometry
    0.227   0.095      6         0                  MainPass
    0.723   0.000     15         0              RenderVirtualShadowMaps(Non-Nanite)
    0.723   0.637     15         0                Batched
    0.240   0.026     16    492387            RenderVelocities(Opaque)
    0.214   0.214     16    492387              ParallelDraw (Index: 0, Num: 1)
    1.509   0.003     20       691            RenderDeferredLighting
    0.580   0.120      3         0              DiffuseIndirectAndAO
    0.179   0.179      0         0                SSGI 641x361
    0.371   0.000     11       434              Lights
    0.371   0.022     11       434                DirectLighting
    0.348   0.000      8       434                  UnbatchedLights
    0.348   0.121      8       434                    12.Ultra_Dynamic_Sky
    0.227   0.172      4         2                      ShadowProjectionOnOpaque
    0.410   0.000      2       256              TranslucencyLightingVolume
    0.227   0.227      2       256                InjectTranslucencyLightingVolume(View=0)
    0.183   0.183      0         0                FilterTranslucentVolume 64x64x64 Cascades:2
    2.864   0.096      7    143425            SingleLayerWater
    2.575   0.029      3    143424              SLW::Draw
    2.546   2.546      3    143424                ParallelDraw (Index: 0, Num: 1)
    0.676   0.002      9        31            Translucency
    0.564   0.001      5        17              Distortion
    0.521   0.003      1         1                Rough Refraction View0
    0.171   0.171      0         0                  TAA
    3.923   0.204     21        21            PostProcessing
    0.345   0.345      1         1              PostProcessMaterial 1281x721 Material=M_UnderOcean_PostProcess_Volume_Inst
    2.538   0.000      0         0              ThirdParty FDLSSSceneViewFamilyUpscaler 1281x721 -> 1920x1080
    2.538   2.537      0         0                DLSS
    0.217   0.113      0         0              MotionBlur
    0.185   0.185     12        12              Bloom
    0.318   0.318      1         1              PostProcessMaterial 1920x1080 Material=M_PP_BoatRace
    0.382   0.026     62      6398      RenderGraphExecute - Slate
    0.356   0.016     62      6398        SlateUI Title = MadWater (64-bit Development PCD3D_SM6)
    0.276   0.001     25      5978          DrawDebugCanvas
    0.275   0.275     25      5978            CanvasFlush
```

Самые дорогие проходы (собственное время, без вложенных):

| Проход | Excl, ms | % кадра |
|---|---|---|
| ParallelDraw (Index: 0, Num: 1) | 2.546 | 16.3% |
| DLSS | 2.537 | 16.2% |
| Batched | 0.637 | 4.1% |
| PostProcessMaterial 1281x721 Material=M_UnderOcean_PostProcess_Volume_Inst | 0.345 | 2.2% |
| Coarse Clipmap | 0.336 | 2.1% |
| PostProcessMaterial 1920x1080 Material=M_PP_BoatRace | 0.318 | 2.0% |
| Nanite::Readback | 0.311 | 2.0% |
| Scene | 0.282 | 1.8% |
| CanvasFlush | 0.275 | 1.8% |
| ParallelDraw (Index: 0, Num: 1) | 0.270 | 1.7% |
| InjectTranslucencyLightingVolume(View=0) | 0.227 | 1.5% |
| ParallelDraw (Index: 0, Num: 1) | 0.214 | 1.4% |

## CSV: `Profile20261006_222409.csv`

| Параметр | Значение |
|---|---|
| platform | Windows |
| config | Development |
| cpu | AuthenticAMD|AMD Ryzen 5 5600H with Radeon Graphics |
| os | Windows 11 (25H2) [10.0.26200.8655] |
| commandline | MadWater -csvGpuStats -log |
| deviceprofile | Windows |
| systemresolution.resx | 1278 |
| systemresolution.resy | 719 |
| engineversion | 5.7.4-51494982+++UE5+Release-5.7 |

Кадров: **3913**, длительность: **67.0 с**, средний FPS: **58.4**, FPS по медиане: **58.1**, 1% low FPS: **51.9**

| Метрика, ms | Среднее | P50 | P95 | P99 | Max |
|---|---|---|---|---|---|
| Frame | 17.11 | 17.21 | 18.72 | 19.26 | 20.95 |
| Game | 4.34 | 4.15 | 5.83 | 7.06 | 15.53 |
| Draw | 17.09 | 17.11 | 19.07 | 20.14 | 21.90 |
| RHIT | 5.99 | 5.88 | 7.24 | 8.37 | 10.26 |
| GPU | 16.13 | 16.24 | 17.18 | 17.55 | 19.36 |

### Во что упирается

**GPU** — видеокарта занята почти весь кадр.

- Draw тоже близок к Frame — render thread ждёт GPU, это не его собственная работа.
- GPU занят 94% времени кадра (по медиане).

Упор по кадрам (доля кадров): GPU 100%, Game 0%, Render 0%, Другое 0%

### Потоки CPU: работа и ожидание (ms, по Exclusive-статам)

| Поток | Всего | Ожидание (EventWait) | Работа | Работа P95 |
|---|---|---|---|---|
| Game | 16.64 | 12.87 | 3.77 | 5.26 |
| Draw (Render) | 17.08 | 6.84 | 10.24 | 12.10 |

Если «Работа» намного меньше Frame, поток не узкое место — он ждёт GPU или другой поток.

### Фризы (кадр > 34.4 ms = 2x медианы)

Нет.

### Топ `GPU` (ms)

| Что | Среднее | P95 | Max |
|---|---|---|---|
| SingleLayerWater | 3.30 | 3.56 | 4.16 |
| DLSS | 2.56 | 2.61 | 2.66 |
| ShadowDepths | 1.74 | 2.36 | 3.07 |
| Unaccounted | 1.72 | 2.21 | 3.09 |
| Postprocessing | 1.11 | 1.14 | 1.21 |
| RenderDeferredLighting | 0.53 | 0.63 | 0.66 |
| BasePass | 0.48 | 0.50 | 0.53 |
| MotionBlur | 0.41 | 0.58 | 0.68 |
| SingleLayerWaterDepthPrepass | 0.37 | 0.41 | 0.46 |
| NaniteVisBuffer | 0.35 | 0.38 | 0.70 |
| CanvasDrawTiles | 0.35 | 0.52 | 0.85 |
| Prepass | 0.25 | 0.34 | 0.65 |
| Distortion | 0.24 | 0.42 | 0.61 |
| NaniteReadback | 0.24 | 0.34 | 0.67 |
| RenderVelocities | 0.23 | 0.24 | 0.27 |

### Топ `Exclusive/GameThread` (ms)

| Что | Среднее | P95 | Max |
|---|---|---|---|
| EventWait | 12.75 | 14.62 | 17.05 |
| TickActors | 1.12 | 2.06 | 4.02 |
| UI | 0.76 | 1.10 | 2.17 |
| ViewportMisc | 0.31 | 1.24 | 2.82 |
| Effects | 0.21 | 0.30 | 1.06 |
| SyncBodies | 0.15 | 0.26 | 0.95 |
| PlayerControllerTick | 0.14 | 0.26 | 0.99 |
| WorldTickMisc | 0.11 | 0.16 | 3.62 |
| DebugHUD | 0.10 | 0.18 | 0.55 |
| Physics | 0.10 | 0.14 | 0.93 |
| PostProcessSettings | 0.10 | 0.14 | 0.81 |
| Animation | 0.09 | 0.16 | 0.82 |
| EndOfFrameUpdates | 0.09 | 0.13 | 0.67 |
| EngineTickMisc | 0.08 | 0.11 | 0.37 |
| TimerManager | 0.08 | 0.25 | 0.93 |

### Топ `Exclusive/RenderThread` (ms)

| Что | Среднее | P95 | Max |
|---|---|---|---|
| EventWait/Visibility | 6.83 | 8.24 | 10.57 |
| RenderThreadOther | 2.45 | 3.06 | 4.34 |
| RenderOther | 1.61 | 2.08 | 3.90 |
| RDG_CollectResources | 1.19 | 1.59 | 3.27 |
| RDG | 0.80 | 1.13 | 3.04 |
| RenderShadows | 0.80 | 1.06 | 2.16 |
| RenderLighting | 0.46 | 0.63 | 1.19 |
| RenderPostProcessing | 0.30 | 0.43 | 0.97 |
| Material_UpdateDeferredCachedUniformExpressions | 0.30 | 0.40 | 0.95 |
| RDG_Execute | 0.27 | 0.42 | 1.15 |
| InitRenderResource | 0.27 | 0.37 | 3.29 |
| PrepareDistanceFieldScene | 0.20 | 0.31 | 1.64 |
| Slate | 0.18 | 0.35 | 1.31 |
| Niagara | 0.18 | 0.37 | 2.39 |
| RenderTranslucency | 0.16 | 0.34 | 0.86 |

