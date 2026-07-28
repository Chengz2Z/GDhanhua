## 项目简介

本项目用于 GD(Grim Dawn《恐怖黎明》)游戏的汉化编辑和一键生成汉化文件。

~~项目基于游戏Ver1.3版本文件和CM版本汉化修改：~~
~~1.如需CM版本文件或CM作者联系方式，可自行搜索；~~
~~2.将持续跟随游戏版本更新文本文件和汉化内容；~~

### 2026年06月29日 更新
项目基于游戏Ver1.3版本和工具网同步更新：
1.当前已不再基于CM汉化更新，改为基于游戏自带汉化；
2.对于CM遗留内容或mod内容将作为额外内容进行支持；
3.对齐原版游戏和工具网，同步更新汉化内容和文本文件；

### 2026年07月02日 更新
1.补充 对齐原版游戏和工具网 汉化；
2.移除过时的技能/物品等条目的额外辅助描述；
3.待做：增加技能/物品等条目的新手友好辅助描述。

### 2026年07月23日 更新
1.同步v1.3《阿斯特堪之牙》正式版全部内容；
2.增加全部新内容的辅助描述并修正部分内容；
2.待做：增加技能/物品等条目的新手友好辅助描述。

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
│  ├─ split.bat       一键解包脚本（Windows）
│  ├─ split.py        一键解包脚本（跨平台）
│  └─ text_*/         示例：解包后的目录
├─ out/               编译输出目录（release 模式生成）
│  ├─ arc_with_desc/  带词缀简述的归档文件
│  │  └─ Text_ZH.arc
│  ├─ set_with_desc/  带词缀简述的源文件目录
│  │  └─ Text_ZH/
│  ├─ arc_no_desc/    无词缀简述的归档文件
│  │  └─ Text_ZH.arc
│  └─ set_no_desc/    无词缀简述的源文件目录
│     └─ Text_ZH/
├─ scripts/           构建辅助脚本目录
│  └─ prepare-build.ps1
│                     编译前处理词缀简述开关
├─ tools/             实用工具目录
│  ├─ update_entries.py
│  │                 条目更新工具
│  └─ diff_entries.py
│                    条目对比工具
├─ ArchiveTool.exe    归档打包/解包工具（Windows）
├─ zlibwapi.dll       ArchiveTool 运行依赖（Windows）
├─ arc_tool.py        归档打包/解包工具（跨平台，使用原生 LZ4 库）
├─ build.bat          一键编译脚本（Windows）
├─ build.py           一键编译脚本（跨平台）
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

- `arc_tool.py`（Python 归档工具）
- `Text_ZH` 目录

如果缺少上述文件，脚本将无法正常完成打包。

### macOS / Linux 额外准备

`arc_tool.py` 使用系统原生 LZ4 库进行压缩（速度快），请确保已安装：

```bash
# macOS
brew install lz4

# Ubuntu / Debian
sudo apt install liblz4-dev
```

如果未安装 LZ4 库，工具会自动回退到纯 Python 实现（速度较慢）。

## 编译方法

### Windows

在项目根目录下直接双击 `build.bat`，或在命令行中执行：

```bat
build.bat
```

默认执行 `release` 模式，打包所有版本文件用于发布。

可用参数：

```bat
build.bat                 # 默认: release 模式，打包所有版本
build.bat release         # 同上，显式指定 release 模式
build.bat with-desc       # 仅打包带词缀简述版本
build.bat no-desc         # 仅打包无词缀简述版本
build.bat -h / --help     # 显示帮助
```

### macOS / Linux

在项目根目录下使用 Python 脚本（无需额外安装依赖）：

```bash
python3 build.py              # 默认: release 模式，打包所有版本
python3 build.py release      # 同上，显式指定 release 模式
python3 build.py with-desc    # 仅打包带词缀简述版本
python3 build.py no-desc      # 仅打包无词缀简述版本
```

## 编译脚本行为

### release 模式（默认）

执行 `build.bat` 或 `build.py` 时，默认进入 release 模式，按以下顺序处理：

1. **带描述构建**：将 `Text_ZH` 打包为 `out/arc_with_desc/Text_ZH.arc`
2. **拷贝源文件**：复制 `Text_ZH` 到 `out/set_with_desc/Text_ZH/`
3. **无描述构建**：复制 `Text_ZH` 到临时目录，移除词缀简述后打包为 `out/arc_no_desc/Text_ZH.arc`
4. **移动源文件**：将处理后的临时目录移动到 `out/set_no_desc/Text_ZH/`
5. **清理临时文件**：删除 `_build` 临时目录

### 单次构建模式

使用 `with-desc` 或 `no-desc` 参数时，仅执行单次构建：

1. 检查 `./out` 目录是否存在，不存在则自动创建。
2. 检查 `./out/Text_ZH.arc` 是否已存在，若存在则先删除旧文件。
3. 根据参数决定是否保留前后缀属性简述。
4. 如果为"不带简述"模式，则先复制 `./Text_ZH` 到临时目录，并移除词缀简述。
5. 调用打包工具重新打包。
6. 编译成功后输出成功提示。

