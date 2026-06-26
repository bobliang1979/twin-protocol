// Chrome DevTools 通用辅助函数
// 在 Node REPL 中加载后使用

/**
 * 初始化 Chrome 浏览器运行时
 * @param {string} chromePluginRoot - Chrome 插件根目录路径
 */
export async function initChromeRuntime(chromePluginRoot) {
  const { setupBrowserRuntime } = await import(`${chromePluginRoot}/scripts/browser-client.mjs`);
  await setupBrowserRuntime({ globals: globalThis });
  globalThis.browser = await agent.browsers.get("extension");
  return browser;
}

/**
 * 读取全部文档
 */
export async function readBrowserDocs() {
  return await browser.documentation();
}

/**
 * 获取或创建标签页
 * @param {"selected"|"new"|string} mode - selected: 当前选中, new: 新建, string: 按标题匹配
 * @param {string} url - 导航 URL
 */
export async function getTab(mode = "selected", url = null) {
  let tab;
  if (mode === "selected") {
    tab = await browser.tabs.selected();
  } else if (mode === "new") {
    tab = await browser.tabs.new();
  } else {
    const openTabs = await browser.user.openTabs();
    const match = openTabs.find(t => t.title.includes(mode));
    if (!match) throw new Error(`未找到标题包含 "${mode}" 的标签页`);
    tab = await browser.user.claimTab(match);
  }
  if (url) await tab.goto(url);
  return tab;
}

/**
 * 安全执行 Playwright 定位并点击
 * @param {*} tab - tab 对象
 * @param {string} role - ARIA role
 * @param {string} name - accessible name
 * @param {object} options - 额外选项
 */
export async function safeClick(tab, role, name, options = {}) {
  const locator = tab.playwright.getByRole(role, { name });
  const count = await locator.count();
  if (count === 0) throw new Error(`未找到 role="${role}" name="${name}" 的元素`);
  if (count > 1) throw new Error(`找到 ${count} 个 role="${role}" name="${name}" 的元素，不唯一`);
  await locator.click(options);
}

/**
 * 批量提取页面结构化数据
 * @param {*} tab - tab 对象
 * @param {Function} extractFn - 在页面上下文中执行的数据提取函数
 */
export async function extractData(tab, extractFn) {
  return await tab.playwright.evaluate(extractFn);
}

/**
 * 获取页面性能指标
 */
export async function getPageMetrics(tab) {
  return await tab.playwright.evaluate(() => {
    const nav = performance.getEntriesByType("navigation")[0];
    if (!nav) return null;
    return {
      ttfb: nav.responseStart - nav.requestStart,
      domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
      domComplete: nav.domComplete - nav.startTime,
      loadComplete: nav.loadEventEnd - nav.startTime,
    };
  });
}

/**
 * 诊断模式：一次性获取日志 + 快照 + 截图
 */
export async function diagnosePage(tab) {
  const logs = await tab.dev.logs({ limit: 50 });
  const snapshot = await tab.playwright.domSnapshot();
  const screenshotBuffer = await tab.screenshot({ format: "png" });
  return { logs, snapshot, screenshotBuffer };
}
