# Tree2HTML

一个生成HTML文件目录清单的程序

<img src="https://github.com/user-attachments/assets/5dc5f54c-18ad-4f33-8f69-16fd2b86c2f0" />

<img src="https://github.com/user-attachments/assets/9511703c-962b-4c1c-b7eb-845f2e594ae9" />

# 使用方法

1. 下载Tree2HTML.py和template.html文件，两个文件放在一起，运行Tree2HTML.py（需安装[Python](https://www.python.org/)）
2. 到 [Releases](https://github.com/Little-Data/Tree2HTML/releases) 下载压缩文件后 **全部** 解压运行.exe文件（仅Windows）

# 配置说明

忽略规则文件（IGNORE_NAMES.json）

程序首次运行时会自动在运行目录生成IGNORE_NAMES.json文件，用于定义需要忽略的文件 / 文件夹名称（不区分大小写）。

自定义忽略规则

直接编辑IGNORE_NAMES.json文件，添加 / 删除需要忽略的名称即可，例如：

```json
[
  ".DS_Store",
  "Thumbs.db",
  "node_modules",  // 新增忽略node_modules目录
  ".git",          // 新增忽略.git目录
  "venv"           // 新增忽略Python虚拟环境目录
]
```
修改后再次生成文件时生效

# 生成的 HTML 特点

- 根目录默认展开，子目录默认折叠，点击目录名称可切换展开 / 折叠状态
- 目录项显示：修改时间、包含的子目录 / 文件数量
- 文件项显示：文件大小、修改时间
- 隐藏文件 / 文件夹（若勾选包含）会正常显示，无特殊标记
- 权限不足的目录（若勾选包含）会标记错误状态，无子项展示
- 响应式布局，适配不同尺寸的浏览器窗口

# 常见问题

Q1：运行提示 “模板文件 template.html 不存在”

A：确保template.html与Tree2HTML.py在同一目录下，模板文件是生成 HTML 的基础框架，不可缺失。

Q2：生成的 HTML 中缺少某些文件 / 文件夹

A：检查以下原因：

- 该文件 / 文件夹名称在IGNORE_NAMES.json中被忽略
- 该文件 / 文件夹是隐藏属性，且未勾选 “包含隐藏属性文件 / 文件夹”
- 程序无访问该文件 / 文件夹的权限（会在控制台输出权限不足提示）

Q3：点击 HTML 中的文件链接无反应

A：

- 确保勾选了 “为文件添加本地链接” 后生成的 HTML
- 部分浏览器对本地 URI 链接有安全限制，可右键链接选择 “在新标签页中打开”

Q4：生成过程中点击 “停止生成” 无立即响应

A：程序会等待当前处理的目录 / 文件完成后停止，若处理大目录可能有短暂延迟，属于正常现象。

Q5：macOS/Linux 系统下隐藏文件识别异常

A：程序通过文件名是否以.开头 + 系统标志位判断隐藏文件，若仍有异常，可检查文件的隐藏属性设置。

Q6：tkinter 报错

A: 检查是否安装了tkinter模块

# 模板文件基础规则

文件位置要求

自定义模板文件需命名为 template.html，并放置在 Tree2HTML.py（或可执行文件）的同目录下

核心模板变量

| 变量名 | 含义 | 示例 |
| :---: | :---: | :---: |
| `$title` | 快照标题 | `<title>$title的快照</title>` |
| `$root_display` | 根目录展示名称（转义后的文件夹名） | `<h1>快照: $root_display</h1>` |
| `$dirs_count` | 遍历统计的文件夹总数 | `<p class="count-info">共 $dirs_count 个文件夹 \| $files_count 个文件</p>` |
| `$files_count` | 遍历统计的文件总数 | 同上 |
| `$now` | HTML 生成时间（格式：YYYY-MM-DD HH:MM:SS） | `<p class="small">生成时间: $now</p>` |
| `$tree_html` | 核心树形结构 HTML 片段（由 Python 遍历生成的 li 标签拼接而成） | `<ul id="tree">$tree_html</ul>` |

CSS 样式

`.dir/.file` 标记目录 / 文件节点（Python 生成 li 时添加）

`data-error='true'` 标记权限不足 / 访问失败的目录（Python 生成）

以上为最基础变量，其余部分可以自由发挥

可以参考默认的模板文件

# 默认模板CSS部分参考样例

修改树形结构线条样式

```css
/* 替换默认的灰色竖线为虚线 */
li::before {
    background: #999;
    border-left: 1px dashed #999;
    width: 0; /* 隐藏原实线，改用虚线边框 */
}
```

调整搜索匹配高亮色

```css
.match {
    background: #e1f5fe; /* 浅蓝色高亮 */
    color: #000;
}
```

关闭 “全部展开 / 收起” 功能

```css
#toggle-all-btn {
    display: none;
}
```

# License

CC BY-NC-SA 4.0

[署名—非商业性使用—相同方式共享 4.0 协议国际版](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh-hans)
