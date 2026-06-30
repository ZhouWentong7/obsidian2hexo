#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian 到 Hexo 的 Markdown 转换工具
功能：将 Obsidian 的 Markdown 笔记转换为 Hexo 兼容格式，并打包相关图片
"""

import re
import os
import sys
import shutil
import zipfile
import argparse
from pathlib import Path


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


def parse_front_matter(content):
    """
    解析 Front-matter，提取 hexo-path 信息
    """
    front_matter = {}
    if content.startswith('---'):
        end_idx = content.find('---', 3)
        if end_idx != -1:
            fm_content = content[3:end_idx].strip()
            for line in fm_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    front_matter[key.strip()] = value.strip()
    return front_matter


def convert_callouts(content):
    """
    规则 A：转换 Callout 语法
    """
    lines = content.split('\n')
    result = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # 检查是否是 Callout 开始
        callout_match = re.match(r'^>\s*\[!([^\]]+)\](.*?)$', line)
        if callout_match:
            callout_type = callout_match.group(1).strip().lower()
            optional_title = callout_match.group(2).strip()

            # 获取 Callout 配置
            config = CALLOUT_MAPPING.get(callout_type, DEFAULT_CALLOUT)
            title = optional_title if optional_title else config['title']

            # 收集 Callout 内容行
            callout_content = []
            i += 1
            while i < n:
                next_line = lines[i]
                if next_line.startswith('>'):
                    # 去除 > 前缀
                    content_line = next_line[1:].lstrip()
                    callout_content.append(content_line)
                    i += 1
                else:
                    break

            # 构建 Hexo message 标签
            result.append(
                f'{{% message color:{config["color"]} size:default icon:"{config["icon"]}" title:"{title}" %}}'
            )
            if callout_content:
                result.extend(callout_content)
            result.append('{% endmessage %}')
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def convert_images(content):
    """
    规则 B：转换图片与绘图语法
    返回转换后的内容和提取的图片文件名列表
    """
    image_files = []

    # 1. 处理带有宽高的图片 [[图片名.png|100x145]] 或 [[图片名.png|100]]
    def replace_image_with_size(match):
        filename = match.group(1)
        size_part = match.group(2)

        # 处理 Excalidraw 文件
        if filename.endswith('.excalidraw'):
            filename = filename.replace('.excalidraw', '.svg')

        image_files.append(filename)

        width = None
        height = None

        if 'x' in size_part:
            w, h = size_part.split('x', 1)
            if w.isdigit():
                width = w
            if h.isdigit():
                height = h
        elif size_part.isdigit():
            width = size_part

        attrs = []
        if width:
            attrs.append(f'width="{width}"')
        if height:
            attrs.append(f'height="{height}"')

        return f'<img src="{filename}" {" ".join(attrs)} />'

    content = re.sub(
        r'!\[\[([^|\]]+)\|([^\]]+)\]\]',
        replace_image_with_size,
        content
    )

    # 2. 处理标准的 Obsidian 图片 [[图片名.png]]
    def replace_simple_image(match):
        filename = match.group(1)

        # 处理 Excalidraw 文件
        is_excalidraw = filename.endswith('.excalidraw')
        if is_excalidraw:
            filename = filename.replace('.excalidraw', '.svg')

        image_files.append(filename)
        alt_text = os.path.splitext(filename)[0]

        return f'![{alt_text}]({filename})'

    content = re.sub(
        r'!\[\[([^\]|]+)\]\]',
        replace_simple_image,
        content
    )

    return content, image_files


def convert_internal_links(content, front_matter):
    """
    规则 C：转换内部双链
    """
    # 1. 处理内部标题链接 [[# 标题名称]]
    def replace_heading_link(match):
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
    def replace_regular_link(match):
        link_text = match.group(1).strip()
        # 普通双链直接转换为同名链接，不使用当前文件的 hexo-path
        return f'[{link_text}]({link_text})'

    content = re.sub(
        r'\[\[([^#\]]+)\]\]',
        replace_regular_link,
        content
    )

    return content


def find_attachments_dir(md_file_path):
    """
    查找附件文件夹
    优先查找 md 文件同级目录下的 attachments 文件夹
    """
    md_dir = os.path.dirname(os.path.abspath(md_file_path))

    # 检查 attachments 文件夹
    attachments_dir = os.path.join(md_dir, 'attachments')
    if os.path.exists(attachments_dir):
        return attachments_dir

    # 尝试一些常见的附件文件夹名称
    common_names = ['Attachments', 'assets', 'Assets', 'images', 'Images']
    for name in common_names:
        candidate = os.path.join(md_dir, name)
        if os.path.exists(candidate):
            return candidate

    # 如果都没找到，返回 md 文件所在目录
    return md_dir


def extract_image_files(image_files, attachments_dir, output_dir):
    """
    从附件文件夹中提取图片文件到输出目录
    """
    copied_files = []

    for filename in image_files:
        src_path = os.path.join(attachments_dir, filename)
        dst_path = os.path.join(output_dir, filename)

        if os.path.exists(src_path):
            try:
                shutil.copy2(src_path, dst_path)
                copied_files.append(filename)
                print(f'已复制图片: {filename}')
            except Exception as e:
                print(f'警告: 复制图片 {filename} 失败: {e}')
        else:
            # 尝试查找 Excalidraw 的 svg 版本（如果原始是 excalidraw）
            if filename.endswith('.svg'):
                excalidraw_src = os.path.join(attachments_dir, filename.replace('.svg', '.excalidraw'))
                if os.path.exists(excalidraw_src):
                    print(f'提示: 找到 {filename.replace(".svg", ".excalidraw")}，但需要手动转换为 SVG')
            print(f'警告: 未找到图片文件: {filename}')

    return copied_files


def create_zip(output_dir, zip_path):
    """
    创建 ZIP 压缩包
    """
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, output_dir)
                zipf.write(file_path, arcname)


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='Obsidian Markdown 转 Hexo 格式工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例: python obsidian2hexo.py /path/to/note.md'
    )
    parser.add_argument('md_file', help='Obsidian Markdown 文件路径')

    args = parser.parse_args()

    # 检查输入文件是否存在
    md_file = args.md_file
    if not os.path.exists(md_file):
        print(f'错误: 文件不存在: {md_file}')
        sys.exit(1)

    if not md_file.endswith('.md'):
        print(f'警告: 输入文件不是 .md 格式，继续处理...')

    # 读取源文件
    print(f'正在读取文件: {md_file}')
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f'错误: 读取文件失败: {e}')
        sys.exit(1)

    # 解析 Front-matter
    front_matter = parse_front_matter(content)

    # 执行转换（注意顺序很重要）
    print('正在转换语法...')

    # 先转换 Callout
    content = convert_callouts(content)

    # 转换图片并提取图片文件名
    content, image_files = convert_images(content)

    # 转换内部链接
    content = convert_internal_links(content, front_matter)

    # 去重图片文件
    image_files = list(set(image_files))

    # 创建临时输出目录
    md_filename = os.path.basename(md_file)
    md_name = os.path.splitext(md_filename)[0]
    output_dir = f'{md_name}_temp'
    current_dir = os.getcwd()

    try:
        # 创建输出目录
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)
        print(f'创建临时目录: {output_dir}')

        # 保存转换后的 Markdown 文件
        output_md = os.path.join(output_dir, md_filename)
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'保存转换后的文件: {md_filename}')

        # 查找附件文件夹
        attachments_dir = find_attachments_dir(md_file)
        print(f'附件目录: {attachments_dir}')

        # 提取图片文件
        if image_files:
            print('正在提取图片文件...')
            extract_image_files(image_files, attachments_dir, output_dir)
        else:
            print('未找到需要提取的图片')

        # 创建 ZIP 文件
        zip_filename = f'{md_name}_hexo_ready.zip'
        zip_path = os.path.join(current_dir, zip_filename)
        print(f'正在创建压缩包: {zip_filename}')
        create_zip(output_dir, zip_path)

        print(f'\n✅ 转换完成！')
        print(f'压缩包已保存: {zip_path}')

    except Exception as e:
        print(f'错误: 处理过程中发生异常: {e}')
        sys.exit(1)
    finally:
        # 清理临时目录
        if os.path.exists(output_dir):
            try:
                shutil.rmtree(output_dir)
                print(f'已清理临时目录')
            except Exception as e:
                print(f'警告: 删除临时目录失败: {e}')


if __name__ == '__main__':
    main()
