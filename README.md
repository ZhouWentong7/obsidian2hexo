# Obsidian2Hexo

将 Obsidian 笔记一键转换为 Hexo 兼容格式（ZIP 包），支持图片、绘图（Excalidraw）、内部链接、Callout 块等。

A script that packages individual Obsidian notes into Hexo posts (ZIP format), supporting images, drawings (Excalidraw), internal links, and Callout block conversion.

---

## 核心功能 / Features

### 规则 A — Callout 语法转换

- 支持所有 Obsidian Callout 类型（note, info, abstract, summary, todo, tip, hint, success, check, warning, caution, failure, fail, missing, danger, error, bug, example, quote, cite）
- 自动转换为 Hexo 的 `{% message %}` 标签
- **支持嵌套 Callout**（多层 `>` 引用自动对应嵌套层级）

```
> [!note] 外层
> 外层内容
> > [!warning] 内层
> > 内层内容
> 回到外层
```
→
```
{% message color:info ... title:"外层" %}
外层内容
{% message color:warning ... title:"内层" %}
内层内容
{% endmessage %}
回到外层
{% endmessage %}
```

### 规则 B — 图片与绘图语法转换

| Obsidian 语法 | 转换结果 |
|---|---|
| `![[图片名.png]]` | `![图片名](图片名.png)` |
| `![[图片名.png\|100x145]]` | `<img src="图片名.png" width="100" height="145" />` |
| `![[图片名.png\|100]]` | `<img src="图片名.png" width="100" />` |
| `![[diagram.excalidraw]]` | `![diagram](diagram.svg)`（自动转换扩展名） |

- 支持 `--image-prefix` 参数为图片路径添加前缀（如 `/images/`）

### 规则 C — 内部双链转换

| Obsidian 语法 | 转换结果 |
|---|---|
| `[[# 标题名称]]` | `[标题名称](#标题名称)`（自动小写+连字符） |
| `[[文章B]]` | `[文章B](文章B)` |

### 打包功能

- 自动查找同级目录下的 `attachments` / `assets` / `images` 等文件夹
- 提取所有引用的图片文件
- 打包为 `{原文件名}_hexo_ready.zip`
- 自动清理临时目录

---

## 使用方法 / Usage

```bash
# 基础用法
python obsidian2hexo.py "你的中文路径/笔记.md"

# 指定图片 URL 前缀（用于 Hexo 的 post_asset_folder 或 CDN）
python obsidian2hexo.py "笔记.md" --image-prefix /images/

# 或使用相对路径
python obsidian2hexo.py /path/to/note.md
```

### 参数说明

| 参数 | 说明 |
|---|---|
| `md_file` | Obsidian Markdown 文件路径（必填） |
| `--image-prefix` | 图片路径前缀（可选，默认为空），如 `/images/` 或 `https://cdn.example.com/img/` |

---

## 输出示例 / Output

运行后在同级目录生成 `{笔记名}_hexo_ready.zip`，内含：

- 转换后的 Markdown 文件（可直接复制到 Hexo 文章）
- 提取的所有图片文件

---

## 技术要点 / Technical Notes

- **日志分级**：使用 `logging` 模块，区分 INFO / WARNING / ERROR 级别
- **细粒度异常处理**：读取、转换、打包各阶段独立捕获异常，精确报错
- **路径统一**：全程使用 `pathlib.Path` 对象，完美支持中文路径
- **编码兼容**：ZIP 文件使用 UTF-8 标志位，确保中文文件名正确