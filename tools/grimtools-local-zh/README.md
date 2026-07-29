# GrimTools 本地汉化优先扩展

## 一、工具介绍

本工具是为《恐怖黎明》GrimTools 构筑模拟器制作的本地汉化扩展，适用于 Chrome 和 Edge 浏览器。

安装扩展后，GrimTools 会优先显示当前汉化工程 `Text_ZH` 中的文本：

- 本地汉化中存在同名 KEY：显示本地汉化内容。
- 本地汉化中不存在该 KEY：继续显示 GrimTools 网页自带的中文内容。

这样既能在构筑模拟器中及时预览正在制作的汉化，又不会因为本地文本不完整而出现大量缺失内容。

扩展会自动匹配 GrimTools 更新后的语言文件，不依赖 `zh.js` 后面的版本号。它只处理 `www.grimtools.com` 的简体中文语言文件，不会修改 `Text_ZH` 中的任何源文件。

## 二、使用步骤

### 2.1 第一次安装

#### 第一步：生成扩展使用的汉化文件

双击运行：

```text
build_extension.bat
```

脚本会读取 `Text_ZH` 中白名单允许的汉化文件，并生成浏览器扩展需要的文件。

看到下面的提示就表示生成成功：

```text
[SUCCESS] Extension files were generated.
```

窗口最后会显示：

```text
Press any key to continue . . .
```

确认没有错误后，按任意键关闭窗口。

如果提示找不到 Python，需要先安装 Python 3，并在安装时启用“Add Python to PATH”。

#### 第二步：打开浏览器扩展管理页

根据使用的浏览器，在地址栏输入：

Chrome：

```text
chrome://extensions/
```

Edge：

```text
edge://extensions/
```

按回车打开扩展管理页。

#### 第三步：开启开发者模式

在扩展管理页找到并开启：

- Chrome：“开发者模式”
- Edge：“开发人员模式”

#### 第四步：加载扩展

点击“加载已解压的扩展程序”或“加载解压缩的扩展”，然后选择本工具目录下的：

```text
extension
```

完整目录示例：

```text
E:\GDhanhua\tools\grimtools-local-zh\extension
```

注意必须选择 `extension` 目录，不要选择 `grimtools-local-zh`、`generated` 或 `Text_ZH` 目录。

加载成功后，扩展管理页中会出现：

```text
GrimTools 本地汉化优先
```

#### 第五步：打开 GrimTools

打开：

```text
https://www.grimtools.com/calc/
```

如果页面不是中文，在网页底部选择：

```text
Simplified Chinese
```

切换中文后，网址仍然显示 `https://www.grimtools.com/calc/` 是正常现象。GrimTools 会将语言设置保存在浏览器中，不一定改变网址。

最后按一次 `Ctrl+F5` 强制刷新页面，本地汉化即可生效。

### 2.2 汉化内容修改后的更新方法

每次修改 `Text_ZH` 中的汉化后，依次执行：

1. 双击 `build_extension.bat`，重新生成扩展文件。
2. 打开浏览器扩展管理页。
3. 找到“GrimTools 本地汉化优先”。
4. 点击扩展卡片上的“重新加载”按钮。
5. 返回 GrimTools 页面，按 `Ctrl+F5` 强制刷新。

只重新运行脚本还不够，浏览器不会自动重新载入已经安装的扩展，因此必须点击一次“重新加载”。

### 2.3 如何确认扩展是否生效

在 GrimTools 页面按 `F12` 打开开发者工具，切换到 `Console`（控制台）。

正常情况下可以看到类似信息：

```text
[GrimTools 本地汉化] 已覆盖 11076 个 KEY，远程回退 16271 个 KEY。
```

KEY 数量会随着汉化文件的增减而变化。

如果没有这条信息，请检查扩展是否已启用、是否选择了简体中文，以及修改汉化后是否重新加载了扩展。

## 三、目录和文件说明

```text
grimtools-local-zh/
├─ build_extension.bat       双击运行的构建脚本
├─ build_extension.py        实际执行构建的 Python 脚本
├─ config.json               汉化目录、白名单及重复 KEY 配置
├─ README.md                 本说明文档
└─ extension/                浏览器需要加载的扩展目录
   ├─ manifest.json          扩展清单
   ├─ rules.json             GrimTools 语言文件重定向规则
   └─ generated/
      ├─ db-zh.js            物品数据库本地汉化
      └─ editor-zh.js        构筑编辑器本地汉化
```

`generated` 目录中的文件由构建脚本自动生成，不要手工编辑。需要修改显示文本时，应修改 `Text_ZH` 中的源文件，然后重新运行构建脚本。

