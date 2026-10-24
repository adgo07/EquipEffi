# 标准历史材料归档（2026-10-24）

当前标准从[标准总入口](../../standards/README.md)进入。本目录仅保存来源、核验、历史解释与交接，不维护第二套当前状态。历史文字中的待批准、已完成等描述只代表当时；当前解释见主映射，问题状态见[根台账](../../../STANDARD_ISSUES_REGISTER.md)。

每个标准保留原来的资料相对结构；原tmp/_tmp/_work内容归入work_records，其中独有的提取、原页图像和脚本作为核验材料保存。完全相同的非Markdown文件按SHA去重，旧路径对应关系见[文件清单](FILE_MANIFEST.json)。归档Markdown仅调整链接，不改事实文字；before中的原映射保留修改前字节及旧路径，供回溯。脚本是历史方法证据，内含旧路径，复跑前按清单恢复工作布局，不能当现行自动任务。

|标准|当前映射|历史资料|
|---|---|---|
|gb18613_2020|[映射](../../standards/gb18613_2020/STANDARD_MAPPING.md)|[历史来源及目录](gb18613_2020/README.md)|
|gb19153_2019|[映射](../../standards/gb19153_2019/STANDARD_MAPPING.md)|[历史来源及目录](gb19153_2019/README.md)|
|gb19576_2019|[映射](../../standards/gb19576_2019/STANDARD_MAPPING.md)|[历史来源及目录](gb19576_2019/README.md)|
|gb19577_2024|[映射](../../standards/gb19577_2024/STANDARD_MAPPING.md)|[历史来源及目录](gb19577_2024/README.md)|
|gb19761_2020|[映射](../../standards/gb19761_2020/STANDARD_MAPPING.md)|[历史来源及目录](gb19761_2020/README.md)|
|gb21454_2021|[映射](../../standards/gb21454_2021/STANDARD_MAPPING.md)|[历史来源及目录](gb21454_2021/README.md)|
|gb24500_2020|[映射](../../standards/gb24500_2020/STANDARD_MAPPING.md)|[历史来源及目录](gb24500_2020/README.md)|
|gb28381_2012|[映射](../../standards/gb28381_2012/STANDARD_MAPPING.md)|[历史来源及目录](gb28381_2012/README.md)|
|gb28381_2026|[映射](../../standards/gb28381_2026/STANDARD_MAPPING.md)|[历史来源及目录](gb28381_2026/README.md)|
|gb29541_2013|[映射](../../standards/gb29541_2013/STANDARD_MAPPING.md)|[历史来源及目录](gb29541_2013/README.md)|
|gb30253_2024|[映射](../../standards/gb30253_2024/STANDARD_MAPPING.md)|[历史来源及目录](gb30253_2024/README.md)|
|gb30254_2024|[映射](../../standards/gb30254_2024/STANDARD_MAPPING.md)|[历史来源及目录](gb30254_2024/README.md)|
|gb32030_2022|[映射](../../standards/gb32030_2022/STANDARD_MAPPING.md)|[历史来源及目录](gb32030_2022/README.md)|
|gb37479_2019|[映射](../../standards/gb37479_2019/STANDARD_MAPPING.md)|[历史来源及目录](gb37479_2019/README.md)|
|gbt36561_2018|[映射](../../standards/gbt36561_2018/STANDARD_MAPPING.md)|[历史来源及目录](gbt36561_2018/README.md)|

## 本次范围与验证

本仓HEAD：`d9f711068bde583138a7f3dded6f64dcaa339761`，origin为adgo07/EquipEffi，工作分支codex/six-standard-mappings。fetch成功，默认master；本地master落后origin/master 123提交，本次未切分支。locked central SHA：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`。本任务不涉及中央公共Contract，不需要修改中央Contract。适用要求：保留标准事实和Owner解释、根台账唯一状态、冻结资产不动；无Contract冲突。

15个未冻结标准收口：GB 19576、GB 29541、GB 37479使用单文件，其余12项保留工作簿。相关Standard Issue沿用原编号和决定，含2026-10-23已答25项；不作新解释，不关闭未答问题。GB 32030引用资料真实性待核验限制保留。未改软件、原文、Canonical、Approved Golden、scope/support或验收状态。

三项小型标准共150个等级限值，GB 19576已有39值逐行比对，另两项迁入111值；记录见[TABLE_TRANSFER_CHECKS](TABLE_TRANSFER_CHECKS.json)。本次验证迁移一致性，不冒称重新完成原PDF全量验收。冻结目录哈希见[保护清单](PROTECTED_HASHES.json)。最终核验见[VALIDATION](VALIDATION.json)。

清理结果：15个标准目录由877个文件收为27个当前文件（3份单文件映射，12组映射＋工作簿）；850个原位置文件已在校验归档后移除，其中6个完全相同副本去重；10个node_modules目录联接已解除，外部依赖目录未删除。独有的原页图像、源文提取及构建/核验脚本作为历史证据保留。

全仓`git diff --check`另发现原有`.gitignore`末尾空行；本次修改的跟踪文档定向检查通过，未清理无关改动。本次无生产代码测试或新原PDF逐格验收。
