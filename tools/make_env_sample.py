#!/usr/bin/env python3
"""把 .env 复制为 .env.sample，敏感值等长替换为 *（保留 sk- 之类前缀）"""

import re
from pathlib import Path

SRC, DST = Path(".env"), Path(".env.sample")

# 变量名以这些词结尾（前缀用 _ 或 . 分隔）则视为敏感
SENSITIVE = re.compile(
    r"(^|[_.])(KEY|SECRET|TOKEN|PASSWORD|PASSWD|PWD|PASS|"
    r"CREDENTIALS?|SALT|SIGNATURE|DSN|CONNECTION_?STRING)$",
    re.IGNORECASE,
)

# KEY=VALUE / export KEY=VALUE
LINE = re.compile(
    r"^(?P<pre>\s*(?:export\s+)?)"
    r"(?P<key>[A-Za-z_][A-Za-z0-9_.\-]*)"
    r"(?P<sep>\s*=\s*)"
    r"(?P<val>.*)$"
)

# 无信息含量的前缀：sk- / pk- / ghp_ / pat- ...
PREFIX = re.compile(r"^([a-z]{2,5}[-_])")


def mask(raw: str) -> str:
    """等长替换为 *，保留引号、前缀（sk- 等）和行尾注释。"""
    val = raw.strip()
    if not val:
        return raw

    # 行尾注释
    comment = ""
    for marker in (" #", "\t#"):
        i = val.find(marker)
        if i > 0:
            comment, val = val[i:], val[:i].rstrip()
            break

    # 引号
    quote = ""
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        quote, val = val[0], val[1:-1]

    # 保留无信息量的前缀（如 sk-），其余等长打码
    m = PREFIX.match(val)
    prefix = m.group(1) if m else ""
    body = val[len(prefix) :]

    return f"{quote}{prefix}{'*' * len(body)}{quote}{comment}"


def convert(text: str) -> str:
    # 无论源文件是 LF / CRLF / CR，统一按行切分
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out, n = [], 0
    for line in lines:
        m = LINE.match(line)
        if m and m.group("val").strip() and SENSITIVE.search(m.group("key")):
            line = (
                f"{m.group('pre')}{m.group('key')}"
                f"{m.group('sep')}{mask(m.group('val'))}"
            )
            n += 1
        out.append(line)
    print(f"✅ 已生成 {DST}（脱敏 {n} 处）")
    # 统一 LF + 恰好一个末尾换行
    return "\n".join(out).rstrip("\n") + "\n"


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"[error] 找不到 {SRC}")
    text = SRC.read_text(encoding="utf-8", errors="replace")
    data = convert(text).encode("utf-8")
    # 用二进制写入，彻底绕开 Windows 的 \n -> \r\n 自动转换
    DST.write_bytes(data)


if __name__ == "__main__":
    main()
