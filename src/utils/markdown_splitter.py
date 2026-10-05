
import copy
import re
from typing import TypedDict

from langchain_text_splitters import RecursiveCharacterTextSplitter

class Chunk(TypedDict):
    content: str
    level: int
    title_stack: list[str]

_TITLE_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_CODE_RE = re.compile(r'^[ \t]{0,3}(`{3,}|~{3,})')

def markdown_split_by_title(
    md_content:str,
    ) -> list[Chunk]:
    chunk_list = []

    md_lines = md_content.splitlines()  # 将内容按行分割
    current_title:list[str] = []
    current_level = 0
    current_content_lines:list[str] = []
    is_code = False

    for line_num, line in enumerate(md_lines):
        # 跳过空行
        if not line.strip():
            # 为不破坏 md 结构，仍然把空行加入 current_content_lines
            current_content_lines.append(line)
            continue

        # 代码行不分块，整块吞下
        if _CODE_RE.match(line):
            is_code = not is_code
            current_content_lines.append(line)
            continue

        if is_code:
            current_content_lines.append(line)
            continue

        # 判断当前行是正文还是标题
        if _TITLE_RE.match(line):
        # 当前行是标题
            if current_content_lines:
                # 之前 content 中有内容，这是一个新块的开始
                # 处理之前的 block
                last_content = "\n".join(current_content_lines).strip()
                last_level = current_level
                last_chunk = Chunk(
                    content=last_content,
                    level=last_level,
                    title_stack=copy.deepcopy(current_title),
                )
                if last_content:  # 只有当内容不为空时才加入 chunk_list
                    chunk_list.append(last_chunk)
            # 重置当前的状态
            current_level = len(_TITLE_RE.match(line).group(1))
            current_content_lines.clear()
            # current_content_lines.append(line)  # 把标题本身也加入到当前内容中
            current_title[max(current_level-1,0):] = [_TITLE_RE.match(line).group(2)]
            continue

        else:
        # 当前行是正文
            current_content_lines.append(line)

    if current_content_lines:
        last_content = "\n".join(current_content_lines).strip()
        last_level = current_level
        last_chunk = Chunk(
            content=last_content,
            level=last_level,
            title_stack=copy.deepcopy(current_title),
        )
        if last_content:  # 只有当内容不为空时才加入 chunk_list
            chunk_list.append(last_chunk)

    return chunk_list

def _split_oversized_chunks(
    chunk_list: list[Chunk],
    max_chunk_size: int,
    overlap_size: int) -> list[Chunk]:

    result_chunks: list[Chunk] = []

    for chunk in chunk_list:
        if len(chunk["content"]) > max_chunk_size:
        # 块过长，需要拆分
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=max_chunk_size,
                chunk_overlap=overlap_size,
                length_function=len,
                is_separator_regex=True,
                separators=[
                        r"\n(?=#{1,6} )",      # 标题前换行，标题保留到下一块
                        r"\n(?=```)",          # 代码块前换行
                        r"\n(?=~~~)",          # 另一种代码块
                        r"\n\n",               # 段落
                        r"\n(?=[-*+] )",       # 无序列表项
                        r"\n(?=\d+\. )",       # 有序列表项，匹配任意数字
                        r"\n",                 # 换行
                        r"(?<=[。！？!?])",     # 中英文句子结束
                ],
            )

            split_chunks = splitter.split_text(chunk["content"])

            for split_text in split_chunks:
                result_chunks.append(Chunk(
                    content=split_text,
                    level=chunk["level"],
                    title_stack=copy.deepcopy(chunk["title_stack"]),
                ))
        else:
            result_chunks.append(chunk)

    return result_chunks

def split_markdown(md_content: str,
                   max_chunk_size: int,
                   overlap_size: int,
                   ) -> list[Chunk]:
    # 1. 首先按照标题层级切分
    chunk_list = markdown_split_by_title(md_content)

    # 2. 超长块继续切分, 同时保持 chunk 顺序不变
    chunk_list = _split_oversized_chunks(chunk_list, max_chunk_size, overlap_size)

    return chunk_list

if __name__ == "__main__":
    import json
    import os

    from rich import print as rprint
    md_content = ""
    md_path = "test/test-data/第一章-初识智能体.md"
    with open(md_path, "r") as f:
        md_content = f.read()

    chunk_list = split_markdown(md_content, max_chunk_size=800, overlap_size=50)
    for chunk in chunk_list:
        rprint(chunk)

    output_path = os.path.join("tmp", "chunks.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunk_list, f, ensure_ascii=False, indent=2)
    rprint(f"[green]已写入 {len(chunk_list)} 个 chunk 到 {output_path}[/green]")