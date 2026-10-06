#!/usr/bin/env python3
"""Сводка по профилированию Unreal Engine.

Принимает файлы CSV Profiler (Saved/Profiling/CSV/*.csv) и логи игры
(Saved/Logs/*.log, в том числе с выводом ProfileGPU) и печатает отчёт в Markdown:
  - железо и условия теста (из лога);
  - Frame / Game / Draw / RHI / GPU: среднее, перцентили, во что упирается кадр;
  - фризы (кадры дольше 2x медианы) и чем они вызваны;
  - самые дорогие проходы GPU и функции потоков (если они есть в CSV);
  - дерево ProfileGPU из лога;
  - сравнение нескольких CSV между собой (например, 100% и 50% разрешения).

Только стандартная библиотека Python 3.8+.

Примеры:
  python ue_perf_report.py captures/PC2
  python ue_perf_report.py Profile1.csv Profile2.csv MadWater.log -o report.md
"""

import argparse
import csv
import os
import re
import statistics
import sys

# Основные метрики CSV Profiler и запасные имена колонок.
CORE_STATS = [
    ("Frame", ["FrameTime"]),
    ("Game", ["GameThreadTime", "GameThreadTime_CriticalPath"]),
    ("Draw", ["RenderThreadTime", "RenderThreadTime_CriticalPath"]),
    ("RHIT", ["RHIThreadTime"]),
    ("GPU", ["GPUTime", "GPU/Total", "GPUTime_GPU0"]),
]

# Группы колонок, для которых выводится топ по среднему времени.
DETAIL_GROUPS = ["GPU", "Exclusive/GameThread", "Exclusive/RenderThread"]

LOG_PREFIX_RE = re.compile(r"^\[[^\]]*\]\[\s*\d+\]")
CVAR_SET_RE = re.compile(r"^\[[^\]]*\]\[\s*\d+\]([A-Za-z][\w.]*) = \"(.*)\"\s*$")


