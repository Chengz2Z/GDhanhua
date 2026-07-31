# GrimTools 本地汉化开发工具

## 一、工具介绍

本工具用于在 GrimTools《恐怖黎明》构筑模拟器中预览本工程正在开发的中文汉化。

工具按配置顺序选择汉化目录：优先读取工具目录内的 `Text_ZH`，如果不存在或没有匹配白名单的文件，再读取仓库根目录的 `Text_ZH`。

扩展会保留 GrimTools 原有的 `Simplified Chinese`，并在语言菜单中增加“简体中文-本地化”：

- 选择 `Simplified Chinese`：使用 GrimTools 官方简体中文。
- 选择“简体中文-本地化”：优先显示本地汉化，找不到 KEY 时继续使用网页中文。

当前支持两套本地开发环境：

- Windows：Chrome 或 Edge。
- macOS：Safari 26 或更高版本。

这是工程内部的开发工具，不是面向普通用户发布的 Safari 应用。Safari 采用临时扩展方式加载，不涉及 Xcode 打包、签名、公证或 App Store。

## 二、快速使用

### 2.1 生成扩展资源

构建脚本默认依次尝试：

```text
Text_ZH
../../Text_ZH
```

并同时生成 Chromium 与 Safari 使用的语言脚本及语言选项脚本。

#### Windows

双击：

```text
build_extension.bat
```

也可以在 PowerShell 中执行：

```powershell
python .\build_extension.py
```

#### macOS

在终端进入本工具目录，执行：

```bash
python3 ./build_extension.py
```

也可以使用：

```bash
./build_extension.command
```

如果 `.command` 没有执行权限，先执行一次：

```bash
chmod +x ./build_extension.command
```

构建成功后会显示：

```text
[完成] 扩展目标: 2 个
[SUCCESS] Chromium and Safari extension files were generated.
```

生成目录分别为：

```text
extension/generated/
extension-safari/generated/
```

### 2.2 在 Chrome 或 Edge 中加载

1. 打开扩展管理页：

   ```text
   Chrome: chrome://extensions/
   Edge:   edge://extensions/
   ```

2. 开启“开发者模式”或“开发人员模式”。
3. 点击“加载已解压的扩展程序”。
4. 选择：

   ```text
   tools/grimtools-local-zh/extension
   ```

5. 打开 `https://www.grimtools.com/calc/`。
6. 在网页右下角打开语言菜单。
7. 选择“简体中文-本地化”，页面会自动刷新并加载本地汉化。

修改汉化并重新构建后，需要在扩展管理页点击该扩展的“重新加载”，然后再次刷新 GrimTools。

### 2.3 在 macOS Safari 中加载

以下流程面向工程开发，建议使用 Safari 26 或更高版本。

1. 运行构建脚本，确认 `extension-safari/generated/` 已生成三份 JS。
2. 打开 Safari →“设置”→“高级”。
3. 开启“显示网页开发者功能”。
4. 打开 Safari 设置中的“开发者”标签页。
5. 如果页面要求，开启“允许未签名的扩展”。
6. 点击“添加临时扩展”。
7. 选择：

   ```text
   tools/grimtools-local-zh/extension-safari
   ```

8. 在“扩展”标签页启用“GrimTools 本地化”。
9. 允许扩展访问 `www.grimtools.com`。
10. 打开 `https://www.grimtools.com/calc/`，在右下角语言菜单选择“简体中文-本地化”；页面会自动刷新。

Safari 会在退出浏览器或临时扩展加载满 24 小时后移除它。再次使用时，重新执行“添加临时扩展”即可。

修改汉化并重新构建后，在 Safari 的扩展设置中重新加载临时扩展；如果没有重新加载入口，就移除后重新添加 `extension-safari`。

### 2.4 确认是否生效

打开 GrimTools 的开发者工具控制台，搜索：

```text
GrimTools 本地汉化
```

正常情况下会看到类似：

```text
[GrimTools 本地汉化] 当前模式: local；已覆盖 11076 个 KEY，远程回退 16271 个 KEY。
```

KEY 数量会随着白名单及汉化内容变化，不要求与示例完全相同。

选择官方 `Simplified Chinese` 时会看到：

```text
[GrimTools 本地汉化] 当前模式: official；使用 GrimTools 官方简体中文。
```

## 三、目录说明

```text
grimtools-local-zh/
├─ build_extension.bat        Windows 构建入口
├─ build_extension.command    macOS 构建入口
├─ build_extension.py         跨平台构建脚本
├─ config.json                汉化目录、白名单与重复 KEY 配置
├─ README.md                  本文档
├─ extension/                 Chrome / Edge 扩展
│  ├─ manifest.json
│  ├─ rules.json
│  └─ generated/              三份自动生成的 JS，不提交
└─ extension-safari/          Safari 开发扩展
   ├─ manifest.json
   ├─ rules.json
   └─ generated/              三份自动生成的 JS，不提交
```

两套 `generated` 中的文件由构建脚本自动生成，不要手工修改。

## 四、配置说明

`config.json` 当前配置：

```json
{
  "source_roots": [
    "Text_ZH",
    "../../Text_ZH"
  ],
  "include": [
    "**/*_items.txt",
    "**/*_skills.txt",
    "**/*_ui.txt"
  ],
  "exclude": [],
  "duplicate_policy": "last",
  "remove_markers": [
    "^-"
  ]
}
```

字段说明：

