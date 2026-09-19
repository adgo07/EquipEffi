# 标准数据包

这里保存随Python wheel发布的标准JSON副本。`src/equipeffi/standard_manifest.json`
只通过显式路径加载这些文件；根目录`standards/`保留为原始/校对工作区，不作为安装包运行时依赖。

永磁同步电机只允许加载`gb30253_2024_pdf_verified_v1.json`，旧版`motor_pmsm.json`
不会复制到本目录。标准文件的来源、校对状态和版本由manifest及人工校对册维护。
