青舟静态资产随本产品离线包分发，不依赖中央仓或其它产品安装目录。

- `qingzhou-logo.png`：Owner指定原图 `青舟节能  --转曲.png`，3060×759 RGBA，原样保留。SHA256 `db557a6374a928b46bd3ab499c0a295ef147e87d79a273d1fde1f2d61f8bc24d`。首页/侧栏均以180 DIP目标宽，从原图按当前DPR缩放，保留透明及比例。
- `icons.svg`：中央既有15图形（24×24、1.7 stroke），Git blob/LF原始字节SHA256 `f78b7a6249ffe88eedcdf52c71c24299e306e73b067c191b5fb02ea901764712`，与中央 `829853a943c421e0b9864d84f3d94970d2ddf688/docs/ui/assets/icons.svg` 正式副本一致。历史复制来源为 `a389ac1de63c4f331f3b04e5e7b7a17ef02ed111/docs/ui/phase2/prototype/assets/icons.svg`，仅复用几何，不继承历史原型规则。使用QIconEngine在目标DPR绘制，支持换色；本轮未改几何或原文件字节。
- 2026-11-10 局部收口读取中央 `origin/main@829853a943c421e0b9864d84f3d94970d2ddf688` 的当前UI规格、指南v0.2和 `docs/ui/assets/README.md` 正式资产说明；沿用原图及15图标几何，未修改资产字节或platform-lock。
- `chevron-down.svg` 是同线宽、端点与配色的本地控件箭头扩展。

Qt高DPI实现依据：https://doc.qt.io/qt-6/highdpi.html 。本轮PNG和图标哈希均与改动前一致。
