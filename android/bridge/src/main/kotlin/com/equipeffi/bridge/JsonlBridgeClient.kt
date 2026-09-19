package com.equipeffi.bridge

import org.json.JSONObject
import java.io.BufferedReader
import java.io.BufferedWriter
import java.io.Closeable
import java.io.EOFException
import java.io.IOException
import java.util.concurrent.atomic.AtomicLong

/**
 * EquipEffi JSON Lines v1.0 的极薄客户端。
 *
 * 该类只处理协议传输，不包含设备字段、标准数值或判定公式。Android 外层可以
 * 用任意 InputStream/OutputStream 提供传输（本地进程、Unix socket 或测试桩），
 * 从而不把 Python/Tk/Excel 依赖带入界面模块。
 *
 * 调用约束：同一个实例按顺序发送请求；方法内部同步写入并读取一行响应。若需要
 * 并行请求，应由上层建立多个连接，而不是在一个连接上交错写入。
 */
class JsonlBridgeClient(
    private val input: BufferedReader,
    private val output: BufferedWriter,
    private val closeStreams: Boolean = true,
) : Closeable {
    companion object {
        const val PROTOCOL_VERSION = "1.0"
    }

    private val sequence = AtomicLong(0)
    @Volatile private var closed = false

    /** 发送一条请求并等待对应的单行响应。 */
    @Synchronized
    @Throws(IOException::class, JsonlRemoteException::class)
    fun request(op: String, payload: JSONObject? = null, requestId: String? = null): JSONObject {
        checkOpen()
        val normalizedOp = op.trim()
        require(normalizedOp.isNotEmpty()) { "op不能为空" }
        val id = requestId ?: "android-${sequence.incrementAndGet()}"
        val request = JSONObject()
            .put("protocol_version", PROTOCOL_VERSION)
            .put("request_id", id)
            .put("op", normalizedOp)
        if (payload != null) request.put("payload", payload)

        output.write(request.toString())
        output.newLine()
        output.flush()

        val line = input.readLine() ?: throw EOFException("JSONL服务端已关闭连接")
        val response = try {
            JSONObject(line)
        } catch (error: Exception) {
            throw IOException("服务端返回的JSON无效", error)
        }
        val responseId = response.optString("request_id", "")
        if (responseId != id) {
            throw IOException("响应request_id不匹配：期望$id，实际$responseId")
        }
        if (response.optString("protocol_version", "") != PROTOCOL_VERSION) {
            throw IOException("协议版本不兼容：${response.optString("protocol_version")}")
        }
        if (!response.optBoolean("ok", false)) {
            val error = response.optJSONObject("error")
            throw JsonlRemoteException(
                type = error?.optString("type", "remote_error") ?: "remote_error",
                message = error?.optString("message", "服务端请求失败") ?: "服务端请求失败",
                operation = normalizedOp,
            )
        }
        return response
    }

    fun status(requestId: String? = null): JSONObject = resultObject(request("status", requestId = requestId))

    fun deviceTypes(requestId: String? = null): Any =
        resultValue(request("device_types", requestId = requestId))

    fun schema(deviceType: String, requestId: String? = null): JSONObject =
        resultObject(request("schema", JSONObject().put("device_type", deviceType), requestId))

    fun evaluate(payload: JSONObject, requestId: String? = null): JSONObject =
        resultObject(request("evaluate", payload, requestId))

    fun evaluateBatch(payload: JSONObject, requestId: String? = null): Any =
        resultValue(request("evaluate_batch", payload, requestId))

    /** 向服务端发送quit，然后关闭传输流。 */
    @Synchronized
    fun quit(requestId: String? = null): JSONObject {
        checkOpen()
        return try {
            resultObject(request("quit", requestId = requestId))
        } finally {
            close()
        }
    }

    override fun close() {
        if (closed) return
        closed = true
        if (closeStreams) {
            runCatching { output.close() }
            runCatching { input.close() }
        }
    }

    private fun checkOpen() {
        check(!closed) { "JSONL桥接已关闭" }
    }

    private fun resultObject(response: JSONObject): JSONObject {
        return response.optJSONObject("result")
            ?: throw IOException("响应result不是JSON对象")
    }

    /** result可能是数组（device_types/evaluate_batch），保留原始JSON容器。 */
    private fun resultValue(response: JSONObject): Any =
        response.opt("result")?.takeUnless { it == JSONObject.NULL }
            ?: throw IOException("响应缺少result")
}

class JsonlRemoteException(
    val type: String,
    override val message: String,
    val operation: String,
) : IOException("$type: $message（op=$operation）")
