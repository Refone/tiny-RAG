# Markdown Splitter

一个**纯静态**的单页查看器:把 `chunks.json` **拖进页面**,查看切分结果。

页面不发任何网络请求,不执行 Python,也没有后端接口 —— 直接双击
`index.html` 打开即可(`file://` 也能用)。

## 用法

```bash
# 1) 生成数据: 按标题切分 Markdown, 写出 tmp/chunks.json
python src/utils/markdown_splitter.py
```

2. 双击打开 `tools/markdown-splitter/index.html`;
3. 把 `tmp/chunks.json` **拖进窗口任意位置**(或点右上角「打开 JSON」选择文件)。

重新生成数据后,再拖一次文件即可刷新。顶栏会显示当前文件名、
chunk 数量、文件大小和载入时间。

### 显示宽度

顶栏的 `width` 滑杆控制内容列的宽度(**相对窗口宽度的百分比, 默认 50%**),
内容在窗口中居中;点右侧的百分读数可一键恢复默认值。选择会被记在
`localStorage` 里, 下次打开自动恢复。

## 输入格式

一个 chunk 数组(`python src/utils/markdown_splitter.py` 的默认输出):

```json
[
  { "content": "该块的 Markdown 正文", "level": 2, "title_stack": ["第一章 初识智能体", "习题"] }
]
```

文件不是合法 JSON、或者顶层不是数组时,页面会直接显示失败原因和期望的格式。

## 生成数据

```bash
cd <repo root>                      # 脚本里的路径是相对当前目录的
python src/utils/markdown_splitter.py
# test/test-data/第一章-初识智能体.md  ->  tmp/chunks.json
```

切分参数(标题切分 + 超长块用 `RecursiveCharacterTextSplitter` 继续切)在脚本的
`__main__` 里固定为 `max_chunk_size=800, overlap_size=50`。

## 三种视图

| 视图     | 内容                                                                      |
| -------- | ------------------------------------------------------------------------- |
| `merge`  | 只用 JSON 里的信息把文档拼回去(标题取 `title_stack` 最后一项),默认视图     |
| `split`  | 每个 chunk 一张卡片:标题面包屑、标题层级、字符数,块与块之间有 `✂` 切分标记 |
| `meta`   | 原始 JSON:每个元素一张代码卡片(超宽自动换行),卡片和顶栏都有复制按钮       |

Markdown 渲染用 CDN 上的 `marked`;取不到 CDN 时会退化成等宽纯文本,
其余功能不受影响。

## 左侧长度条

载入数据后,左侧会出现一条 chunk 长度图:

- 每个 chunk 一根 bar,从上到下按顺序排列,**左对齐、向右延长**,长度 = 该 chunk 字符数 / 最长 chunk;
- 滚动页面时,视口顶部的那个 chunk 对应的 bar 会**高亮**(merge 视图按长度占比估算);
- **鼠标悬停** bar 显示该 chunk 的字符数;
- **点击** bar 平滑滚动到对应 chunk(`split` / `meta` 精确跳转,`merge` 按长度占比跳转);
- 高亮的 bar 滚出视野时,左侧条会自动把它带回可视区。

窄屏(`≤720px`)下长度条隐藏,优先保证正文可读。

## 文件

- `index.html` — 顶栏(文件名 / 宽度滑杆 / 视图切换 / 打开 JSON)、左侧长度条、预览容器、拖拽提示层。
- `app.js` — 拖拽与文件读取、显示宽度、三种视图渲染、左侧长度条。无任何网络请求。
- `styles.css` — 布局、内容列宽度、长度条、投放区与卡片 / JSON / Markdown 排版。
- `../../src/utils/markdown_splitter.py` — 真正的切分逻辑,由命令行运行,
  负责生成 `tmp/chunks.json`。
