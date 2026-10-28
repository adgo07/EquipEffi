青舟静态资产随本产品离线包分发，不依赖中央仓或其它产品安装目录。

- `qingzhou-logo.png`：Owner指定原图 `青舟节能  --转曲.png`，3060×759 RGBA，原样保留。SHA256 `db557a6374a928b46bd3ab499c0a295ef147e87d79a273d1fde1f2d61f8bc24d`。首页/侧栏均以180 DIP目标宽，从原图按当前DPR缩放，保留透明及比例。
- `icons.svg`：中央既有15图形（24×24、1.7 stroke），SHA256 `ae20eb19ff20f2a41c53ac840f89426afc13fa19f1a3fd81d978b300989d897c`。从中央 `a389ac1de63c4f331f3b04e5e7b7a17ef02ed111/docs/ui/phase2/prototype/assets/icons.svg` 复制，仅复用几何，不继承历史原型规则。使用QIconEngine在目标DPR绘制，支持换色；本轮未改几何或原文件字节。
- 2026-10-28 本轮实施参考中央已验收但未合并候选 `e1486fb20c1dda33b7344ca860ff8f303c2183ee` 的正式资产副本与UI规格。不称为已发布指南，不升级platform-lock。
- `chevron-down.svg` 是同线宽、端点与配色的本地控件箭头扩展。

Qt高DPI实现依据：https://doc.qt.io/qt-6/highdpi.html 。本轮PNG和图标哈希均与改动前一致。
