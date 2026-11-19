const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.join(__dirname, "..");
const jsRoot = path.join(root, "assets", "js");
const adminSource = fs.readFileSync(path.join(jsRoot, "admin.js"), "utf8");
const apiSource = fs.readFileSync(path.join(jsRoot, "api.js"), "utf8");
const uiSource = fs.readFileSync(path.join(jsRoot, "ui.js"), "utf8");
const adminCss = fs.readFileSync(path.join(root, "assets", "css", "admin.css"), "utf8");
const adminHtml = fs.readFileSync(path.join(root, "admin", "index.html"), "utf8");

test("admin profile uses PDF resume upload instead of a URL field", () => {
  assert.doesNotMatch(adminSource, /name:\s*["']resume_url["']\s*,\s*label:\s*["']Resume URL["']/);
  assert.doesNotMatch(adminSource, /Replace Resume/);
  assert.match(adminSource, /Resume \/ CV/);
  assert.match(adminSource, /Choose PDF File/);
  assert.match(adminSource, /accept="\.pdf,application\/pdf"/);
  assert.match(adminSource, /id="resume-selected-name"/);
  assert.match(adminSource, />Upload Resume</);
  assert.match(adminSource, /Preview Resume/);
  assert.match(adminSource, /Download Resume/);
  assert.match(adminSource, /api\.upload\("\/admin\/profile\/resume"/);
  assert.match(adminSource, /const refreshed = await api\.get\("\/admin\/profile"/);
  assert.match(adminSource, /id="resume-progress"/);
  assert.match(adminSource, /id="resume-upload-status"/);
  assert.match(adminSource, /MAX_RESUME_BYTES\s*=\s*5\s*\*\s*1024\s*\*\s*1024/);
  assert.match(adminSource, /RESUME_MIME_TYPES\s*=\s*new Set\(\["application\/pdf"/);
  assert.equal((adminSource.match(/function\s+resumeCurrentHtml\s*\(/g) || []).length, 1);
});

test("api exposes a progress-aware upload helper", () => {
  assert.match(apiSource, /function\s+upload\(path,\s*formData,\s*options\s*=\s*\{\}\)/);
  assert.match(apiSource, /xhr\.upload\.onprogress/);
  assert.match(apiSource, /onProgress\(Math\.round/);
  assert.match(apiSource, /upload,\s*\n\s*get:/);
});

test("public resume buttons prefer the saved profile path", () => {
  assert.match(uiSource, /profileResumeUrl\s*=\s*config\.cacheBustUrl/);
  assert.match(uiSource, /\$\$\("\[data-resume\]"\)\.forEach/);
  assert.doesNotMatch(uiSource, /\$\("\[data-resume\]"\)\.addEventListener/);
  assert.match(uiSource, /window\.open\(profileResumeUrl,\s*"_blank",\s*"noopener"\)/);
  assert.match(uiSource, /No CV has been published yet/);
});

test("resume upload styles and cache-busted assets are present", () => {
  assert.match(adminCss, /\.resume-progress\s*\{/);
  assert.match(adminCss, /\.resume-upload-status\.error/);
  assert.match(adminCss, /\.resume-upload \.btn \{ width: 100%; \}/);
  assert.match(adminHtml, /admin\.css\?v=20261119e/);
  assert.match(adminHtml, /api\.js\?v=20261119i/);
  assert.match(adminHtml, /ui\.js\?v=20261119i/);
  assert.match(adminHtml, /admin\.js\?v=20261119k/);

  const publicPages = [
    "index.html",
    "about.html",
    "blog.html",
    "contact.html",
    "projects.html",
    "project.html",
    "research.html",
    "certificates.html"
  ];
  publicPages.forEach((page) => {
    const source = fs.readFileSync(path.join(root, page), "utf8");
    assert.match(source, /api\.js\?v=20261119i/, page);
    assert.match(source, /ui\.js\?v=20261119i/, page);
  });
});
