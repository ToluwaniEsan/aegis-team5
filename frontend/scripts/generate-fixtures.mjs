import { readFile, writeFile } from "node:fs/promises";
import { URL } from "node:url";

const names = [
  "idle",
  "assigned",
  "secured",
  "travelling",
  "degraded",
  "link_lost",
  "route_blocked",
  "queued",
  "fault_shift",
  "estop_held",
  "at_destination",
  "delivered",
];
const entries = await Promise.all(
  names.map(async (name) => {
    const data = JSON.parse(
      await readFile(
        new URL(`../src/mock/fixtures/${name}.json`, import.meta.url),
        "utf8",
      ),
    );
    return `export const ${name}: Snapshot = ${JSON.stringify(data, null, 2)};`;
  }),
);
await writeFile(
  new URL("../src/mock/fixtures.generated.ts", import.meta.url),
  `// Generated from fixtures/*.json by scripts/generate-fixtures.mjs.\nimport type { Snapshot } from '../contracts/ui';\n\n${entries.join("\n\n")}\n`,
);
