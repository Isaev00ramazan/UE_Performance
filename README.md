# UE_Performance

Замеры производительности MadWater (UE 5.7) на разных ПК и скрипт, который превращает их в отчёт.

```
tools/ue_perf_report.py   — отчёт по CSV Profiler + логам (ProfileGPU, железо, PSO, CVar)
captures/<ПК>/            — файлы замеров с каждого компьютера
```

## Как снять замер на новом ПК

### 1. Запуск

Запустите упакованный билд с параметрами (можно через ярлык → «Объект»):

```
MODWATER_Build.exe -csvGpuStats -log
```

`-csvGpuStats` добавляет в CSV время каждого прохода GPU, `-log` открывает окно лога.

### 2. Условия

- Одно и то же разрешение и режим окна на всех ПК (лучше полноэкранный).
- Одна и та же точка уровня / один и тот же маршрут.
- Все `stat`-оверлеи выключены: они сами нагружают CPU и GPU.
- Фоновые программы (браузер, Discord, запись экрана) закрыты.

### 3. Команды в консоли игры (`~`), по одной строке

**Замер A — как есть (30–60 секунд):**
```
csvprofile start
```
…поиграть 30–60 секунд по одному и тому же маршруту…
```
csvprofile stop
```

**Замер B — меньшее разрешение рендера (проверка «GPU или CPU»):**
```
r.ScreenPercentage 50
csvprofile start
```
…тот же маршрут 30–60 секунд…
```
csvprofile stop
r.ScreenPercentage 66.7
```

**Замер C — разбивка GPU по проходам (одна команда = один кадр):**
```
r.ProfileGPU.Root *
r.ProfileGPU.ThresholdPercent 1
ProfileGPU
```

### 4. Какие файлы собрать

Из папки билда `…\Windows\MadWater\Saved\`:

| Файл | Где лежит |
|---|---|
| CSV замеров A и B | `Saved\Profiling\CSV\Profile(…).csv` |
| Лог с ProfileGPU и железом | `Saved\Logs\MadWater.log` |

Положить их в `captures/<имя-ПК>/` этого репозитория (например `captures/PC2_GTX1660/`)
и запушить, или просто прислать.

## Отчёт

```
python tools/ue_perf_report.py captures/PC2_GTX1660 -o captures/PC2_GTX1660/report.md
```

Нужен только Python 3.8+, без библиотек. В отчёте:

- железо, разрешение, DLSS, изменённые CVar;
- Frame / Game / Draw / RHIT / GPU: среднее, P50, P95, P99, 1% low FPS;
- **во что упирается кадр** — GPU, Game thread или Render thread;
- фризы и их вероятная причина (Game / RHI-PSO / GPU / Render);
- топ проходов GPU и функций потоков из CSV;
- дерево ProfileGPU и самые дорогие проходы;
- сравнение замеров A и B.

### Как читать «Draw ≈ Frame»

`Draw` в `stat unit` включает время, когда render thread **ждёт GPU**. Если GPU тоже близко к Frame,
то упор в видеокарту, а не в render thread. Окончательно это видно по замеру B: если при меньшем разрешении
Frame заметно падает — упор в GPU; если почти не меняется — в CPU.