不带简述模式只影响编译时的临时副本，不会修改仓库里的原始 `Text_ZH` 文本。

## 输出文件

### release 模式输出

编译完成后，在 `out/` 目录下生成四个子目录：

```text
out/
├─ arc_with_desc/     带词缀简述的归档文件
│  └─ Text_ZH.arc
├─ set_with_desc/     带词缀简述的源文件目录（可直接用于游戏替换）
│  └─ Text_ZH/
├─ arc_no_desc/       无词缀简述的归档文件
│  └─ Text_ZH.arc
└─ set_no_desc/       无词缀简述的源文件目录
   └─ Text_ZH/
```

- `arc_*` 目录：包含打包后的 `.arc` 归档文件，可直接用于游戏替换
- `set_*` 目录：包含解包后的源文件目录，便于查看或进一步编辑

### 单次构建模式输出

使用 `with-desc` 或 `no-desc` 参数时，输出文件为：

```text
./out/Text_ZH.arc
```

## 原始文件解包

项目同时提供了解包脚本，可从游戏源文件中将 `.arc` 文件拷贝到 `origin` 目录中，运行 `split.bat` 一键解包，便于查看或比对游戏原版文本，及时更新汉化内容；
也可以导入其他汉化版本解包后自行修改。

### 解包前准备

请确认以下内容存在：

- `arc_tool.py`（位于项目根目录）
- `origin` 目录中的 `.arc` 文件

### 解包方法

#### Windows

进入 `origin` 目录后，直接双击 `split.bat`，或在命令行中执行：

```bat
cd origin
split.bat
```

#### macOS / Linux

```bash
cd origin
python3 split.py
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
2. 运行构建脚本：
   - Windows：`build.bat`
   - macOS / Linux：`python3 build.py`
3. 检查 `out/` 目录下是否成功生成以下内容：
   - `arc_with_desc/Text_ZH.arc`（带描述版本）
   - `arc_no_desc/Text_ZH.arc`（无描述版本）
4. 将生成的 `.arc` 文件用于游戏替换或发布。

如果只需要单个版本，可使用 `with-desc` 或 `no-desc` 参数。

## arc_tool.py 使用说明

`arc_tool.py` 是跨平台的 `.arc` 归档工具，支持以下命令：

### 打包

```bash
python3 arc_tool.py pack <output.arc> <input_dir> [--level N] [--algo lz4|zlib]
```

- `--level N`：压缩级别 0-9，默认 6（仅 zlib 有效）
- `--algo lz4|zlib`：压缩算法，默认 LZ4（与 ArchiveTool.exe 兼容）

示例：

```bash
python3 arc_tool.py pack out/Text_ZH.arc Text_ZH
python3 arc_tool.py pack out/Text_ZH.arc Text_ZH --algo zlib --level 9
```

**压缩算法说明**：
- `lz4`（默认）：使用系统原生 liblz4 库，速度快，与游戏完全兼容
- `zlib`：压缩率更高，文件更小，但游戏可能无法识别

### 解包

```bash
python3 arc_tool.py unpack <input.arc> <output_dir>
```

自动检测压缩算法（LZ4/zlib），兼容所有 `.arc` 文件。

### 提取数据库文件

```bash
python3 arc_tool.py database <input.arc> <output_dir> [file]
```

类似 ArchiveTool.exe 的 `-database` 命令，可提取特定文件：

```bash
python3 arc_tool.py database origin/Text_EN.arc origin/text_en
python3 arc_tool.py database origin/Text_EN.arc origin/text_en tags_items
```

### 列出内容

```bash
python3 arc_tool.py list <input.arc>
```

### 查看详细信息

```bash
python3 arc_tool.py info <input.arc>
```

显示文件头、压缩算法检测、EntryType 分布等信息。

## 常见问题

### 修改文本后如何重新生成

直接重新运行一次 `build.bat`（或 `python3 build.py`）即可。脚本会自动删除旧文件并重新编译。

### release 模式和单次构建有什么区别

- **release 模式**（默认）：同时生成带描述和无描述两个版本，以及对应的源文件目录，适合发布
- **单次构建**（`with-desc` 或 `no-desc`）：仅生成单个版本，适合快速测试

### 删除旧文件失败怎么办

通常表示 `.arc` 文件正被其他程序占用。关闭正在使用该文件的程序后，再重新执行脚本即可。

### 解包时出现错误弹窗怎么办

如果出现 `ArchiveTool.exe` 的报错弹窗，通常与工具处理相对路径有关。当前 `split.bat` 已改为使用绝对路径解包，一般可直接正常使用。如仍有问题，请确认 `.arc` 文件未被占用，且 `ArchiveTool.exe` 位于项目根目录。

## 许可证

本项目许可证见 [LICENSE](./LICENSE)。
