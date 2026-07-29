# GrimTools 本地汉化开发工具

## 一、工具介绍

本工具用于在 GrimTools《恐怖黎明》构筑模拟器中预览本工程正在开发的中文汉化。

工具直接读取仓库根目录的 `Text_ZH`：

- 本地汉化存在同名 KEY：优先显示本地内容。
- 本地汉化不存在该 KEY：继续使用 GrimTools 网页自带的中文内容。

当前支持两套本地开发环境：

- Windows：Chrome 或 Edge。
- macOS：Safari 26 或更高版本。

这是工程内部的开发工具，不是面向普通用户发布的 Safari 应用。Safari 采用临时扩展方式加载，不涉及 Xcode 打包、签名、公证或 App Store。

## 二、快速使用

### 2.1 生成扩展资源

构建脚本默认读取：

```text
../../Text_ZH
```

并同时生成 Chromium 与 Safari 使用的语言脚本。

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
6. 在网页底部选择 `Simplified Chinese`。
7. 按 `Ctrl+F5` 强制刷新。

修改汉化并重新构建后，需要在扩展管理页点击该扩展的“重新加载”，然后再次刷新 GrimTools。

### 2.3 在 macOS Safari 中加载

以下流程面向工程开发，建议使用 Safari 26 或更高版本。

1. 运行构建脚本，确认 `extension-safari/generated/` 已生成两份 JS。
2. 打开 Safari →“设置”→“高级”。
3. 开启“显示网页开发者功能”。
4. 打开 Safari 设置中的“开发者”标签页。
5. 如果页面要求，开启“允许未签名的扩展”。
6. 点击“添加临时扩展”。
7. 选择：

   ```text
   tools/grimtools-local-zh/extension-safari
   ```

8. 在“扩展”标签页启用“GrimTools 本地汉化优先”。
9. 允许扩展访问 `www.grimtools.com`。
10. 打开 `https://www.grimtools.com/calc/`，选择 `Simplified Chinese` 并刷新。

Safari 会在退出浏览器或临时扩展加载满 24 小时后移除它。再次使用时，重新执行“添加临时扩展”即可。

修改汉化并重新构建后，在 Safari 的扩展设置中重新加载临时扩展；如果没有重新加载入口，就移除后重新添加 `extension-safari`。

### 2.4 确认是否生效

打开 GrimTools 的开发者工具控制台，搜索：

```text
GrimTools 本地汉化
```

正常情况下会看到类似：

```text
[GrimTools 本地汉化] 已覆盖 13707 个 KEY，远程回退 16271 个 KEY。
```

KEY 数量会随着白名单及汉化内容变化，不要求与示例完全相同。

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
│  └─ generated/              自动生成，不提交
└─ extension-safari/          Safari 开发扩展
   ├─ manifest.json
   ├─ rules.json
   └─ generated/              自动生成，不提交
```

两套 `generated` 中的文件由构建脚本自动生成，不要手工修改。

## 四、白名单配置

`config.json` 当前配置：

```json
{
  "source_root": "../../Text_ZH",
  "include": [
    "**/*_items.txt",
    "**/*_skills.txt",
    "**/*_ui.txt"
  ],
  "exclude": [],
  "duplicate_policy": "last"
}
```

字段说明：

- `source_root`：相对于 `config.json` 的汉化根目录。
- `include`：需要读取的文件 glob 白名单。
- `exclude`：需要从白名单结果中排除的文件。
- `duplicate_policy`：重复 KEY 的处理方式。

`duplicate_policy` 支持：

- `last`：后读取的值覆盖先读取的值，当前默认。
- `first`：保留第一次读取到的值。
- `error`：发现重复 KEY 后停止构建。

同一个 KEY 对应不同文本时，脚本会列出来源文件及行号，但不会修改汉化源文件。

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

扩展使用不依赖版本号的规则，把请求重定向到本地生成脚本。本地脚本随后：

1. 读取 GrimTools 当前版本的完整中文词典。
2. 使用本工程 `Text_ZH` 中的白名单 KEY 覆盖网页词典。
3. 将合并结果交给构筑模拟器。

因此未在本地汉化中找到的 KEY 会继续使用网页中文。若远程中文词典读取失败，页面仍会使用本地已有 KEY，并在控制台输出警告。

## 八、常见问题

### 8.1 切换中文后网址仍是 `/calc/`

这是正常现象。GrimTools 会把语言保存在浏览器本地，扩展不依赖地址栏是否出现 `/zh`。

### 8.2 修改汉化后网页没有变化

确认完成：

1. 重新运行构建脚本。
2. 重新加载对应浏览器扩展。
3. 强制刷新 GrimTools。

### 8.3 Safari 找不到“添加临时扩展”

确认已经在 Safari →“设置”→“高级”中开启网页开发者功能，并检查当前 Safari 版本。较旧版本需要通过 Xcode 将 Web Extension 转换为 macOS 容器应用，不属于本工具当前支持的本地流程。

### 8.4 Safari 重启后扩展消失

这是临时扩展的正常行为。重新添加 `extension-safari` 即可。

### 8.5 Safari 已启用扩展但没有运行

检查 Safari 是否已经允许该扩展访问 `www.grimtools.com`。Safari 的网站权限可以按扩展和浏览器配置分别控制。

## 九、限制

- Safari 运行态必须在真实 macOS 和 Safari 中验证。
- 当前推荐 Safari 26 或更高版本。
- Safari 临时扩展会在退出 Safari 或 24 小时后移除。
- 当前只处理 `https://www.grimtools.com/` 的简体中文 `zh.js`。
- 工具不会修改或写回本工程的 `Text_ZH`。
- 使用 GrimTools 网页原文回退时需要连接网络。
