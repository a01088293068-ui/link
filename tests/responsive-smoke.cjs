const { chromium } = require("playwright");
const fs = require("node:fs/promises");
const path = require("node:path");

const base = "https://linkwiki.info";
const routes = [
  { name: "home", path: "/" },
  { name: "directory", path: "/directory" },
  { name: "korean-category", path: "/categories/korean" },
  { name: "address-guide", path: "/guides/address-check" },
  { name: "blog-index", path: "/blog/" },
];
const viewports = [
  { name: "desktop", width: 1440, height: 900, isMobile: false },
  { name: "mobile", width: 390, height: 844, isMobile: true },
];
const failures = [];
const report = [];

(async () => {
  await fs.mkdir("artifacts/responsive", { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of viewports) {
      for (const route of routes) {
        const page = await browser.newPage({
          viewport: { width: viewport.width, height: viewport.height },
          deviceScaleFactor: 1,
          isMobile: viewport.isMobile,
          hasTouch: viewport.isMobile,
        });
        const pageErrors = [];
        page.on("pageerror", error => pageErrors.push(error.message));
        const response = await page.goto(base + route.path, {
          waitUntil: "networkidle",
          timeout: 60000,
        });
        if (!response || response.status() !== 200) {
          failures.push(`${viewport.name} ${route.path}: HTTP ${response?.status() ?? "no response"}`);
        }
        await page.evaluate(() => document.fonts?.ready);
        const state = await page.evaluate(() => {
          const styleLinks = [...document.querySelectorAll('link[rel="stylesheet"]')]
            .filter(link => /assets\/(?:style|blog)\.css/.test(link.href));
          const footer = document.querySelector(".footer");
          const cta = document.querySelector(".footer-cta");
          const directoryAction = document.querySelector(".footer-secondary-action");
          const menu = document.querySelector("#mobile-primary-nav");
          const toggle = document.querySelector(".mobile-menu-toggle");
          return {
            title: document.title,
            width: window.innerWidth,
            documentWidth: document.documentElement.scrollWidth,
            bodyWidth: document.body.scrollWidth,
            stylesheetLinks: styleLinks.map(link => ({
              href: link.getAttribute("href"),
              loaded: Boolean(link.sheet),
            })),
            footer: Boolean(footer),
            cta: Boolean(cta && directoryAction),
            ctaWidth: cta?.getBoundingClientRect().width ?? 0,
            menu: Boolean(menu),
            toggle: Boolean(toggle),
            gridColumns: document.querySelector('#v6-results') ? getComputedStyle(document.querySelector('#v6-results')).gridTemplateColumns.trim().split(/\s+/).length : 0,
          };
        });
        if (state.documentWidth > viewport.width + 1 || state.bodyWidth > viewport.width + 1) {
          failures.push(`${viewport.name} ${route.path}: horizontal overflow (document=${state.documentWidth}, viewport=${viewport.width})`);
        }
        if (!state.footer || !state.cta) failures.push(`${viewport.name} ${route.path}: shared footer/directory action missing`);
        if (route.name === "directory" && viewport.isMobile && state.gridColumns !== 1) failures.push(`mobile /directory: expected one result-card column, got ${state.gridColumns}`);
        if (route.name === "directory" && !viewport.isMobile && state.gridColumns < 2) failures.push(`desktop /directory: expected multi-column result cards, got ${state.gridColumns}`);
        if (!state.stylesheetLinks.length) failures.push(`${viewport.name} ${route.path}: style.css link missing`);
        for (const asset of state.stylesheetLinks) {
          if (!/\?v=[a-f0-9]{12}$/.test(asset.href)) failures.push(`${viewport.name} ${route.path}: stylesheet cache fingerprint missing: ${asset.href}`);
          if (!asset.loaded) failures.push(`${viewport.name} ${route.path}: stylesheet failed to load: ${asset.href}`);
        }
        if (pageErrors.length) failures.push(`${viewport.name} ${route.path}: page errors: ${pageErrors.join(" | ")}`);

        if (viewport.isMobile && state.toggle && state.menu) {
          await page.locator(".mobile-menu-toggle").click();
          const opened = await page.locator(".mobile-menu-toggle").getAttribute("aria-expanded");
          const openClass = await page.locator("#mobile-primary-nav").evaluate(el => el.classList.contains("is-open"));
          if (opened !== "true" || !openClass) failures.push(`mobile ${route.path}: menu did not open`);
          await page.keyboard.press("Escape");
          const closed = await page.locator(".mobile-menu-toggle").getAttribute("aria-expanded");
          if (closed !== "false") failures.push(`mobile ${route.path}: Escape did not close menu`);
        }

        if (route.name === "directory") {
          const search = page.locator("#v6-query");
          if (!(await search.count())) failures.push(`${viewport.name} /directory: search input missing`);
          else {
            await search.fill("정부24");
            await page.waitForTimeout(500);
            const empty = await page.locator("#v6-empty").evaluate(el => !el.hidden);
            if (empty) failures.push(`${viewport.name} /directory: search for 정부24 returned empty state`);
          }
        }

        const file = path.join("artifacts/responsive", `${route.name}-${viewport.name}.png`);
        await page.screenshot({ path: file, fullPage: true, animations: "disabled" });
        report.push({ viewport: viewport.name, route: route.path, status: response?.status(), ...state, pageErrors });
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  await fs.writeFile("artifacts/responsive/report.json", JSON.stringify({ report, failures }, null, 2));
  for (const item of report) {
    console.log(`PASS? ${item.viewport} ${item.route} HTTP ${item.status}; width ${item.documentWidth}/${item.width}; CSS ${item.stylesheetLinks.length}; footer ${item.footer}; CTA ${item.cta}`);
  }
  if (failures.length) {
    console.error("RESPONSIVE QA FAILURES:");
    failures.forEach(item => console.error(" - " + item));
    process.exitCode = 1;
  } else {
    console.log(`PASS: ${report.length} real-browser viewport/page combinations; no overflow, missing CSS fingerprints, footer/directory-action issues, search failures or JS page errors.`);
  }
})();
