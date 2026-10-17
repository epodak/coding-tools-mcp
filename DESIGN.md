# Design System & Visual Tokens

<!-- design-system:oceanic-crisp-light 1 -->

> **视觉基准单一真源**：遵循 [AGENTS.md](file:///c:/Users/root/AGENTS.md) 规定的 **Oceanic Crisp Light（冰川瓷白海蓝 · 清爽主义）**。
> **浅色第一契约 (Light-First Contract)**：默认拒斥暗黑底座与赛博朋克地摊风。

---

## 🎨 调色盘与设计令牌 (Color Tokens)

| Token 语义 | 推荐色值 | 视觉用途 |
|---|---|---|
| `--canvas-bg` | `#F4F7FB` ~ `#EDF2F9` | **底色 (Misty Sea-Ice Canvas)**：冷海冰蓝灰/晨雾白，白昼天光漫反射质感 |
| `--surface-card` | `#FFFFFF` | **表面 (Porcelain Float)**：纯白白瓷卡片，浮于水面感 |
| `--text-primary` | `#0F172A` / `#1E293B` | **墨水 (Deep Oceanic Navy)**：深海石板墨蓝主文字，杜绝死黑 |
| `--text-muted` | `#64748B` | **次文字 (Sea Fog Slate)**：海雾灰辅助说明与标签 |
| `--primary` | `#0284C7` / `#2563EB` | **天海蓝 (Sky Oceanic Blue)**：核心强调色、主要操作入口 |
| `--success` | `#10B981` | **生机翠绿 (Vibrant Emerald)**：成功状态、运行正常标识 |
| `--warning` | `#F59E0B` | **珊瑚橙黄**：预警、提示点缀（克制使用） |
| `--border-subtle`| `rgba(215, 225, 240, 0.6)` | **微透光浅蓝边**：卡片与分隔线描边 |

---

## 📐 表面与阴影质感 (Porcelain Float)

- **容器圆角 (Border Radius)**：`14px ~ 18px`，大圆角柔和轮廓。
- **弥散软阴影 (Soft Shadow)**：`box-shadow: 0 10px 30px rgba(15, 30, 60, 0.04);`
- **呼吸感 (Negative Space)**：卡片内间距 `18px ~ 24px`，图表洗练通透。

---

## 🔤 排版与字体阶梯 (Typography)

- **主字体族**：`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif`
- **等宽代码字体**：`ui-monospace, "Cascadia Code", "Fira Code", monospace`
- **排版阶梯**：
  - H1 页面标题：`24px ~ 28px` / 700 / 行高 1.2
  - H2 板块标题：`18px ~ 20px` / 600 / 行高 1.3
  - 正文 Body：`14px ~ 15px` / 400 / 行高 1.5
  - 辅助 Caption：`12px ~ 13px` / 500 / 行高 1.4

---

## 🚫 视觉反模式禁令 (Anti-Patterns)

1. **严禁暗黑默认**：未经用户显式要求，严禁建立 `#000000` / `#070B12` 等沉重黑底；
2. **严禁赛博地摊风**：杜绝暗黑霓虹高亮描边发光线；
3. **色彩节制**：核心强调色收敛至天海蓝与生机绿，告别高饱和五颜六色。
