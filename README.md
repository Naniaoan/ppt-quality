# PPT Quality · 让幻灯片"真的"变好

一个给 Claude Code 用的 Skill：把"美化 PPT"从**改颜色**变成**改结构**，并且改完必须渲染成图逐页验收。

> 大多数"AI 美化 PPT"只是换配色、加圆角、调字号，版式和信息关系原样不动——所以看起来还是同一份稿子。
> 这个 Skill 的顺序是：**先定场景 → 再定信息结构 → 再选视觉语法 → 最后才上色**，并且自带渲染、校验脚本，让"看不懂想象、只能凭感觉"这件事有解。

## 它解决什么

- **场景决定标准**：招生宣讲要"讲得清、可信、能复述"，不是苹果发布会那套大图少字。上来就套"高级感"是错的。
- **一页一件事**：写不出一句话结论的页，不该画。
- **标题写结论**：只读全部标题，应该能读出一整条论证。
- **版式有参数**：16:9 栅格、字号阶梯、间距两档、光学居中，不靠手感。
- **颜色有依据**：品牌色（去官网查）> 内容语义 > 场景，而不是模板色或审美偏好。
- **改完要看图**：自带 pptx → PNG 渲染器，逐页检查溢出、重叠、悬空。
- **不许悄悄丢信息**：校验脚本会对比原稿，列出被改丢的句子。

## 目录结构

```
ppt-quality/
├── SKILL.md                     # 方法论 + 执行手册（Claude 读这个）
└── scripts/
    ├── render_deck.sh           # pptx → 逐页 PNG（渲染验收）
    ├── render_slides.py         # 渲染器：OOXML → 绝对定位 HTML
    ├── slidekit.py              # OOXML 形状构建器（矩形/圆/线/富文本/图片）
    └── validate_pptx.py         # 结构校验 + 丢失文本比对
```

## 安装

把整个目录放进 Claude Code 的 skills 目录：

```bash
cp -r ppt-quality ~/.claude/skills/
```

之后在对话里说"帮我美化这份 PPT"，Claude 会自动加载它。

## 环境要求

- **macOS**（脚本里的 Chrome 路径是 macOS 的；Linux 改一下 `render_deck.sh` 里的 `CHROME` 变量即可）
- **Google Chrome**（无头截图）
- **Python 3.8+**，只用标准库
- **不需要** PowerPoint / LibreOffice / python-pptx

## 快速开始

```bash
# 1. 渲染一份 pptx，得到每页 PNG
bash scripts/render_deck.sh deck.pptx ./out
#    -> ./out/pngs/slide01.png ...

# 2. 校验（可选带原稿，会列出被改丢的文字）
python3 scripts/validate_pptx.py new.pptx original.pptx
```

> `render_deck.sh` 需要在**沙箱外**运行（Claude Code 的 terminal 工具或你自己的终端）：Chrome 的无头模式在受限沙箱里会因 socket 权限失败。

## 校验覆盖什么

- zip 完整性、每个 XML 能否解析
- 关系（rels）是否都指向真实存在的部件
- 嵌入图片是否有对应的 content-type（漏了 PowerPoint 会直接报错）
- 每页形状 id 是否唯一、是否有元素跑出画布
- 与原稿对比：哪些句子在改写后消失了（区分"重写"和"丢失"）

## 十条踩过的坑

手册里 ADR 式地记了 10 个真实问题，包括：散文本框叠字、列宽算错冲出画布、helper 空调用导致分隔线全部消失、细线太细看不见、大编号抢戏、装饰元素悬空、改写丢信息、先换色后排版、容器大于内容、不查品牌色就选色。

## License

MIT
