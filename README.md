# README.md
一个将Obsidain单独打包成hexo文章的脚本。将Obsidain中的笔记转换为hexo文章（zip格式），支持图片、绘图、内部链接等。支持callout转换。

可以直接将内容复制到hexo文章内。

A script that packages individual Obsidian notes into Hexo posts. It converts notes from Obsidian into Hexo articles（zip format）, with support for images, drawings, internal links, and callout block conversion.

You can directly copy the content to your Hexo article.

It can package your images from the attachments folder.

### 1. 脚本文件 obsidian2hexo.py
### 核心功能： 规则 A - Callout 语法转换
- 支持所有 Obsidian Callout 类型（note, info, abstract, summary, todo, tip, hint, success, check, warning, caution, failure, fail, missing, danger, error, bug, example, quote, cite）
- 自动转换为 Hexo 的 {% message %} 标签
- 正确处理多行 Callout 内容 规则 B - 图片与绘图语法转换
- 标准 ![[图片名.png]] → ![图片名](图片名.png)
- 带尺寸的 ![[图片名.png|100x145]] → `<img src="图片名.png" width="100" height="145" />`
- 仅宽度的 ![[图片名.png|100]] → `<img src="图片名.png" width="100" />`
- Excalidraw 绘图 ![[diagram.excalidraw]] → `![diagram](diagram.svg) `规则 C - 内部双链转换
- 内部标题链接 [[# 标题名称]] → `[标题名称](#标题名称) `（自动小写+连字符）
- 普通双链 [[文章B]] → [文章B](文章B) 打包功能
- 自动查找同级目录下的 attachments 文件夹
- 提取所有引用的图片文件
- 打包为 {原文件名}_hexo_ready.zip
- 自动清理临时目录
### 使用方法(Example)
```
python3 obsidian2hexo.py /path/to/your/note.md
```
### 测试结果
已通过测试！脚本成功转换了测试文件，生成的压缩包包含：

- 转换后的 Markdown 文件
- 提取的图片文件
脚本具有良好的鲁棒性，包含完善的错误处理和日志输出。