<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
:root {
  --bg: #0f172a;
  --fg: #e2e8f0;
  --muted: #94a3b8;
  --accent: #22c55e;
}
html, body, #app { height: 100%; margin: 0; }
body { background: var(--bg); color: var(--fg); font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji"; }
button { cursor: pointer; }
input, button, select { background: #0b1220; color: var(--fg); border: 1px solid #1f2937; border-radius: 6px; padding: 8px 10px; }
.container { max-width: 1200px; margin: 0 auto; padding: 16px; }
.toolbar { display: flex; gap: 8px; align-items: center; padding: 8px 0; }
.card { background: #0b1220; border: 1px solid #1f2937; border-radius: 8px; padding: 16px; }
.link { color: var(--accent); text-decoration: none; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: 8px; border-bottom: 1px solid #1f2937; }
.table th { text-align: left; color: var(--muted); font-weight: 500; }
.table tr:hover { background: #0e1626; }
.badge { background: #065f46; color: #d1fae5; border-radius: 999px; padding: 2px 8px; font-size: 12px; }
</style>