def percentile(sorted_values, p):
    if not sorted_values:
        return float("nan")
    k = (len(sorted_values) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def fmt(v, digits=2):
    if v is None or v != v:
        return "—"
    return f"{v:.{digits}f}"


# ---------------------------------------------------------------- CSV ---------

class CsvCapture:
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.header = []
        self.columns = {}
        self.metadata = {}
        self._load()

    def _load(self):
        with open(self.path, newline="", encoding="utf-8-sig", errors="replace") as f:
            rows = list(csv.reader(f))
        if not rows:
            raise ValueError("пустой файл")
        self.header = [h.strip() for h in rows[0]]
        data = {h: [] for h in self.header}
        for row in rows[1:]:
            if not row:
                continue
            if row[0].startswith("["):
                self._parse_metadata(row)
                continue
            if [c.strip() for c in row] == self.header:
                continue
            for i, h in enumerate(self.header):
                cell = row[i].strip() if i < len(row) else ""
                try:
                    data[h].append(float(cell))
                except ValueError:
                    data[h].append(None)
        self.columns = data

    def _parse_metadata(self, row):
        for i in range(0, len(row) - 1, 2):
            key = row[i].strip()
            if key.startswith("[") and key.endswith("]"):
                self.metadata[key[1:-1]] = row[i + 1].strip()

    def column(self, candidates):
        lowered = {h.lower(): h for h in self.header}
        for c in candidates:
            if c.lower() in lowered:
                return self.columns[lowered[c.lower()]]
        return None

    def numeric(self, values):
        return [v for v in values if v is not None] if values else []

    def core(self):
        return {label: self.column(names) for label, names in CORE_STATS}


def summarize_stat(values):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    return {
        "avg": statistics.fmean(vals),
        "p50": percentile(vals, 50),
        "p95": percentile(vals, 95),
        "p99": percentile(vals, 99),
        "max": vals[-1],
    }


def verdict(med):
    frame, game, draw, gpu = med.get("Frame"), med.get("Game"), med.get("Draw"), med.get("GPU")
    if not frame:
        return "не хватает данных FrameTime"
    notes = []
    if gpu and gpu >= 0.85 * frame:
        main = "**GPU** — видеокарта занята почти весь кадр."
        if draw and draw >= 0.85 * frame:
            notes.append("Draw тоже близок к Frame — render thread ждёт GPU, это не его собственная работа.")
    elif game and game >= 0.85 * frame:
        main = "**Game thread** — CPU-логика игры (тики, Blueprint, физика, анимации)."
    elif draw and draw >= 0.85 * frame:
        main = "**Render thread (CPU)** — GPU заметно ниже кадра, render thread реально нагружен."
        notes.append("Проверить: stat InitViews, stat SceneRendering, число draw calls, Unreal Insights.")
    else:
        main = "**не упирается ни во что явно** — вероятно, лимит FPS / VSync / простои синхронизации."
    if gpu and frame:
        notes.append(f"GPU занят {gpu / frame * 100:.0f}% времени кадра (по медиане).")
    return main + ("\n\n" + "\n".join(f"- {n}" for n in notes) if notes else "")


def classify_frame(f, game, draw, gpu):
    """Та же логика, что в verdict(), но для одного кадра."""
    if gpu is not None and gpu >= 0.85 * f:
        return "GPU"
    if game is not None and game >= 0.85 * f:
        return "Game"
    if draw is not None and draw >= 0.85 * f and (gpu is None or gpu < 0.75 * f):
        return "Render"
    return "Другое"


def limiter_shares(core):
    frame = core.get("Frame")
    if not frame:
        return {}
    counts = {"GPU": 0, "Game": 0, "Render": 0, "Другое": 0}
    total = 0

    def at(label, i):
        col = core.get(label)
        return col[i] if col and i < len(col) else None

    for i, f in enumerate(frame):
        if not f:
            continue
        counts[classify_frame(f, at("Game", i), at("Draw", i), at("GPU", i))] += 1
        total += 1
    return {k: v * 100.0 / total for k, v in counts.items()} if total else {}


def report_csv(cap, out, top_n):
    core = cap.core()
    frame = cap.numeric(core["Frame"])
    out.append(f"## CSV: `{cap.name}`\n")
    if not frame:
        out.append("Нет колонки FrameTime — это не CSV Profiler или файл повреждён.\n")
        return None

    meta_keys = ["platform", "config", "cpu", "os", "commandline", "deviceprofile",
                 "systemresolution.resx", "systemresolution.resy", "engineversion"]
    meta = [(k, cap.metadata[k]) for k in meta_keys if cap.metadata.get(k)]
    if meta:
        out.append("| Параметр | Значение |\n|---|---|")
        out.extend(f"| {k} | {v} |" for k, v in meta)
        out.append("")

    duration_s = sum(frame) / 1000.0
    out.append(f"Кадров: **{len(frame)}**, длительность: **{duration_s:.1f} с**, "
               f"средний FPS: **{len(frame) / duration_s:.1f}**, "
               f"FPS по медиане: **{1000.0 / percentile(sorted(frame), 50):.1f}**, "
               f"1% low FPS: **{1000.0 / percentile(sorted(frame), 99):.1f}**\n")

    out.append("| Метрика, ms | Среднее | P50 | P95 | P99 | Max |\n|---|---|---|---|---|---|")
    medians = {}
    for label, _ in CORE_STATS:
        s = summarize_stat(core[label] or [])
        if s is None:
            out.append(f"| {label} | нет данных | | | | |")
            continue
        medians[label] = s["p50"]
        out.append(f"| {label} | {fmt(s['avg'])} | {fmt(s['p50'])} | {fmt(s['p95'])} | "
                   f"{fmt(s['p99'])} | {fmt(s['max'])} |")
    out.append("")

    out.append("### Во что упирается\n")
    out.append(verdict(medians) + "\n")
    shares = limiter_shares(core)
    if shares:
        out.append("Упор по кадрам (доля кадров): " +
                   ", ".join(f"{k} {v:.0f}%" for k, v in shares.items()) + "\n")

    report_hitches(core, out)
    for group in DETAIL_GROUPS:
        report_group(cap, group, out, top_n)
    return medians


def report_hitches(core, out):
    frame = core["Frame"]
    vals = sorted(v for v in frame if v is not None)
    med = percentile(vals, 50)
    threshold = 2 * med
    idx = [i for i, v in enumerate(frame) if v is not None and v > threshold]
    duration_min = sum(vals) / 60000.0
    out.append(f"### Фризы (кадр > {threshold:.1f} ms = 2x медианы)\n")
    if not idx:
        out.append("Нет.\n")
        return
    out.append(f"Всего: **{len(idx)}** ({len(idx) / max(duration_min, 1e-9):.1f} в минуту). Худшие:\n")
    out.append("| Кадр # | Frame | Game | Draw | RHIT | GPU | Вероятная причина |\n|---|---|---|---|---|---|---|")
    worst = sorted(idx, key=lambda i: frame[i], reverse=True)[:10]

    def at(label, i):
        col = core.get(label)
        return col[i] if col and i < len(col) else None

    medians = {}
    for label in ("Game", "Draw", "RHIT", "GPU"):
        col = sorted(v for v in (core.get(label) or []) if v is not None)
        if col:
            medians[label] = percentile(col, 50)
    names = {"Game": "Game thread", "Draw": "Render thread", "RHIT": "RHI thread (часто компиляция PSO)", "GPU": "GPU"}

    for i in worst:
        vals = {k: at(k, i) for k in ("Frame", "Game", "Draw", "RHIT", "GPU")}
        # Причина — метрика, выросшая сильнее всего относительно своей медианы.
        # Draw растёт и когда render thread просто ждёт, поэтому его берём,
        # только если ни Game, ни RHIT, ни GPU не объясняют скачок.
        growth = {k: vals[k] - medians[k] for k in ("Game", "RHIT", "GPU")
                  if vals.get(k) is not None and k in medians}
        jump = vals["Frame"] - med
        cause = "?"
        if growth and max(growth.values()) >= 0.5 * jump:
            cause = names[max(growth, key=growth.get)]
        elif vals.get("Draw") is not None and "Draw" in medians:
            cause = names["Draw"]
        out.append(f"| {i} | {fmt(vals['Frame'])} | {fmt(vals['Game'])} | {fmt(vals['Draw'])} | "
                   f"{fmt(vals['RHIT'])} | {fmt(vals['GPU'])} | {cause} |")
    out.append("")


def report_group(cap, group, out, top_n):
    prefix = group + "/"
    rows = []
    for h in cap.header:
        if not h.startswith(prefix):
            continue
        name = h[len(prefix):]
        if name.lower() in ("total", "frametime"):
            continue
        vals = sorted(v for v in cap.columns[h] if v is not None)
        if not vals:
            continue
        avg = statistics.fmean(vals)
        if avg <= 0:
            continue
        rows.append((avg, percentile(vals, 95), vals[-1], name))
    if not rows:
        return
    rows.sort(reverse=True)
    out.append(f"### Топ `{group}` (ms)\n")
    out.append("| Что | Среднее | P95 | Max |\n|---|---|---|---|")
    for avg, p95, mx, name in rows[:top_n]:
        out.append(f"| {name} | {fmt(avg)} | {fmt(p95)} | {fmt(mx)} |")
    out.append("")


def report_comparison(results, out):
    if len(results) < 2:
        return
    out.append("## Сравнение CSV (медианы, ms)\n")
    labels = [label for label, _ in CORE_STATS]
    out.append("| Файл | " + " | ".join(labels) + " | FPS |")
    out.append("|---|" + "---|" * (len(labels) + 1))
    for name, med in results:
        frame = med.get("Frame")
        fps = 1000.0 / frame if frame else None
        out.append(f"| {name} | " + " | ".join(fmt(med.get(l)) for l in labels) + f" | {fmt(fps, 1)} |")
    out.append("\nЕсли при меньшем `r.ScreenPercentage` Frame и GPU заметно падают — упор в GPU. "
               "Если почти не меняются — упор в CPU (Game или Render thread).\n")


# ---------------------------------------------------------------- LOG ---------

HW_PATTERNS = [
    ("ОС / CPU / GPU", re.compile(r"LogInit: OS: (.*)$")),
    ("Оперативная память", re.compile(r"Memory total: Physical=(\S+)")),
    ("Видеопамять", re.compile(r"Adapter has (\d+MB) of dedicated video memory")),
    ("Драйвер GPU", re.compile(r"LogRHI:\s+Driver Version: (.*)$")),
    ("Конфигурация сборки", re.compile(r"Build Configuration: (\w+)")),
    ("Версия движка", re.compile(r"LogInit: Engine Version: (\S+)")),
    ("Exe", re.compile(r"ExecutableName: (.*)$")),
    ("Профиль устройства", re.compile(r"Active device profile: .*\] (\w+)\s*$")),
]


def strip_prefix(line):
    return LOG_PREFIX_RE.sub("", line, count=1)


def parse_profilegpu(lines):
    """Возвращает список таблиц ProfileGPU: {frame, queue, frame_ms, rows}."""
    tables = []
    cur = None
    head_re = re.compile(r"GPU Profile for Frame (\d+) - (.+?) - GPU (\d+)")
    ft_re = re.compile(r"- Frame Time\s*:\s*([\d.]+)ms")
    for raw in lines:
        if "LogRHI: Display:" not in raw:
            continue
        content = raw.split("LogRHI: Display:", 1)[1]
        m = head_re.search(content)
        if m:
            cur = {"frame": m.group(1), "queue": m.group(2), "frame_ms": None, "rows": []}
            tables.append(cur)
            continue
        if cur is None:
            continue
        m = ft_re.search(content)
        if m:
            cur["frame_ms"] = float(m.group(1))
            continue
        if "┃" not in content:
            continue
        parts = content.split("┃")
        if len(parts) < 5 or "Draws" in parts[1] or "Exclusive" in parts[1]:
            continue
        excl, incl, event = parts[1].split("│"), parts[2].split("│"), parts[3]
        try:
            excl_ms = float(excl[-1].replace("ms", "").strip())
            incl_ms = float(incl[-1].replace("ms", "").strip())
            draws = int(incl[0].strip())
            prims = int(incl[2].strip())
        except (ValueError, IndexError):
            continue
        name = event.rstrip()
        indent = len(name) - len(name.lstrip())
        cur["rows"].append({
            "name": name.strip(), "depth": max(0, (indent - 1) // 3),
            "excl": excl_ms, "incl": incl_ms, "draws": draws, "prims": prims,
        })
    return [t for t in tables if t["rows"]]


def report_log(path, out, min_ms):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        lines = f.read().splitlines()
    out.append(f"## Лог: `{os.path.basename(path)}`\n")

    hw = {}
    for line in lines:
        for label, rx in HW_PATTERNS:
            if label in hw:
                continue
            m = rx.search(line)
            if m:
                hw[label] = m.group(1).strip()
    monitors = sorted({m.group(1) for l in lines for m in [re.search(r"LogWindows:\s+resolution: (\d+x\d+)", l)] if m})
    if monitors:
        hw["Мониторы"] = ", ".join(monitors)
    dlss = [re.search(r"Creating\s+NGX DLSS Feature\s+SrcRect=\[0x0->(\d+x\d+)\], DestRect=\[0x0->(\d+x\d+)\]", l) for l in lines]
    dlss = [m for m in dlss if m]
    if dlss:
        hw["DLSS (последний)"] = f"{dlss[-1].group(1)} → {dlss[-1].group(2)}"
    if hw:
        out.append("| Параметр | Значение |\n|---|---|")
        out.extend(f"| {k} | {v} |" for k, v in hw.items())
        out.append("")

    flags = []
    if any("Skipping loading Streamline Reflex" in l for l in lines):
        flags.append("NVIDIA Reflex не загружен (плагин StreamlineReflex выключен).")
    if any("Could not open FPipelineCacheFile" in l for l in lines):
        flags.append("Нет bundled PSO-кэша (`.stable.upipelinecache` не найден).")
    pso = sum(1 for l in lines if "Encountered a new graphics PSO" in l or "Encountered a new compute PSO" in l)
    if pso:
        flags.append(f"Новых PSO во время работы: {pso} (возможные микрофризы при первом показе эффектов).")
    waits = [float(m.group(1)) for l in lines for m in [re.search(r"Spent ([\d.]+) ms in a blocking wait", l)] if m]
    if waits:
        flags.append(f"Блокирующие ожидания загрузки шейдеров: {len(waits)} шт., всего {sum(waits):.0f} ms.")
    if flags:
        out.append("**Замечания:**\n")
        out.extend(f"- {f}" for f in flags)
        out.append("")

    cvars = {}
    for line in lines:
        m = CVAR_SET_RE.match(line)
        if m:
            cvars[m.group(1)] = m.group(2)
    if cvars:
        out.append("**CVar, изменённые во время игры (последнее значение):** " +
                   ", ".join(f"`{k}={v}`" for k, v in cvars.items()) + "\n")

    for t in parse_profilegpu(lines):
        if t["queue"].startswith("Copy"):
            continue
        out.append(f"### ProfileGPU, кадр {t['frame']}, очередь {t['queue']}: {fmt(t['frame_ms'])} ms\n")
        out.append("```")
        out.append(f"{'Inclusive':>9} {'Excl':>7} {'Draws':>6} {'Prims':>9}  Событие")
        for r in t["rows"]:
            if r["incl"] < min_ms or r["name"] in ("<root>",):
                continue
            out.append(f"{r['incl']:9.3f} {r['excl']:7.3f} {r['draws']:6d} {r['prims']:9d}  "
                       f"{'  ' * r['depth']}{r['name']}")
        out.append("```\n")
        leaves = [r for r in t["rows"] if r["name"] != "<root>" and not r["name"].startswith("Frame ")]
        leaves = sorted(leaves, key=lambda r: r["excl"], reverse=True)[:12]
        out.append("Самые дорогие проходы (собственное время, без вложенных):\n")
        out.append("| Проход | Excl, ms | % кадра |\n|---|---|---|")
        for r in leaves:
            share = r["excl"] / t["frame_ms"] * 100 if t["frame_ms"] else 0
            out.append(f"| {r['name']} | {r['excl']:.3f} | {share:.1f}% |")
        out.append("")


# ---------------------------------------------------------------- main --------

def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for n in sorted(names):
                    if n.lower().endswith((".csv", ".log", ".txt")):
                        files.append(os.path.join(root, n))
        else:
            files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description="Отчёт по CSV Profiler и логам Unreal Engine.")
    ap.add_argument("paths", nargs="+", help="CSV/лог файлы или папки с ними")
    ap.add_argument("-o", "--output", help="записать отчёт в файл (UTF-8) вместо вывода в консоль")
    ap.add_argument("--top", type=int, default=15, help="сколько строк в топах (по умолчанию 15)")
    ap.add_argument("--min-ms", type=float, default=0.05,
                    help="порог для дерева ProfileGPU, ms (по умолчанию 0.05)")
    args = ap.parse_args()

    out = ["# Отчёт по производительности\n"]
    results = []
    for path in collect(args.paths):
        try:
            if path.lower().endswith(".csv"):
                medians = report_csv(CsvCapture(path), out, args.top)
                if medians:
                    results.append((os.path.basename(path), medians))
            else:
                report_log(path, out, args.min_ms)
        except Exception as e:  # один битый файл не должен ломать весь отчёт
            out.append(f"Не удалось разобрать `{path}`: {e}\n")
    report_comparison(results, out)

    text = "\n".join(out) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Отчёт записан в {args.output}")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
