---
name: chrome-dev
description: >
  Chrome DevTools 与浏览器自动化技能。使用 Chrome DevTools Protocol、Playwright、DOM 操作等技术进行页面分析、性能诊断、网络追踪、截图抓取、元素定位和交互自动化。
  当任务涉及以下场景时使用：(1) 通过 Chrome DevTools 分析页面性能/网络/控制台日志 (2) 自动化浏览器交互 (3) DOM 深度检查与元素定位 (4) 页面截图与资产管理。
  依赖 Codex Chrome 插件的 agent.browsers.* API，于 Node REPL 环境中运行 JavaScript 代码控制 Chrome。
---

# Chrome Dev 技术技能

## 核心架构概览

本技能构建在 Codex Chrome 插件的 `agent.browsers` API 之上，通过 Node REPL (`mcp__node_repl__js`) 执行 JavaScript 代码控制 Chrome 浏览器。

### 能力分层

```
agent.browsers.get("extension")
  ├── browser.user          → 用户浏览器上下文（打开的标签页、历史记录）
  ├── browser.tabs          → 标签页管理（新建、列出、获取、关闭）
  │   └── tab.playwright    → Playwright 自动化（定位器、快照、求值）
  │   └── tab.cua           → 坐标级交互（点击、拖拽、滚动、键盘）
  │   └── tab.dom_cua       → DOM 节点级交互（可见 DOM 快照、点击）
  │   └── tab.dev           → DevTools 诊断（控制台日志、网络请求）
  │   └── tab.capabilities  → 额外能力（pageAssets 等）
  │   └── tab.screenshot()  → 截图
  │   └── tab.goto()        → 导航
  │   └── tab.clipboard     → 剪贴板
  └── browser.capabilities  → 浏览器级能力发现
```

## 快速启动

### 第一步：初始化 Chrome 运行时

```js
// 一次性初始化（每个 node_repl 会话只需一次）
const { setupBrowserRuntime } = await import("<chrome-plugin-root>/scripts/browser-client.mjs");
await setupBrowserRuntime({ globals: globalThis });
globalThis.browser = await agent.browsers.get("extension");
nodeRepl.write(await browser.documentation());
```

### 第二步：获取或创建标签页

```js
// 获取当前选中的标签页
let tab = await browser.tabs.selected();

// 或者新建一个标签页
tab = await browser.tabs.new();

// 或者接管用户已打开的标签页
const openTabs = await browser.user.openTabs();
const targetTab = openTabs.find(t => t.title.includes("目标页面标题"));
tab = await browser.user.claimTab(targetTab);
```

### 第三步：导航与交互

```js
await tab.goto("https://example.com");
await tab.playwright.domSnapshot(); // 获取 DOM 快照进行元素定位
```

## 核心操作指南

### 1. 标签页管理 (Tabs API)

```js
// 列出所有标签页
const tabs = await browser.tabs.list();

// 按 ID 获取标签页
const tab = await browser.tabs.get("tab-id");

// 获取用户打开的标签页（不接管）
const userTabs = await browser.user.openTabs();
// userTabs 包含: title, url, tabGroup, lastOpened, windowId

// 获取浏览历史
const history = await browser.user.history({ limit: 10 });
// history 包含: title, url, dateVisited

// 关闭/清理标签页
await tab.close();
await browser.tabs.finalize({ keep: [{ tab, status: "deliverable" }] });
```

### 2. Playwright 自动化 (Playwright API)

Playwright 是核心交互引擎。关键原则：**始终先获取 DOM 快照，再从快照构建定位器。**

#### 定位器优先级（按推荐顺序）

1. `getByRole(role, { name: "精确可访问名称" })` — 名称必须为普通字符串，不能用正则
2. `getByLabel("label-text")` — 表单标签绑定
3. `getByTestId("test-id")` — 稳定 test-id 属性
4. `getByPlaceholder("placeholder-text")` — 输入框占位符
5. `getByText("可见文本")` — 按文本内容定位
6. 带作用域的 CSS 选择器 `locator("css-selector")`

#### DOM 快照纪律

```js
// 获取快照（导航后必须获取新快照）
const snapshot = await tab.playwright.domSnapshot();
// 从快照中定位元素，不要猜测选择器

// 快照提供: tag, text, attributes, role, accessibleName 等
// 用于构建稳定的定位器
```

#### 交互操作模式

```js
// 标准操作流程：快照 → 定位器 → count() 确认唯一 → 操作 → 验证
const snapshot = await tab.playwright.domSnapshot();
const locator = tab.playwright.getByRole("button", { name: "Submit" });
const count = await locator.count(); // 确认唯一
if (count === 1) {
  await locator.click();
}
```

#### 支持的操作

- `locator.click(options?)` — 点击
- `locator.fill(value)` — 填写输入框
- `locator.check() / locator.uncheck()` — 复选框
- `locator.setChecked(true/false)` — 设置选中状态
- `locator.press("Enter")` — 按键
- `locator.selectText()` — 选中文本
- `locator.textContent()` — 获取文本内容
- `locator.getAttribute(name)` — 获取属性
- `locator.count()` — 匹配元素数量
- `locator.isVisible() / .isHidden()` — 可见性检查
- `locator.waitFor({ state })` — 等待状态

#### 作用域限定

```js
// 先找到容器，再在容器内定位
const container = tab.playwright.getByRole("list", { name: "Products" });
const productLink = container.getByRole("link", { name: "Product A" });
const prodCount = await productLink.count(); // 确认唯一
if (prodCount === 1) await productLink.click();
```

#### Read-only evaluate（批量数据提取）