- `source_roots`：相对于 `config.json` 的候选汉化目录，按数组顺序选择第一个能匹配白名单文件的目录。
- `include`：需要读取的文件 glob 白名单。
- `exclude`：需要从白名单结果中排除的文件。
- `duplicate_policy`：重复 KEY 的处理方式。
- `remove_markers`：生成网页词典时需要移除的字符串数组。

`duplicate_policy` 支持：

- `last`：后读取的值覆盖先读取的值，当前默认。
- `first`：保留第一次读取到的值。
- `error`：发现重复 KEY 后停止构建。

同一个 KEY 对应不同文本时，脚本会列出来源文件及行号，但不会修改汉化源文件。

`remove_markers` 默认包含游戏专用的 `^-` 格式控制标记。需要增加其他标记时，继续向数组添加字符串；脚本按数组顺序处理，设置为空数组 `[]` 可关闭移除功能。该转换只影响生成结果，不会修改 `Text_ZH`；未配置的颜色、变量和换行标记保持原样。

旧版单路径配置 `source_root` 仍然兼容，但不能和 `source_roots` 同时设置。

## 五、构建脚本参数

默认同时生成两套扩展：

```bash
python3 ./build_extension.py
```

使用自定义输出目录：

```bash
python3 ./build_extension.py --output-dir /tmp/grimtools-extension
```

指定多个自定义目录：

```bash
python3 ./build_extension.py \
  --output-dir /tmp/chromium \
  --output-dir /tmp/safari
```

一旦指定 `--output-dir`，脚本只写入指定目录，不再写入默认的两个扩展目录。

如果显示：

```text
[完成] 生成文件更新: 0 个
```

表示生成文件已经是最新内容，不是失败。

## 六、浏览器差异

两套扩展使用相同的生成脚本和重定向规则，差异只保留在各自的 `manifest.json`：

### Chrome / Edge

```json
"permissions": [
  "declarativeNetRequest"
]
```

### Safari

```json
"permissions": [
  "declarativeNetRequestWithHostAccess"
]
```

Safari 对重定向操作要求 `declarativeNetRequestWithHostAccess`。Safari 扩展清单也不包含 Chromium 专用的 `minimum_chrome_version`。

Safari 26 修复了 `declarativeNetRequest` 重定向到扩展内部资源的问题，因此本工具将 Safari 26 作为推荐最低测试版本。

## 七、工作原理

GrimTools 会动态加载：

```text
/db/itemdb/l10n/zh.js?<版本号>
/editor/js/l10n/zh.js?<版本号>
```

扩展的页面脚本会在语言菜单中保留 `Simplified Chinese`，并新增“简体中文-本地化”。选择结果保存为：

```text
grimtools_local_zh_mode = official
grimtools_local_zh_mode = local
```

两种选项底层都使用 GrimTools 支持的 `zh` 语言代码。因为在两个中文模式之间切换时语言代码没有变化，扩展会刷新当前页面，使新模式立即生效。

扩展使用不依赖版本号的规则，把中文词典请求重定向到本地生成脚本。本地脚本随后：

1. 读取 GrimTools 当前版本的完整中文词典。
2. 检查 `grimtools_local_zh_mode`。
3. `official` 模式直接使用官方中文词典。
4. `local` 模式使用配置选中的 `Text_ZH` 白名单 KEY 覆盖官方词典。
5. 将结果交给构筑模拟器。

因此 `local` 模式中未在本地汉化找到的 KEY 会继续使用网页中文。若远程中文词典读取失败，`local` 模式仍会使用本地已有 KEY，并在控制台输出警告。

游戏会把 `^-` 解释为格式控制标记，但 GrimTools 会把它显示成额外字符。本工具会在写入扩展词典前，移除 `config.json` 的 `remove_markers` 数组中列出的全部字符串。

## 八、常见问题

### 8.1 切换中文后网址仍是 `/calc/`

这是正常现象。GrimTools 会把语言保存在浏览器本地，扩展不依赖地址栏是否出现 `/zh`。

### 8.2 看不到“简体中文-本地化”

确认扩展已经重新加载，并刷新 GrimTools。新选项位于网页右下角的语言菜单中，紧跟在 `Simplified Chinese` 后面。

### 8.3 修改汉化后网页没有变化

确认完成：

1. 重新运行构建脚本。
2. 重新加载对应浏览器扩展。
3. 强制刷新 GrimTools。
4. 确认语言菜单选择的是“简体中文-本地化”，而不是 `Simplified Chinese`。

### 8.4 Safari 找不到“添加临时扩展”

确认已经在 Safari →“设置”→“高级”中开启网页开发者功能，并检查当前 Safari 版本。较旧版本需要通过 Xcode 将 Web Extension 转换为 macOS 容器应用，不属于本工具当前支持的本地流程。

### 8.5 Safari 重启后扩展消失

这是临时扩展的正常行为。重新添加 `extension-safari` 即可。

### 8.6 Safari 已启用扩展但没有运行

检查 Safari 是否已经允许该扩展访问 `www.grimtools.com`。Safari 的网站权限可以按扩展和浏览器配置分别控制。

## 九、限制

- Safari 运行态必须在真实 macOS 和 Safari 中验证。
- 当前推荐 Safari 26 或更高版本。
- Safari 临时扩展会在退出 Safari 或 24 小时后移除。
- 当前只处理 `https://www.grimtools.com/` 的简体中文 `zh.js`。
- 工具不会修改或写回本工程的 `Text_ZH`。
- 使用 GrimTools 网页原文回退时需要连接网络。
