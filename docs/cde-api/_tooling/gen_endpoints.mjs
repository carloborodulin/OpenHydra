// Generate endpoints.md from openapi.json (run: node gen_endpoints.mjs).
import { readFileSync, writeFileSync } from 'node:fs';

const spec = JSON.parse(readFileSync(new URL('../openapi.json', import.meta.url)));
const server = spec.servers?.[0]?.url ?? '';
const tagOrder = (spec.tags ?? []).map((t) => t.name);

const byTag = new Map();
for (const [path, ops] of Object.entries(spec.paths)) {
  for (const [method, op] of Object.entries(ops)) {
    const tag = op.tags?.[0] ?? 'Other';
    if (!byTag.has(tag)) byTag.set(tag, []);
    byTag.get(tag).push({ path, method, op });
  }
}

const order = [...tagOrder, ...[...byTag.keys()].filter((t) => !tagOrder.includes(t))];

let out = `# FBI CDE API — endpoint reference\n\n`;
out += `> Generated from \`openapi.json\` by \`_tooling/gen_endpoints.mjs\`. Do not edit by hand.\n\n`;
out += `- **Spec:** OpenAPI ${spec.openapi} — ${spec.info?.title} (${spec.info?.version})\n`;
out += `- **Server:** \`${server}\`\n`;
out += `- **Auth:** append \`?API_KEY=<key>\` to every request\n`;
out += `- **Totals:** ${Object.keys(spec.paths).length} paths across ${byTag.size} groups\n`;

for (const tag of order) {
  const items = byTag.get(tag);
  if (!items) continue;
  out += `\n## ${tag}\n\n`;
  for (const { path, method, op } of items) {
    out += `### \`${method.toUpperCase()} ${path}\`\n\n`;
    const params = op.parameters ?? [];
    if (params.length) {
      out += `| param | in | required | type | values |\n|---|---|---|---|---|\n`;
      for (const pr of params) {
        const sch = pr.schema ?? {};
        const type = sch.type ?? (sch.$ref ? sch.$ref.split('/').pop() : '') ?? '';
        const ev = sch.enum ?? [];
        const values = ev.length
          ? '`' + ev.slice(0, 20).join(', ') + (ev.length > 20 ? ` …(+${ev.length - 20})` : '') + '`'
          : '';
        out += `| \`${pr.name}\` | ${pr.in} | ${pr.required ? 'yes' : 'no'} | ${type} | ${values} |\n`;
      }
      out += '\n';
    } else {
      out += `_No parameters._\n\n`;
    }
    out += `Responses: ${Object.keys(op.responses ?? {}).map((r) => '`' + r + '`').join(', ') || '—'}\n\n`;
  }
}

writeFileSync(new URL('../endpoints.md', import.meta.url), out);
console.log('wrote endpoints.md —', out.length, 'chars');