```js
// 批量提取结构化数据，一次性读取，不要逐元素轮询
const data = await tab.playwright.evaluate(() => {
  return Array.from(document.querySelectorAll(".product-card")).slice(0, 20).map(card => ({
    title: card.querySelector(".title")?.textContent?.trim(),
    price: card.querySelector(".price")?.textContent?.trim(),
  }));
});
```

### 3. 坐标级交互 (CUA API)

适用于需要精确坐标的场景或 Playwright 定位器无法处理的元素：

```js
// 点击坐标
await tab.cua.click({ x: 100, y: 200 });

// 双击
await tab.cua.double_click({ x: 100, y: 200 });

// 拖拽
await tab.cua.drag({ path: [{ x: 100, y: 100 }, { x: 200, y: 200 }] });

// 滚动
await tab.cua.scroll({ x: 0, y: 500 });

// 键盘按键
await tab.cua.keypress({ keys: ["Enter"] });

// 输入文本
await tab.cua.type({ text: "Hello World" });

// 鼠标移动
await tab.cua.move({ x: 100, y: 200 });
```

### 4. DOM 节点级交互 (DOM CUA API)

获取可见 DOM 并通过节点 ID 交互：

```js
// 获取可见 DOM（返回带 node_id 的交互元素树）
const dom = await tab.dom_cua.get_visible_dom();

// 基于 DOM 节点 ID 点击
await tab.dom_cua.click({ node_id: "123" });

// 滚动页面或特定节点
await tab.dom_cua.scroll({ node_id: "456", x: 0, y: 300 });

// 键盘与输入
await tab.dom_cua.keypress({ keys: ["Tab"] });
await tab.dom_cua.type({ text: "Hello" });
```

### 5. DevTools 诊断 (Dev API)

```js
// 获取控制台日志
const logs = await tab.dev.logs({ limit: 100 });
// 返回: [{ level, message, timestamp, url }]
// level: "debug" | "info" | "log" | "warn" | "error"

// 按级别过滤
const errors = await tab.dev.logs({ levels: ["error"], limit: 50 });

// 按文本过滤
const apiLogs = await tab.dev.logs({ filter: "API", limit: 20 });

// 清除日志
await tab.dev.logsClear();
```

### 6. 页面资产管理 (Page Assets)

```js
// 获取 pageAssets 能力
const assets = await tab.capabilities.get("pageAssets");

// 盘存页面资源
const inventory = await assets.list();
// 返回: id, assets[], inlineSvgs[], summary
// assets[].kind: "script" | "font" | "image" | "stylesheet" | "video" | "other"

// 下载资源到本地
const bundle = await assets.bundle({
  inventoryId: inventory.id,
  kinds: ["image", "font"],
});
// 返回: directoryPath, manifestPath, assets[], summary
// 本地文件保存在 directoryPath 中
```

### 7. 截图与剪贴板

```js
// 截图（返回 Uint8Array）
const screenshotBuffer = await tab.screenshot({ format: "png" });
// 可通过 nodeRepl.emitImage(screenshotBuffer) 在 Codex 中展示

// 剪贴板读取
const clipboard = await tab.clipboard.read();
// 返回: { entries: [{ mimeType, text?, base64? }], presentationStyle? }

// 剪贴板写入
await tab.clipboard.write({
  entries: [{ mimeType: "text/plain", text: "Hello" }]
});
```

### 8. 浏览器能力发现

```js
// 列出浏览器级能力
const browserCaps = await browser.capabilities.list();
// 查看能力文档
if (browserCaps.length > 0) {
  const capDoc = await (await browser.capabilities.get(browserCaps[0].id)).documentation();
}

// 列出标签页级能力
const tabCaps = await tab.capabilities.list();
const tabCapDoc = await (await tab.capabilities.get(tabCaps[0].id)).documentation();
```

## 错误处理与恢复

### 定位器失败

```
严格模式违规 → 立即获取新快照 → 从快照重建定位器 → 不要重试同一定位器
超时 → 目标可能缺失/隐藏 → 获取新快照确认 → 使用更稳定属性
选择器解析错误 → 语法不支持 → 改用定位器 API
```

### 恢复工作流

```js
// 定位器失败后的标准恢复流程
const freshSnapshot = await tab.playwright.domSnapshot();
// 从新快照中寻找更稳定的选择器
// 优先使用 data-* 属性、href 值、role + name 组合
// 必要时降级到 scoped DOM 点击路径
```

### 标签页状态丢失

```js
// 当前标签页不可用时，重新获取
tab = await browser.tabs.selected();
// 或通过 ID 重新获取
tab = await browser.tabs.get(tabId);
```

## 最佳实践

### DOM 快照纪律
- 导航后必须获取新快照
- 重试失败定位器前必须获取新快照
- 从最新快照构建定位器，不猜测选择器
- 用 `count()` 确认定位器唯一性后执行操作

### 性能优化
- 优先 Playwright 定位器而非坐标操作
- 批量数据用 `evaluate()` 一次性提取
- 避免在循环中逐元素读取属性
- 复用 `tab` 绑定，不在每次调用时重新获取

### 安全准则
- 不检查浏览器 cookies、localStorage、密码
- 提交表单/发送消息前需用户确认
- 不绕过 paywall 或安全拦截页面
- 处理 CAPTCHA 前询问用户

## 参考资源

### scripts/
- `chrome-devtools-helper.js` — Chrome DevTools 通用辅助函数

### references/
- `playwright-patterns.md` — Playwright 高级定位模式参考
- `devtools-protocol.md` — Chrome DevTools Protocol 参考

### assets/
- 预留存放 Chrome 相关模板和图标文件
