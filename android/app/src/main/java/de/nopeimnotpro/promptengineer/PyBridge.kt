package de.nopeimnotpro.promptengineer

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.net.Uri
import android.webkit.JavascriptInterface
import android.webkit.WebView
import com.chaquo.python.PyObject
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

// JS -> Python: ein Worker-Thread serialisiert alle Aufrufe; Ergebnis per __bridgeResolve zurueck.
class PyBridge(
    private val webView: WebView,
    private val entry: PyObject,
    private val apiProvider: () -> PyObject,          // AB8: Lazy-Init erst im Executor
    private val onThemeChanged: (String) -> Unit,
) {
    private val executor = Executors.newSingleThreadExecutor()

    @JavascriptInterface
    fun call(id: Int, method: String, argsJson: String) {
        executor.execute {
            // AB2: jede Exception -> Fehler-JSON, Promise haengt nie.
            val json = try {
                entry.callAttr("dispatch", apiProvider(), method, argsJson).toString()
            } catch (e: Throwable) {
                INTERNAL_ERROR
            }
            webView.post {
                webView.evaluateJavascript("__bridgeResolve($id, ${JSONObject.quote(json)})", null)
                if (method == "set_theme" && JSONObject(json).optBoolean("ok")) {
                    onThemeChanged(JSONArray(argsJson).getString(0))
                }
            }
        }
    }

    // R6 b: Zwischenablage nativ (WebView 69/API 26: navigator.clipboard + execCommand wirkungslos). Kein Python-Pfad.
    @JavascriptInterface
    fun copy_text(text: String) {
        webView.post {
            webView.context.getSystemService(ClipboardManager::class.java)
                ?.setPrimaryClip(ClipData.newPlainText("Prompt", text))
        }
    }

    // Repo-Link (Einstellungen -> Ueber) im externen Browser; nur REPO_URL, jede andere URL -> false.
    // WebView-Navigation bleibt gesperrt (shouldOverrideUrlLoading unveraendert).
    @JavascriptInterface
    fun open_url(url: String?): Boolean {
        if (url != REPO_URL) return false
        webView.post {
            try {
                webView.context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(REPO_URL)))
            } catch (_: ActivityNotFoundException) {
                // Kein Browser installiert: still ignorieren, App bleibt stabil.
            }
        }
        return true
    }

    companion object {
        const val REPO_URL = "https://github.com/Nope-im-not-pro/PromptEngineer"
        const val INTERNAL_ERROR = """{"ok": false, "error": "Interner Fehler (Bruecke)."}"""
    }
}
