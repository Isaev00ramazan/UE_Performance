# ТЗ: починить сборку MadWater после обновления Oceanology до V10 (UE 5.8)

## Контекст
- Проект: `G:\TEST5.8\MadWater.uproject` (копия проекта, перенесённая с UE 5.7 на **UE 5.8**, движок `G:\UEProgramm\UE_5.8`).
- Игровой C++-модуль: `Source\MODWATER_Build`. Цель сборки: `MODWATER_BuildEditor Win64 Development`.
- Плагин океана Oceanology заменён на новую версию V10: `Plugins\Oceanoloaa8f47f50db8V10` (модуль `Oceanology_Plugin`).
- Физика воды: плагин DWP2 `Plugins\NWHDynamicWaterPhysics\Source\DWP2` — использует Oceanology.
- Старая рабочая версия проекта (UE 5.7, старая Oceanology): `<OLD_PROJECT>` — **путь уточнить у пользователя**.
- Плагины NVIDIA (DLSS, StreamlineCore/NGXCommon/Reflex, NIS) обновлены и **собираются без ошибок — не трогать**.

## Проблема
Сборка падает: в новой Oceanology нет файла `Subsystems/OceanologyWorldSubsystem.h` и типа `FOceanologyWaveParamsThreadSafe`.

| Файл | Строка | Ошибка |
|---|---|---|
| `Plugins\NWHDynamicWaterPhysics\Source\DWP2\Public\WaterObjectComponent.h` | 42, 47 | `FOceanologyWaveParamsThreadSafe` — неизвестный тип |
| `Plugins\NWHDynamicWaterPhysics\Source\DWP2\Private\WaterObjectComponent.cpp` | 20 | нет `Subsystems/OceanologyWorldSubsystem.h` |
| `Source\MODWATER_Build\Private\GAS\PickupBase.cpp` | 20 | то же |
| `Source\MODWATER_Build\Private\Effects\FloatingDebris.cpp` | 7 | то же |

**Почему:** почти наверняка это собственный код команды, который был дописан прямо внутрь старого плагина Oceanology
(мост «волны океана → потокобезопасные параметры для асинхронной физики»: DWP2 + AsyncTickPhysics).
При замене папки плагина целиком эти файлы удалились. Косвенный признак — предупреждение UBT:
`Plugin 'DWP2' does not list plugin 'Oceanology_Plugin' as a dependency` (связку добавляли вручную).

## Задача

### Этап 1 — найти все свои доработки в старом плагине (обязательно)
1. В `<OLD_PROJECT>\Plugins` найти все упоминания `OceanologyWorldSubsystem` и `FOceanologyWaveParamsThreadSafe`
   (ожидаются `Public/Subsystems/OceanologyWorldSubsystem.h` и `Private/Subsystems/OceanologyWorldSubsystem.cpp`).
2. Сравнить папку `Source` старой Oceanology с новой V10 (diff всего дерева). Составить список:
   файлы, которых нет в V10, и правки внутри общих файлов, не похожие на код автора плагина.
3. Показать список пользователю перед переносом.

### Этап 2 — вынести свой код в отдельный плагин-мост (рекомендуется)
Чтобы следующее обновление Oceanology снова ничего не стёрло:
1. Создать плагин `Plugins\MadWaterOceanBridge` (Runtime-модуль `MadWaterOceanBridge`),
   зависимости: `Oceanology_Plugin` (в `.uplugin` и в `Build.cs`).
2. Перенести туда subsystem и структуру **с теми же именами классов** и тем же путём include
   (`Public/Subsystems/OceanologyWorldSubsystem.h`), заменить макрос экспорта `OCEANOLOGY_PLUGIN_API` → `MADWATEROCEANBRIDGE_API`.
3. Подключить `MadWaterOceanBridge`:
   - в `DWP2.Build.cs` и `MODWATER_Build.Build.cs` (`PublicDependencyModuleNames`);
   - в `DWP2.uplugin` → `"Plugins"`: `Oceanology_Plugin` и `MadWaterOceanBridge`;
   - в `MadWater.uproject` → включить плагин.
4. Класс и структура поменяли модуль, поэтому Blueprint-ассеты, которые на них ссылаются, сломаются.
   Добавить в `Config\DefaultEngine.ini`:
   ```ini
   [CoreRedirects]
   +ClassRedirects=(OldName="/Script/Oceanology_Plugin.OceanologyWorldSubsystem",NewName="/Script/MadWaterOceanBridge.OceanologyWorldSubsystem")
   +StructRedirects=(OldName="/Script/Oceanology_Plugin.OceanologyWaveParamsThreadSafe",NewName="/Script/MadWaterOceanBridge.OceanologyWaveParamsThreadSafe")
   ```

*Быстрый вариант, если нужно срочно собрать:* скопировать найденные файлы обратно в новый плагин по тем же путям.
Тогда этап 2 сделать позже.

### Этап 3 — адаптировать к API Oceanology V10
В V10 расчёт волн переделан (`OceanologyWaveSolverComponent`, `OceanologyGerstnerWaveSolverComponent`,
`OceanologyLegacyGerstnerWaveUtils`). Если перенесённый код вызывает старые функции или поля, перевести его на новые.
**Важно:** расчёт волн на CPU (для плавучести) должен давать ту же высоту, что и материал воды V10 на GPU.

## Ограничения
- Перед началом сделать коммит или резервную копию `G:\TEST5.8`.
- Не менять код Oceanology V10, DLSS, Streamline и NIS. Исключение — если без этого никак, тогда согласовать с пользователем.
- Предупреждения `C4305` (double → float) и deprecation-предупреждения внутри Oceanology **не исправлять**: это код автора плагина.
- Не менять игровую логику, только перенос и адаптация.

## Как проверить
Сборка:
```
"G:\UEProgramm\UE_5.8\Engine\Build\BatchFiles\Build.bat" MODWATER_BuildEditor Win64 Development -Project="G:\TEST5.8\MadWater.uproject" -WaitMutex
```
Готово, когда:
1. Сборка проходит без ошибок, предупреждения про зависимость DWP2 нет.
2. Редактор открывается без запроса пересобрать модули и без ошибок загрузки Blueprint.
3. В PIE на уровне `/Game/Isaev_R/TraceLevels/LVL1_Hollywood/12`:
   - лодка плавает ровно по видимым волнам (не проваливается и не висит над водой);
   - подбираемые предметы (`PickupBase`) и плавающий мусор (`FloatingDebris`) держатся на воде.
4. Упакованный Development-билд запускается, в логе нет ошибок загрузки модулей.

## Что вернуть пользователю
- Список найденных доработок из этапа 1.
- Список изменённых и созданных файлов.
- Что пришлось менять под API V10 и почему.
