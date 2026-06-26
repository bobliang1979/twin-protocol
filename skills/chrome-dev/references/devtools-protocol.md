# Chrome DevTools Protocol 参考

## 通过 agent.browsers API 可用的 CDP 能力

Codex Chrome 插件封装了 Chrome DevTools Protocol 的核心能力，通过以下 API 暴露：

### 控制台日志 (Console)

通过 `tab.dev.logs()` 获取页面 Console API 输出：

```js
// 获取最近 100 条日志
const logs = await tab.dev.logs({ limit: 100 });

// 过滤特定级别
const errors = await tab.dev.logs({ levels: ["error"], limit: 50 });

// 过滤文本
const networkLogs = await tab.dev.logs({ filter: "fetch", limit: 20 });

// 清除控制台
await tab.dev.logsClear();
```

日志条目结构：
```
{
  level: "debug" | "info" | "log" | "warn" | "error",
  message: string,         // 渲染后的日志文本
  timestamp: string,       // ISO 8601
  url: string | undefined  // 来源 URL
}
```

### 页面导航 (Page)

```js
await tab.goto("https://example.com");
await tab.reload();
await tab.back();
await tab.forward();
```

### 截图 (Page.captureScreenshot)

```js
const buffer = await tab.screenshot({ format: "png" });
await nodeRepl.emitImage(buffer); // 在 Codex 中展示
```

### 剪贴板 (Clipboard API)

```js
await tab.clipboard.read();
await tab.clipboard.write({ entries: [...] });
```

## CDP 直接调用（进阶）

通过 Playwright `evaluate()` 可以间接访问部分 CDP 功能：

```js
// 获取 performance 指标
const perfData = await tab.playwright.evaluate(() => {
  return JSON.parse(JSON.stringify(performance.getEntriesByType("navigation")[0]));
});

// 获取资源 timing
const resources = await tab.playwright.evaluate(() => {
  return performance.getEntriesByType("resource").slice(0, 50).map(e => ({
    name: e.name,
    duration: e.duration,
    size: e.transferSize,
  }));
});

// 获取内存信息
const memory = await tab.playwright.evaluate(() => {
  return performance.memory ? {
    usedJSHeapSize: performance.memory.usedJSHeapSize,
    totalJSHeapSize: performance.memory.totalJSHeapSize,
  } : null;
});
```

## 性能分析模式

### 页面加载性能评估

```js
const perf = await tab.playwright.evaluate(() => {
  const nav = performance.getEntriesByType("navigation")[0];
  return {
    dns: nav.domainLookupEnd - nav.domainLookupStart,
    tcp: nav.connectEnd - nav.connectStart,
    ttfb: nav.responseStart - nav.requestStart,
    download: nav.responseEnd - nav.responseStart,
    domInteractive: nav.domInteractive,
    domComplete: nav.domComplete,
    loadComplete: nav.loadEventEnd,
    total: nav.loadEventEnd - nav.startTime,
  };
});
```

### 网络请求监控

```js
// 获取页面中所有资源的加载信息
const resources = await tab.playwright.evaluate(() => {
  return performance.getEntriesByType("resource").map(r => ({
    url: r.name,
    type: r.initiatorType,
    size: r.transferSize || r.encodedBodySize,
    duration: r.duration,
    timing: {
      dns: r.domainLookupEnd - r.domainLookupStart,
      tcp: r.connectEnd - r.connectStart,
      ttfb: r.responseStart - r.requestStart,
    },
  }));
});

// 分析大资源
const largeAssets = resources.filter(r => r.size > 100000);
```