## 四、构建脚本说明

除双击 `build_extension.bat` 外，也可以在本工具目录打开 PowerShell，执行：

```powershell
python .\build_extension.py
```

默认情况下，构建脚本会：

1. 读取 `config.json`。
2. 根据白名单查找汉化文件。
3. 按 `KEY=VALUE` 格式解析文本。
4. 汇总并处理重复 KEY。
5. 生成 `db-zh.js` 和 `editor-zh.js`。

如果构建结果显示：

```text
[完成] 生成文件更新: 0 个
```

表示当前生成文件已经是最新内容，不是构建失败。

## 五、白名单配置

白名单位于 `config.json`。默认配置如下：

```json
{
  "source_root": "../../Text_ZH",
  "include": [
    "**/*_items.txt",
    "**/*_skills.txt"
  ],
  "exclude": [],
  "duplicate_policy": "last"
}
```

各字段含义：

- `source_root`：汉化根目录，相对于 `config.json` 所在目录。
- `include`：允许读取的文件规则。
- `exclude`：需要从允许列表中排除的文件规则。
- `duplicate_policy`：重复 KEY 的处理规则。

当前白名单会读取 `Text_ZH` 及其子目录中的：

```text
*_items.txt
*_skills.txt
```

以后需要增加其他文件时，在 `include` 数组中添加相应规则即可。例如增加所有 `*_ui.txt`：

```json
"include": [
  "**/*_items.txt",
  "**/*_skills.txt",
  "**/*_ui.txt"
]
```

## 六、重复 KEY 处理

`duplicate_policy` 支持三种设置：

- `last`：后读取到的值覆盖先读取到的值，默认使用此设置。
- `first`：保留第一次读取到的值。
- `error`：发现重复 KEY 后立即停止构建。

如果同一个 KEY 出现多次但文本完全相同，通常不会影响显示。

如果同一个 KEY 对应的文本不同，构建脚本会列出来源文件和行号，例如：

```text
tagExample: old_file.txt:10 -> new_file.txt:20
```

这些提示不会修改汉化源文件，只用于帮助检查可能存在的冲突。

## 七、工作原理

GrimTools 构筑模拟器会分别加载两份简体中文语言文件：

```text
/db/itemdb/l10n/zh.js?<版本号>
/editor/js/l10n/zh.js?<版本号>
```

扩展会将这两个请求重定向到本地生成的脚本。本地脚本随后：

1. 读取 GrimTools 当前版本的完整中文词典。
2. 将本工程白名单中的 KEY 覆盖到网页词典上。
3. 把合并后的词典交给构筑模拟器使用。

因此，GrimTools 更新语言文件版本号后通常不需要修改扩展；重新打开或刷新网页时，扩展仍会读取网页当前版本的中文内容作为回退。

如果远程中文词典暂时读取失败，扩展会继续提供本地已有 KEY，并在浏览器控制台输出警告。

## 八、常见问题

### 8.1 双击脚本后提示“生成文件更新: 0 个”

这是正常情况，表示 `Text_ZH` 与现有生成文件相比没有变化。

### 8.2 切换中文后网址没有 `/zh`

这是正常情况。语言设置保存在浏览器本地，扩展是否工作不依赖地址栏中是否出现 `/zh`。

### 8.3 修改汉化后网页没有变化

请确认已依次完成：

1. 重新运行 `build_extension.bat`。
2. 在扩展管理页点击“重新加载”。
3. 在 GrimTools 页面按 `Ctrl+F5`。

### 8.4 扩展管理页提示文件不存在

请先运行一次 `build_extension.bat`，确认下面两个文件存在：

```text
extension/generated/db-zh.js
extension/generated/editor-zh.js
```

### 8.5 页面仍然显示英文

请在 GrimTools 页面底部选择 `Simplified Chinese`。本扩展只覆盖简体中文词典，不会强制把英文页面切换成中文。

### 8.6 如何判断扩展是否加载成功

打开开发者工具控制台，搜索：

```text
GrimTools 本地汉化
```

能够看到覆盖 KEY 数量说明扩展已经运行。

## 九、适用范围和限制

- 当前支持 Chrome 和 Edge。
- 当前只处理 `https://www.grimtools.com/`。
- 当前只处理简体中文 `zh.js`。
- 扩展不会修改、删除或写回 `Text_ZH` 源文件。
- 使用构筑模拟器及网页原文回退时仍需要连接 GrimTools 网站。
- GrimTools 如果改变语言文件路径或数据格式，扩展规则和生成脚本可能需要同步调整。
