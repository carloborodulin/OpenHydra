// Set the theme before first paint so returning dark-mode users do not see a
// flash of the light default. Mirrors lib/theme.ts (key "oh-theme"). A file,
// not an inline script, so the Content-Security-Policy can say script-src 'self'.
try {
  var t = localStorage.getItem("oh-theme");
  document.documentElement.dataset.theme = t === "dark" ? "dark" : "light";
} catch (e) {
  document.documentElement.dataset.theme = "light";
}
