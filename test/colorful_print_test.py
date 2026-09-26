# color_picker.py
import sys

# ---------- 1. 颜色库 ----------
FOREGROUND = {
    "black":   30, "red":     31, "green":   32, "yellow":  33,
    "blue":    34, "magenta": 35, "cyan":    36, "white":   37,
    "bright_black":   90, "bright_red":     91, "bright_green":   92,
    "bright_yellow":  93, "bright_blue":    94, "bright_magenta": 95,
    "bright_cyan":    96, "bright_white":   97,
}

BACKGROUND = {name: code + 10 for name, code in FOREGROUND.items()}

STYLE = {
    "reset": 0, "bold": 1, "dim": 2, "italic": 3, "underline": 4,
    "blink": 5, "reverse": 7, "hidden": 8, "strike": 9,
}

RESET = "\033[0m"


def c(text, fg=None, bg=None, style=None):
    """把 text 包上 ANSI 码。fg/bg/style 支持颜色名或列表。"""
    codes = []
    for s in ([style] if isinstance(style, str) else (style or [])):
        codes.append(str(STYLE[s]))
    for f in ([fg] if isinstance(fg, str) else (fg or [])):
        codes.append(str(FOREGROUND[f]))
    for b in ([bg] if isinstance(bg, str) else (bg or [])):
        codes.append(str(BACKGROUND[b]))
    if not codes:
        return text
    return f"\033[{';'.join(codes)}m{text}{RESET}"


# ---------- 2. 预览所有颜色 ----------
def preview():
    print("\n=== 前景色 (fg) ===")
    for name, code in FOREGROUND.items():
        print(f"  {name:<15} \033[{code}m示例文字 Example\033[0m   \\033[{code}m")

    print("\n=== 背景色 (bg) ===")
    for name, code in BACKGROUND.items():
        print(f"  {name:<15} \033[{code}m示例文字 Example\033[0m   \\033[{code}m")

    print("\n=== 样式 (style) ===")
    for name, code in STYLE.items():
        print(f"  {name:<15} \033[{code}m示例文字 Example\033[0m   \\033[{code}m")

    print("\n=== 组合示例 ===")
    print("  " + c("警告 Warning", fg="yellow", style="bold"))
    print("  " + c("错误 Error",   fg="white",  bg="red",   style="bold"))
    print("  " + c("成功 Success", fg="bright_green"))
    print("  " + c("提示 Info",    fg="bright_cyan", style="underline"))


# ---------- 3. 交互式挑选 ----------
def pick():
    print("\n输入颜色名(可多个用逗号隔开)，例如：")
    print("  红字:      red")
    print("  加粗黄字:  yellow,bold")
    print("  红底白字:  white,on_red")
    print("  回车退出")
    print("\n可用名:", ", ".join(FOREGROUND))
    print("背景加 on_ 前缀, 样式:", ", ".join(STYLE))

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            break

        fg, bg, style = None, None, []
        for tok in map(str.strip, raw.split(",")):
            if not tok:
                continue
            if tok.startswith("on_"):
                bg = tok[3:]
            elif tok in STYLE:
                style.append(tok)
            elif tok in FOREGROUND:
                fg = tok
            else:
                print(f"  ✗ 未知: {tok}")
                fg = bg = None
                break
        if fg is None and bg is None and not style:
            continue

        print("  预览: " + c("示例文字 Example", fg=fg, bg=bg, style=style or None))
        # 生成可直接粘贴的常量
        print("  用法: " + c("print(c('hello', fg=%r, bg=%r, style=%r))"
                             % (fg, bg, style or None),
                             fg="bright_black"))


if __name__ == "__main__":
    preview()
    pick()