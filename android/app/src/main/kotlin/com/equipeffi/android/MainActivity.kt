package com.equipeffi.android

import android.app.Activity
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import com.equipeffi.bridge.JsonlBridgeClient
import org.json.JSONArray
import org.json.JSONObject
import java.net.Socket
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Android最小演示界面。
 *
 * 业务判定仍在EquipEffi JSONL服务端执行；本Activity只负责选择公共设备类型、
 * 传递用户输入的JSON参数并展示返回结果。正式产品可替换为Compose或其他UI，
 * 不需要改动bridge模块和判定内核。
 */
class MainActivity : Activity() {
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private var socket: Socket? = null
    private var client: JsonlBridgeClient? = null

    private lateinit var hostInput: EditText
    private lateinit var portInput: EditText
    private lateinit var deviceSpinner: Spinner
    private lateinit var valuesInput: EditText
    private lateinit var outputText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }

        hostInput = edit("服务地址（模拟器可填10.0.2.2）", "10.0.2.2")
        portInput = edit("端口", "8765")
        root.addView(hostInput)
        root.addView(portInput)

        val connect = Button(this).apply { text = "连接并读取设备类型" }
        root.addView(connect)

        deviceSpinner = Spinner(this)
        deviceSpinner.adapter = adapter(listOf("motor"))
        root.addView(deviceSpinner)

        valuesInput = edit(
            """参数 JSON，例如 {"category":"三相异步电动机","rated_voltage":0.4,"rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}""",
            """{"category":"三相异步电动机","rated_voltage":0.4,"rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}""",
        )
        valuesInput.minLines = 5
        valuesInput.gravity = android.view.Gravity.TOP
        root.addView(valuesInput, LinearLayout.LayoutParams(-1, 0).apply { weight = 1f })

        val evaluate = Button(this).apply { text = "提交判定" }
        root.addView(evaluate)
        outputText = TextView(this).apply { text = "尚未连接服务" }
        root.addView(outputText)
        setContentView(root)

        connect.setOnClickListener { connectAsync() }
        evaluate.setOnClickListener { evaluateAsync() }
    }

    private fun edit(hintText: String, value: String): EditText =
        EditText(this).apply {
            hint = hintText
            setText(value)
            setSingleLine(false)
        }

    private fun adapter(values: List<String>): ArrayAdapter<String> =
        ArrayAdapter(this, android.R.layout.simple_spinner_item, values).also {
            it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        }

    private fun connectAsync() {
        val host = hostInput.text.toString().trim()
        val port = portInput.text.toString().trim().toIntOrNull()
        if (host.isEmpty() || port == null || port !in 1..65535) {
            outputText.text = "服务地址或端口无效"
            return
        }
        outputText.text = "正在连接..."
        executor.execute {
            try {
                val newSocket = Socket(host, port)
                val newClient = JsonlBridgeClient(
                    newSocket.getInputStream().bufferedReader(),
                    newSocket.getOutputStream().bufferedWriter(),
                )
                val status = newClient.status()
                val types = typeNames(newClient.deviceTypes())
                socket?.close()
                socket = newSocket
                client?.close()
                client = newClient
                runOnUiThread {
                    if (types.isNotEmpty()) deviceSpinner.adapter = adapter(types)
                    outputText.text = status.toString(2)
                }
            } catch (error: Exception) {
                runOnUiThread { outputText.text = "连接失败：" + (error.message ?: error.javaClass.simpleName) }
            }
        }
    }

    private fun evaluateAsync() {
        val activeClient = client
        if (activeClient == null) {
            outputText.text = "请先连接服务"
            return
        }
        val deviceType = deviceSpinner.selectedItem?.toString().orEmpty()
        val values = try {
            JSONObject(valuesInput.text.toString())
        } catch (error: Exception) {
            outputText.text = "参数 JSON 无效：" + (error.message ?: "解析失败")
            return
        }
        outputText.text = "正在判定..."
        executor.execute {
            try {
                val payload = JSONObject()
                    .put("device_type", deviceType)
                    .put("values", values)
                val result = activeClient.evaluate(payload)
                runOnUiThread { outputText.text = result.toString(2) }
            } catch (error: Exception) {
                runOnUiThread { outputText.text = "判定失败：" + (error.message ?: error.javaClass.simpleName) }
            }
        }
    }

    private fun typeNames(value: Any): List<String> {
        if (value !is JSONArray) return emptyList()
        val result = mutableListOf<String>()
        for (index in 0 until value.length()) {
            val item = value.opt(index)
            when (item) {
                is JSONObject -> result += item.optString("code").ifEmpty { item.optString("name") }
                is String -> result += item
            }
        }
        return result.filter { it.isNotEmpty() }
    }

    override fun onDestroy() {
        executor.execute { runCatching { client?.quit() } }
        executor.shutdown()
        runCatching { socket?.close() }
        super.onDestroy()
    }
}
