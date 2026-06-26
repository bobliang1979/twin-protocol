# Playwright 高级定位模式参考

## 定位器构建原则

1. **从快照出发** — 每次导航或 DOM 变化后获取新鲜 `domSnapshot()`
2. **最具体优先** — 从最具体（getByRole + name）到最通用（CSS 选择器）
3. **作用域限定** — 始终在容器内定位，避免全局匹配

## 定位器优先级

| 优先级 | 方法 | 适用场景 |
|--------|------|----------|
| 1 | `getByRole("button", { name: "确切的accessible name" })` | 按钮、链接、导航项等带有 ARIA role 的元素 |
| 2 | `getByLabel("标签文本")` | 表单输入框，由 label 元素绑定 |
| 3 | `getByTestId("data-testid值")` | 有 data-testid 属性的元素 |
| 4 | `getByPlaceholder("占位符文本")` | 有 placeholder 的输入框 |
| 5 | `getByText("可见文本")` | 按内容文本定位，需作用域限定 |
| 6 | `locator("css-selector")` | 前述方法不可用时的降级方案 |

## 常见场景定位模式

### 导航栏/菜单项
```js
const nav = tab.playwright.getByRole("navigation");
const menuItem = nav.getByRole("link", { name: "Products" });
// 或
const menuItem = nav.getByText("Products");
```

### 表单输入
```js
const field = tab.playwright.getByLabel("Email");
await field.fill("user@example.com");
```

### 模态框内元素
```js
const dialog = tab.playwright.getByRole("dialog");
const confirmBtn = dialog.getByRole("button", { name: "Confirm" });
```

### 列表/网格中特定项
```js
const list = tab.playwright.getByRole("list");
const item = list.getByRole("listitem").filter({ hasText: "目标项" });
```

### 表格单元格
```js
const cell = tab.playwright.getByRole("cell", { name: "期望值" });
```

## 文本匹配器

```js
// 字符串匹配（部分匹配）
container.getByText("部分文本内容")

// 正则匹配
container.getByText(/精确模式/i)
container.getByText(/包含.*文本/)
```

## 过滤器使用

```js
// 结合 hasText 过滤
const visibleItems = list.getByRole("listitem").filter({ visible: true });

// 结合 has 过滤（包含子定位器）
const cardsWithButton = container.locator(".card").filter({
  has: tab.playwright.getByRole("button")
});

// 组合排除
const items = list.getByRole("listitem").filter({
  hasNotText: "已排除"
});
```

## 等待与状态确认

```js
// 等待元素出现
await locator.waitFor({ state: "visible", timeoutMs: 5000 });

// 等待元素消失
await locator.waitFor({ state: "hidden" });

// 等待页面加载
await tab.playwright.waitForLoadState({ state: "networkidle" });

// 等待特定 URL
await tab.playwright.waitForURL("**/checkout/**");
```

## 快照格式参考

`domSnapshot()` 返回的结构化快照包含：
- `tag`: HTML 标签名
- `text`: 可见文本内容
- `attributes`: 元素属性键值对
- `role`: 计算的 ARIA role
- `accessibleName`: 可访问名称
- `selector`: 建议的选择器候选项
- `bounds`: 元素边界框
- `children`: 子元素递归结构
