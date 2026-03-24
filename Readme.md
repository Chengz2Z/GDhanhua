## 项目简介

本项目用于 GD(Grim Dawn《恐怖黎明》)游戏的汉化编辑和一键生成汉化文件。

项目基于游戏Ver1.3版本文件和CM版本汉化修改：
1.如需CM版本文件或CM作者联系方式，可自行搜索；
2.将持续跟随游戏版本更新文本文件和汉化内容；

☆ 如若发现本项目汉化上有遗漏和错误，或有更好的修改意见；
☆ 请附带意向联系我QQ:1819365107；
☆ 有能力者可参与汉化的优化工作。

## 目录结构

```text
Project/
├─ Text_ZH/           汉化文本资源目录
│  ├─ aom/            扩展内容文本
│  ├─ fg/             扩展内容文本
│  └─ foa/            扩展内容文本
├─ origin/            原始归档与解包输出目录
│  ├─ *.arc           示例：待解包的文件
│  ├─ split.bat       一键解包脚本
│  └─ text_*/         示例：解包后的目录
├─ out/               编译输出目录
│  ├─ *.arc           示例：编译生成的文件
│  └─ _build/         示例：无词缀简述的临时文件
├─ scripts/           构建辅助脚本目录
│  └─ prepare-build.ps1
│                     编译前处理词缀简述开关
├─ ArchiveTool.exe    归档打包/解包工具
├─ zlibwapi.dll       ArchiveTool 运行依赖
├─ build.bat          一键编译脚本
├─ .gitignore         Git 忽略配置
├─ LICENSE            项目许可证
└─ Readme.md          项目说明
```

## 适用场景

- 整理或维护现有 `Text_ZH` 中文文本资源
- 解包游戏原始 `.arc` 文件，查看或比对原版文本内容
- 将修改后的文本重新编译为新的 `Text_ZH.arc` 文件

## 编译前准备

请确认以下内容位于项目根目录：

- `ArchiveTool.exe`
- `zlibwapi.dll`
- `build.bat`
- `Text_ZH` 目录

如果缺少上述文件，脚本将无法正常完成打包。

## 编译方法

在项目根目录下直接双击 `build.bat`，或在命令行中执行：

```bat
build.bat
```

`build.bat` 内默认带有：

```bat
set ENABLE_DESC=1
```

双击脚本时，会按这个变量决定是否保留前后缀括号里的属性简述：

- `set ENABLE_DESC=1`：保留词缀属性简述
- `set ENABLE_DESC=0`：去掉词缀属性简述

如果需要临时按参数覆盖这个默认值，可使用：

去掉词缀名后面的属性简述括号：

```bat
build.bat no-desc
```

显式保留简述：

```bat
build.bat with-desc
```

## 编译脚本行为

执行 `build.bat` 时，脚本会按以下顺序处理：

1. 检查 `./out` 目录是否存在，不存在则自动创建。
2. 检查 `./out/Text_ZH.arc` 是否已存在，若存在则先删除旧文件。
3. 根据 `build.bat` 里的 `ENABLE_DESC` 变量，或命令行传入的覆盖参数，决定是否保留前后缀属性简述。
4. 如果最终为“不带简述”模式，则先复制 `./Text_ZH` 到临时目录，并移除 `tagPrefix/tagSuffix` 项末尾括号中的属性简述。
5. 调用 `ArchiveTool.exe` 将构建源目录重新打包。
6. 编译成功后输出成功提示。
7. 编译失败时输出失败提示，并暂停窗口，方便查看日志。

不带简述模式只影响编译时的临时副本，不会修改仓库里的原始 `Text_ZH` 文本。

## 输出文件

编译完成后，输出文件为：

```text
./out/Text_ZH.arc
```

这是当前仓库生成的汉化归档文件。

## 原始文件解包

项目同时提供了解包脚本，可从游戏源文件中将 `.arc` 文件拷贝到 `origin` 目录中，运行 `split.bat` 一键解包，便于查看或比对游戏原版文本，及时更新汉化内容；
也可以导入其他汉化版本解包后自行修改。

### 解包前准备

请确认以下内容存在：

- `ArchiveTool.exe`
- `origin\split.bat`
- `origin` 目录中的 `.arc` 文件

### 解包方法

进入 `origin` 目录后，直接双击 `split.bat`，或在命令行中执行：

```bat
cd origin
split.bat
```

### 解包脚本行为

执行 `origin\split.bat` 时，脚本会按以下顺序处理：

1. 检查 `ArchiveTool.exe` 是否存在。
2. 删除 `origin` 目录中上一次解包生成的旧内容。
3. 保留当前目录中的 `.bat` 和 `.arc` 文件。
4. 将当前 `origin` 目录中的 `.arc` 文件重新解包到当前目录。
5. 根据 `.arc` 文件名生成对应的解包目录。

### 解包输出目录

解包完成后，输出内容会按 `.arc` 文件名生成对应目录，例如：

```text
origin/Text_ZH.arc  -> origin/text_zh
origin/Text_EN.arc  -> origin/text_en
origin/Text_JP.arc  -> origin/text_jp
```

如果 `origin` 中存在多个 `.arc` 文件，脚本会依次处理，并分别生成对应的解包目录。

## 日常使用流程

1. 修改 `Text_ZH` 目录中的文本文件。
2. 运行 `build.bat`。
3. 检查是否成功生成 `./out/Text_ZH.arc`。
4. 将生成结果用于后续测试、替换或发布。

## 常见问题

### 修改文本后如何重新生成

直接重新运行一次 `build.bat` 即可。脚本会自动删除旧文件并重新编译。

### 删除旧文件失败怎么办

通常表示 `Text_ZH.arc` 正被其他程序占用。关闭正在使用该文件的程序后，再重新执行脚本即可。

### 解包时出现错误弹窗怎么办

如果出现 `ArchiveTool.exe` 的报错弹窗，通常与工具处理相对路径有关。当前 `split.bat` 已改为使用绝对路径解包，一般可直接正常使用。如仍有问题，请确认 `.arc` 文件未被占用，且 `ArchiveTool.exe` 位于项目根目录。

## 许可证

本项目许可证见 [LICENSE](./LICENSE)。
