// 从冻结V2.1导入并只补指定P列；生成新的V2.2修订候选，不覆盖旧版。
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const spec = JSON.parse(await fs.readFile(path.join(here, 'V2.2_辅助阻抗补录坐标.json'), 'utf8'));
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(spec.old_xlsx));
for (const patch of spec.patches) {
  const cell = wb.worksheets.getItem(patch.sheet).getRange(patch.cell);
  const actual = cell.values[0][0] ?? null;
  if (actual !== patch.old) throw new Error(`${patch.sheet}!${patch.cell}: input changed`);
  cell.values = [[patch.new]];
}
wb.recalculate();
for (const target of ['表03!P5', '表04!P7', '表16!P4', '表25!P10', '表26!P11']) {
  const [sheet, address] = target.split('!');
  const result = wb.worksheets.getItem(sheet).getRange(address).values[0][0];
  if (!result) throw new Error(`Missing ${target}`);
}
const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(spec.new_xlsx);
const preview = await wb.render({sheetName:'表03',range:'A1:Q7',scale:1,format:'png'});
await fs.writeFile(path.join(here, 'V2.2_表03_预览.png'), new Uint8Array(await preview.arrayBuffer()));
console.log(JSON.stringify({patches:spec.patches.length,output:spec.new_xlsx}));
