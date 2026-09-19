# EquipEffi Android 工程骨架

本目录只放移动端与EquipEffi判定服务之间的协议桥接，不放设备公式、标准表或Excel逻辑。界面层可以改用Jetpack Compose、传统View或其他移动框架，而不改变判定内核。

## 当前范围

现在已提供一个可导入 Android Studio 的最小 Gradle 多模块工程：`bridge` 为协议库，`app` 为不依赖第三方 UI 框架的演示界面。演示界面可以填写服务地址和端口、读取15类公共设备类型、选择设备类型、输入参数 JSON 并显示判定结果。

`bridge/src/main/kotlin/com/equipeffi/bridge/JsonlBridgeClient.kt`实现JSON Lines v1.0的顺序请求客户端：

- 每条请求自动带唯一`request_id`，并核对响应ID和协议版本；
- 每次写入一行并立即刷新，读取一行后再返回，适合进程或socket桥接；
- 远端错误转换为`JsonlRemoteException`，不把“无法判定”误报为传输错误；
- `quit()`主动关闭服务；EOF、无效JSON、版本不兼容和ID错位均作为连接错误；
- `deviceTypes`、`evaluateBatch`保留数组结果，不在客户端复制业务结构；
- 不携带Tk、Excel、Python或第三方业务依赖，`org.json`使用Android平台自带实现。

## 传输接入

`JsonlBridgeClient`接受`BufferedReader`和`BufferedWriter`，上层可以注入：

1. 宿主机启动的`python -m equipeffi --jsonl`子进程；
2. 本地服务/Unix socket的行缓冲适配器；
3. 测试用内存流。

移动端不应自行实现设备公式或读取标准JSON。启动后先调用`status`，根据返回的15类设备、标准包状态和淘汰目录能力决定界面；当前PMSM标准包为`normalized`时，应原样展示服务返回的“无法判定”。

## 暂未声称的内容

本机没有Android SDK/Gradle环境，因此尚未构建或签名 APK，也未做真机验收。取得目标SDK后，应补充进程生命周期、读取超时、重启策略、权限控制和正式UI，并用`tools/smoke_jsonl.py`的协议样例做端到端回归。演示应用通过网络连接 JSONL 服务端；它不会在手机端复制设备公式、标准 JSON 或 Excel 逻辑。
