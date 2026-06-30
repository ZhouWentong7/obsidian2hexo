#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian 到 Hexo 的 Markdown 转换工具
功能：将 Obsidian 的 Markdown 笔记转换为 Hexo 兼容格式，并打包相关图片
"""

import re
import sys
import shutil
import zipfile
import argparse
import logging
from pathlib import Path


# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


# Callout 类型映射字典
CALLOUT_MAPPING = {
    'note': {'color': 'info', 'icon': 'fa-solid fa-circle-info', 'title': 'NOTE'},
    'info': {'color': 'info', 'icon': 'fa-solid fa-circle-info', 'title': 'NOTE'},
    'abstract': {'color': 'success', 'icon': 'fa-solid fa-box-archive', 'title': 'ABSTRACT'},
    'summary': {'color': 'success', 'icon': 'fa-solid fa-box-archive', 'title': 'ABSTRACT'},
    'todo': {'color': 'info', 'icon': 'fa-solid fa-list-check', 'title': 'TODO'},
    'tip': {'color': 'success', 'icon': 'fa-solid fa-lightbulb', 'title': 'TIP'},
    'hint': {'color': 'success', 'icon': 'fa-solid fa-lightbulb', 'title': 'TIP'},
    'success': {'color': 'success', 'icon': 'fa-solid fa-circle-check', 'title': 'SUCCESS'},
    'check': {'color': 'success', 'icon': 'fa-solid fa-circle-check', 'title': 'SUCCESS'},
    'warning': {'color': 'warning', 'icon': 'fa-solid fa-triangle-exclamation', 'title': 'WARNING'},
    'caution': {'color': 'warning', 'icon': 'fa-solid fa-triangle-exclamation', 'title': 'WARNING'},
    'failure': {'color': 'danger', 'icon': 'fa-solid fa-circle-xmark', 'title': 'FAILURE'},
    'fail': {'color': 'danger', 'icon': 'fa-solid fa-circle-xmark', 'title': 'FAILURE'},
    'missing': {'color': 'danger', 'icon': 'fa-solid fa-circle-xmark', 'title': 'FAILURE'},
    'danger': {'color': 'danger', 'icon': 'fa-solid fa-skull-crossbones', 'title': 'DANGER'},
    'error': {'color': 'danger', 'icon': 'fa-solid fa-skull-crossbones', 'title': 'DANGER'},
    'bug': {'color': 'danger', 'icon': 'fa-solid fa-bug', 'title': 'BUG'},
    'example': {'color': 'info', 'icon': 'fa-solid fa-flask', 'title': 'EXAMPLE'},
    'quote': {'color': 'info', 'icon': 'fa-solid fa-quote-left', 'title': 'QUOTE'},
    'cite': {'color': 'info', 'icon': 'fa-solid fa-quote-left', 'title': 'QUOTE'}
}

# 默认的 Callout 配置
DEFAULT_CALLOUT = {'color': 'info', 'icon': 'fa-solid fa-circle-info', 'title': 'NOTE'}


def parse_front_matter(content: str) -> dict[str, str]:
    """
    解析 Front-matter，提取所有元数据字段
    """
    front_matter: dict[str, str] = {}
    if content.startswith('---'):
        end_idx = content.find('---', 3)
        if end_idx != -1:
            fm_content = content[3:end_idx].strip()
            for line in fm_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    front_matter[key.strip()] = value.strip()
    return front_matter


def _get_blockquote_level(line: str) -> int:
    """统计行开头的块引用层级数（'>' 符号数量）"""
    match = re.match(r'^(?:\s*>\s*)*', line)
    return match.group().count('>') if match else 0


def _strip_blockquote_prefix(line: str) -> str:
    """去除行首的块引用前缀（所有 '>' 及其间空格）"""
    return re.sub(r'^(?:\s*>\s*)+', '', line).lstrip()


def convert_callouts(content: str) -> str:
    """
    规则 A：转换 Callout 语法（支持嵌套）
    使用栈结构处理多层嵌套的 Obsidian Callout。
    """
    lines = content.split('\n')
    result: list[str] = []
    # 栈中每个元素：(层级, config, title)
    callout_stack: list[tuple[int, dict[str, str], str]] = []

    for line in lines:
        level = _get_blockquote_level(line)

        if level == 0:
            # 不在块引用中 → 关闭所有打开的 Callout
            while callout_stack:
                _ = callout_stack.pop()
                result.append('{% endmessage %}')
            result.append(line)
            continue

        stripped = _strip_blockquote_prefix(line)
        callout_match = re.match(r'^\[!([^\]]+)\](.*?)$', stripped)

        if callout_match:
            # 这是一个 Callout 开始标记
            callout_type = callout_match.group(1).strip().lower()
            optional_title = callout_match.group(2).strip()
            config = CALLOUT_MAPPING.get(callout_type, DEFAULT_CALLOUT)
            title = optional_title if optional_title else config['title']
            # 防止标题中的引号破坏 Hexo 标签
            safe_title = title.replace('"', '\\"')

            # 关闭同级或更深层级的 Callout
            while callout_stack and callout_stack[-1][0] >= level:
                _ = callout_stack.pop()
                result.append('{% endmessage %}')

            callout_stack.append((level, config, title))
            result.append(
                f'{{% message color:{config["color"]} size:default icon:"{config["icon"]}" title:"{safe_title}" %}}'
            )
        else:
            # 普通块引用内容 → 关闭更深层级的 Callout
            while callout_stack and callout_stack[-1][0] > level:
                _ = callout_stack.pop()
                result.append('{% endmessage %}')

            if callout_stack:
                result.append(stripped)
            else:
                # 不在任何 Callout 中的块引用，原样保留
                result.append(line)

    # 关闭所有剩余的 Callout
    while callout_stack:
        _ = callout_stack.pop()
        result.append('{% endmessage %}')

    return '\n'.join(result)


def _normalize_image_prefix(prefix: str) -> str:
    """规范化图片路径前缀：确保以 '/' 结尾，或为空字符串"""
    if not prefix:
        return ''
    prefix = prefix.strip()
    if not prefix.endswith('/'):
        prefix += '/'
    return prefix


def _replace_excalidraw(filename: str) -> str:
    """将 .excalidraw 扩展名替换为 .svg"""
    if filename.endswith('.excalidraw'):
        return filename.replace('.excalidraw', '.svg')
    return filename


def convert_images(content: str, prefix: str = '') -> tuple[str, list[str]]:
    """
    规则 B：转换图片与绘图语法
    返回转换后的内容和提取的图片文件名列表
    prefix: 图片路径前缀（如 '/images/'），默认为空
    """
    image_files: list[str] = []
    normalized_prefix = _normalize_image_prefix(prefix)

    # 1. 处理带有宽高的图片 [[图片名.png|100x145]] 或 [[图片名.png|100]]
    def replace_image_with_size(match: re.Match[str]) -> str:
        filename = _replace_excalidraw(match.group(1))
        size_part = match.group(2)

        image_files.append(filename)

        width: str | None = None
        height: str | None = None

        if 'x' in size_part:
            w, h = size_part.split('x', 1)
            if w.isdigit():
                width = w
            if h.isdigit():
                height = h
        elif size_part.isdigit():
            width = size_part

        attrs: list[str] = []
        if width:
            attrs.append(f'width="{width}"')
        if height:
            attrs.append(f'height="{height}"')

        return f'<img src="{normalized_prefix}{filename}" {" ".join(attrs)} />'

    content = re.sub(
        r'!\[\[([^|\]]+)\|([^\]]+)\]\]',
        replace_image_with_size,
        content
    )

    # 2. 处理标准的 Obsidian 图片 [[图片名.png]]
    def replace_simple_image(match: re.Match[str]) -> str:
        filename = _replace_excalidraw(match.group(1))

        image_files.append(filename)
        alt_text = Path(filename).stem

        return f'![{alt_text}]({normalized_prefix}{filename})'

    content = re.sub(
        r'!\[\[([^\]|]+)\]\]',
        replace_simple_image,
        content
    )

    return content, image_files


def convert_internal_links(content: str, _front_matter: dict[str, str] | None = None) -> str:
    """
    规则 C：转换内部双链
    _front_matter 保留供未来扩展（如 hexo-path 映射）
    """
    # 1. 处理内部标题链接 [[# 标题名称]]
    def replace_heading_link(match: re.Match[str]) -> str:
        heading = match.group(1).strip()
        # 转换为小写，空格替换为连字符
        anchor = heading.lower().replace(' ', '-')
        return f'[{heading}](#{anchor})'

    content = re.sub(
        r'\[\[#\s*([^\]]+)\]\]',
        replace_heading_link,
        content
    )

    # 2. 处理普通双链 [[文章B]]
    def replace_regular_link(match: re.Match[str]) -> str:
        link_text = match.group(1).strip()
        # 普通双链直接转换为同名链接
        return f'[{link_text}]({link_text})'

    content = re.sub(
        r'\[\[([^#\]]+)\]\]',
        replace_regular_link,
        content
    )

    return content


def find_attachments_dir(md_file_path: str) -> Path:
    """
    查找附件文件夹
    优先查找 md 文件同级目录下的 attachments 文件夹，返回 Path 对象。
    """
    md_path = Path(md_file_path).resolve()
    md_dir = md_path.parent

    # 检查 attachments 文件夹
    attachments_dir = md_dir / 'attachments'
    if attachments_dir.exists():
        return attachments_dir

    # 尝试一些常见的附件文件夹名称
    common_names = ['Attachments', 'assets', 'Assets', 'images', 'Images']
    for name in common_names:
        candidate = md_dir / name
        if candidate.exists():
            return candidate

    # 如果都没找到，返回 md 文件所在目录
    return md_dir


def extract_image_files(
    image_files: list[str],
    attachments_dir: Path,
    output_dir: Path,
) -> list[str]:
    """
    从附件文件夹中提取图片文件到输出目录
    attachments_dir 和 output_dir 均为 Path 对象
    """
    copied_files: list[str] = []

    for filename in image_files:
        src_path = attachments_dir / filename
        dst_path = output_dir / filename

        if src_path.exists():
            try:
                _ = shutil.copy2(str(src_path), str(dst_path))
                copied_files.append(filename)
                logging.info('已复制图片: %s', filename)
            except OSError as e:
                logging.warning('复制图片 %s 失败: %s', filename, e)
        else:
            # 尝试查找 Excalidraw 的 svg 版本（如果原始是 excalidraw）
            if filename.endswith('.svg'):
                excalidraw_src = attachments_dir / filename.replace('.svg', '.excalidraw')
                if excalidraw_src.exists():
                    logging.info(
                        '提示: 找到 %s，但需要手动转换为 SVG',
                        filename.replace('.svg', '.excalidraw'),
                    )
            logging.warning('未找到图片文件: %s', filename)

    return copied_files


def create_zip(output_dir: Path, zip_path: Path) -> None:
    """
    创建 ZIP 压缩包，确保中文文件名正确编码
    output_dir 和 zip_path 均为 Path 对象
    """
    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in output_dir.rglob('*'):
            if file_path.is_file():
                arcname = str(file_path.relative_to(output_dir))
                # 使用 UTF-8 编码确保中文文件名正确
                zipf.write(str(file_path), arcname)
                # 设置通用位标志，指示文件名使用 UTF-8 编码
                zipinfo = zipf.getinfo(arcname)
                zipinfo.flag_bits |= 0x800


def main() -> None:
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='Obsidian Markdown 转 Hexo 格式工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例: python obsidian2hexo.py /path/to/note.md'
    )
    _ = parser.add_argument('md_file', help='Obsidian Markdown 文件路径')
    _ = parser.add_argument(
        '--image-prefix', default='',
        help='图片路径前缀（如 /images/），默认为空'
    )

    args = parser.parse_args()
    md_file: str = args.md_file  # type: ignore[arg-type]
    image_prefix: str = args.image_prefix  # type: ignore[arg-type]

    # 使用 Path 对象处理文件路径，完美支持中文
    md_path = Path(md_file).resolve()

    # 检查输入文件是否存在
    if not md_path.exists():
        logging.error('文件不存在: %s', md_path)
        sys.exit(1)

    if md_path.suffix.lower() != '.md':
        logging.warning('输入文件不是 .md 格式，继续处理...')

    # 读取源文件
    logging.info('正在读取文件: %s', md_path)
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError as e:
        logging.error('读取文件失败: %s', e)
        sys.exit(1)

    # 解析 Front-matter
    front_matter = parse_front_matter(content)

    # 执行转换（注意顺序很重要）
    logging.info('正在转换语法...')

    # 先转换 Callout
    try:
        content = convert_callouts(content)
    except Exception as e:
        logging.error('Callout 转换失败: %s', e)
        sys.exit(1)

    # 转换图片并提取图片文件名
    try:
        content, image_files = convert_images(content, image_prefix)
    except Exception as e:
        logging.error('图片转换失败: %s', e)
        sys.exit(1)

    # 转换内部链接
    try:
        content = convert_internal_links(content, front_matter)
    except Exception as e:
        logging.error('内部链接转换失败: %s', e)
        sys.exit(1)

    # 去重图片文件
    image_files = list(set(image_files))

    # 创建临时输出目录
    md_filename = md_path.name
    md_name = md_path.stem
    current_dir = Path.cwd()
    output_dir = current_dir / f'{md_name}_temp'
    zip_path = current_dir / f'{md_name}_hexo_ready.zip'

    # ----- 处理阶段（细粒度异常）-----
    # 1. 创建临时目录
    try:
        if output_dir.exists():
            shutil.rmtree(str(output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        logging.info('创建临时目录: %s', output_dir)
    except OSError as e:
        logging.error('创建临时目录失败: %s', e)
        sys.exit(1)

    # 2. 保存转换后的 Markdown 文件
    try:
        output_md = output_dir / md_filename
        with open(output_md, 'w', encoding='utf-8') as f:
            _ = f.write(content)
        logging.info('保存转换后的文件: %s', md_filename)
    except OSError as e:
        logging.error('写入 Markdown 文件失败: %s', e)
        _cleanup(output_dir)
        sys.exit(1)

    # 3. 查找附件并提取图片
    attachments_dir = find_attachments_dir(str(md_path))
    logging.info('附件目录: %s', attachments_dir)

    if image_files:
        logging.info('正在提取图片文件...')
        try:
            copied = extract_image_files(image_files, attachments_dir, output_dir)
            logging.info('成功复制 %d/%d 张图片', len(copied), len(image_files))
        except Exception as e:
            logging.warning('提取图片过程出现异常: %s', e)
    else:
        logging.info('未找到需要提取的图片')

    # 4. 创建 ZIP 文件
    try:
        logging.info('正在创建压缩包: %s', zip_path.name)
        create_zip(output_dir, zip_path)
        logging.info('转换完成！压缩包已保存: %s', zip_path)
    except (OSError, zipfile.BadZipFile) as e:
        logging.error('创建 ZIP 压缩包失败: %s', e)
        _cleanup(output_dir)
        sys.exit(1)

    # 清理临时目录
    _cleanup(output_dir)


def _cleanup(dir_path: Path) -> None:
    """安全删除临时目录"""
    if dir_path.exists():
        try:
            shutil.rmtree(str(dir_path))
            logging.info('已清理临时目录')
        except OSError as e:
            logging.warning('删除临时目录失败: %s', e)


if __name__ == '__main__':
    main()
