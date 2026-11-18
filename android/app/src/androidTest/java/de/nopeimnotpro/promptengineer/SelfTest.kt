package de.nopeimnotpro.promptengineer

import android.content.ClipboardManager
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.util.Log
import androidx.appcompat.app.AppCompatDelegate
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.webkit.WebViewCompat
import com.chaquo.python.Python
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

// Ersatz fuer main.py --selftest (Konzept 10). Frischer App-Zustand je Test: clearPackageData (Orchestrator).
@RunWith(AndroidJUnit4::class)
class SelfTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test
    fun readyGetSettingsOkWithoutEnv() {
        launch { scenario ->
            awaitReady(scenario)
            assertTrue(bridgeCall(scenario, "get_settings").getBoolean("ok"))
            assertFalse(".env ohne Speichern angelegt", File(context.filesDir, ".env").exists())
            var chrome: Any? = null
            scenario.onActivity { chrome = it.webView.webChromeClient }
            assertNotNull("WebChromeClient fehlt (confirm)", chrome)
        }
    }

    @Test
    fun unknownMethodRejected() {
        launch { scenario ->
            awaitReady(scenario)
            val res = bridgeCall(scenario, "_resolve")
            assertFalse(res.getBoolean("ok"))
            assertEquals("Unbekannte Methode.", res.getString("error"))
        }
    }

    @Test
    fun filesDirWritable() {
        val tmp = File.createTempFile("selftest_", ".tmp", context.filesDir)
        tmp.writeText("x")
        assertTrue(tmp.delete())
        assertFalse(tmp.exists())
    }

    @Test
    fun sqliteSelect1() {
        val con = Python.getInstance().getModule("sqlite3").callAttr("connect", ":memory:")
        try {
            val row = con.callAttr("execute", "select 1").callAttr("fetchone")
            assertEquals(1, row.asList()[0].toInt())
        } finally {
            con.callAttr("close")
        }
    }

    @Test
    fun nonAssetRequestForbidden() {
        launch { scenario ->
            awaitReady(scenario)
            js(scenario, "window.__st = null; fetch('/forbidden').then(r => { window.__st = r.status; }, () => { window.__st = -1; });")
            assertEquals("403", poll(scenario, "window.__st", 10_000))
        }
    }

    @Test
    fun foreignNavigationBlocked() {
        launch { scenario ->
            awaitReady(scenario)
            js(scenario, "location.href = 'https://example.com/';")
            SystemClock.sleep(2_000)
            var url: String? = null
            scenario.onActivity { url = it.webView.url }
            assertEquals(MainActivity.START_URL, url)
        }
    }

    // Konzept 4.4: echter Tap (Nutzer-Geste fuer navigator.clipboard), danach ClipboardManager lesen.
    @Test
    fun copyButtonWritesClipboard() {
        launch { scenario ->
            awaitReady(scenario)
            js(scenario, "showTab('optimize'); showStep('result');" +
                " document.getElementById('result').value = '$COPY_TEXT';" +
                " document.getElementById('btn-copy').scrollIntoView({block: 'center'});")
            SystemClock.sleep(300)
            val rect = JSONArray(js(scenario,
                "(() => { const r = document.getElementById('btn-copy').getBoundingClientRect();" +
                    " return [r.left + r.width / 2, r.top + r.height / 2, window.devicePixelRatio]; })()"))
            val loc = IntArray(2)
            scenario.onActivity { it.webView.getLocationOnScreen(loc) }
            val dpr = rect.getDouble(2)
            val x = loc[0] + (rect.getDouble(0) * dpr).toInt()
            val y = loc[1] + (rect.getDouble(1) * dpr).toInt()
            shell("input tap $x $y")

            // (1) Status zuerst: flash() loescht "Kopiert" nach 2 s; allein kein Beweis.
            val tapAt = SystemClock.uptimeMillis()
            var status: String
            do {
                status = js(scenario, "document.getElementById('copy-status').textContent")
                if (status == "\"Kopiert\"") break
                SystemClock.sleep(100)
            } while (SystemClock.uptimeMillis() - tapAt < 1_500)
            assertEquals("\"Kopiert\"", status)

            // (2) Danach Zwischenablage im Vordergrund (Main-Thread) lesen.
            var clip: String? = null
            val deadline = SystemClock.uptimeMillis() + 5_000
            while (SystemClock.uptimeMillis() < deadline) {
                scenario.onActivity {
                    clip = it.getSystemService(ClipboardManager::class.java)
                        ?.primaryClip?.getItemAt(0)?.text?.toString()
                }
                if (clip == COPY_TEXT) break
                SystemClock.sleep(100)
            }
            assertEquals(COPY_TEXT, clip)
        }
    }

    // T6: Nutzerpfad (Select -> app.js -> set_theme -> onThemeChanged) setzt natives Theme und Seitenfarbe.
    @Test
    fun themeDarkLightNative() {
        launch { scenario ->
            awaitReady(scenario)
            selectTheme(scenario, "dark")
            assertEquals(AppCompatDelegate.MODE_NIGHT_YES, awaitNightMode(AppCompatDelegate.MODE_NIGHT_YES))
            assertEquals(BG_DARK, awaitBg(scenario, BG_DARK))
            selectTheme(scenario, "light")
            assertEquals(AppCompatDelegate.MODE_NIGHT_NO, awaitNightMode(AppCompatDelegate.MODE_NIGHT_NO))
            assertEquals(BG_LIGHT, awaitBg(scenario, BG_LIGHT))
        }
    }

    // D7: System-Modus folgt `cmd uimode night`; Originalzustand im finally zurueck.
    @Test
    fun systemModeFollowsUiMode() {
        launch { scenario ->
            awaitReady(scenario)
            selectTheme(scenario, "system")
            assertEquals(AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM, awaitNightMode(AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM))
            // D7 (Decision D1=B): Feature-Probe; WebView ohne prefers-color-scheme (media == "not all") -> Skip.
            val media = JSONArray("[" + js(scenario, "matchMedia('(prefers-color-scheme: dark)').media") + "]").optString(0)
            val matches = js(scenario, "matchMedia('(prefers-color-scheme: dark)').matches")
            val pkg = WebViewCompat.getCurrentWebViewPackage(context)
            Log.i("SelfTest-D7", "media=$media matches=$matches webview=${pkg?.packageName} ${pkg?.versionName}")
            assumeTrue("prefers-color-scheme unbekannt: media=$media matches=$matches", media != "not all")
            val orig = Regex("Night mode: (\\w+)").find(shell("cmd uimode night"))?.groupValues?.get(1)
                ?.takeIf { it in listOf("yes", "no", "auto") } ?: "auto"
            try {
                shell("cmd uimode night no")
                assertScheme(scenario, BG_LIGHT)
                shell("cmd uimode night yes")
                assertScheme(scenario, BG_DARK)
            } finally {
                shell("cmd uimode night $orig")
            }
        }
    }

    // 1.4.0: Android-Default ohne LAYOUT-Schluessel ist "fokus" (Plattform explizit aus android_entry).
    @Test
    fun layoutDefaultFokus() {
        launch { scenario ->
            awaitReady(scenario)
            assertEquals("\"fokus\"", js(scenario, "document.documentElement.dataset.layout"))
            assertEquals("fokus", bridgeCall(scenario, "get_settings").getString("layout"))
            assertFalse(".env ohne Speichern angelegt", File(context.filesDir, ".env").exists())
        }
    }

    // 1.4.0: Nutzerpfad Layout-Umschalter -> set_layout; Wert persistiert und wirkt sofort.
    @Test
    fun setLayoutRoundtrip() {
        launch { scenario ->
            awaitReady(scenario)
            selectLayout(scenario, "werkbank")
            assertEquals("\"werkbank\"", js(scenario, "document.documentElement.dataset.layout"))
            assertEquals("werkbank", pollLayout(scenario, "werkbank"))
            selectLayout(scenario, "fokus")
            assertEquals("\"fokus\"", js(scenario, "document.documentElement.dataset.layout"))
            assertEquals("fokus", pollLayout(scenario, "fokus"))
            val bad = bridgeCall(scenario, "set_layout", "'kachel'")
            assertFalse(bad.getBoolean("ok"))
            assertEquals("Ungueltiges Layout.", bad.getString("error"))
        }
    }

    // 1.4.0: Repo-Link nur fuer die fest hinterlegte URL; fremde URL wird abgelehnt, WebView bleibt auf START_URL.
    @Test
    fun openUrlForeignRejected() {
        launch { scenario ->
            awaitReady(scenario)
            assertEquals("false", js(scenario, "AndroidBridge.open_url('https://example.com/')"))
            assertEquals("false", js(scenario, "AndroidBridge.open_url('${PyBridge.REPO_URL}/')"))
            assertEquals("false", js(scenario, "AndroidBridge.open_url('')"))
            assertEquals("\"${PyBridge.REPO_URL}\"", js(scenario, "document.getElementById('repo-link').getAttribute('href')"))
            var url: String? = null
            scenario.onActivity { url = it.webView.url }
            assertEquals(MainActivity.START_URL, url)
        }
    }

    private fun selectLayout(scenario: ActivityScenario<MainActivity>, layout: String) =
        js(scenario, "(() => { const s = document.getElementById('layout'); s.value = '$layout';" +
            " s.dispatchEvent(new Event('change')); })()")

    private fun pollLayout(scenario: ActivityScenario<MainActivity>, expected: String): String {
        val deadline = SystemClock.uptimeMillis() + 10_000
        var r = bridgeCall(scenario, "get_settings").getString("layout")
        while (r != expected && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(200)
            r = bridgeCall(scenario, "get_settings").getString("layout")
        }
        return r
    }

    private fun selectTheme(scenario: ActivityScenario<MainActivity>, mode: String) =
        js(scenario, "(() => { const s = document.getElementById('theme'); s.value = '$mode';" +
            " s.dispatchEvent(new Event('change')); })()")

    private fun awaitNightMode(expected: Int): Int {
        val deadline = SystemClock.uptimeMillis() + 10_000
        while (AppCompatDelegate.getDefaultNightMode() != expected && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(100)
        return AppCompatDelegate.getDefaultNightMode()
    }

    private fun bg(scenario: ActivityScenario<MainActivity>): String =
        JSONArray("[" + js(scenario, "getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()") + "]")
            .optString(0).lowercase()

    private fun awaitBg(scenario: ActivityScenario<MainActivity>, expected: String): String {
        val deadline = SystemClock.uptimeMillis() + 10_000
        var r = bg(scenario)
        while (r != expected && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(200)
            r = bg(scenario)
        }
        return r
    }

    // System-Modus: --bg folgt prefers-color-scheme, data-theme bleibt entfernt (View-Vertrag 4.1.6).
    private fun assertScheme(scenario: ActivityScenario<MainActivity>, expectedBg: String) {
        assertEquals(expectedBg, awaitBg(scenario, expectedBg))
        assertEquals("null", js(scenario, "document.documentElement.getAttribute('data-theme')"))
    }

    private fun launch(block: (ActivityScenario<MainActivity>) -> Unit) =
        ActivityScenario.launch(MainActivity::class.java).use(block)

    // Ergebnis als JSON-Text (evaluateJavascript), undefined/Fehler -> "null".
    private fun js(scenario: ActivityScenario<MainActivity>, script: String): String {
        val latch = CountDownLatch(1)
        var result = "null"
        scenario.onActivity {
            it.webView.evaluateJavascript(script) { r -> result = r ?: "null"; latch.countDown() }
        }
        assertTrue("evaluateJavascript Timeout", latch.await(10, TimeUnit.SECONDS))
        return result
    }

    private fun poll(scenario: ActivityScenario<MainActivity>, script: String, timeoutMs: Long): String {
        val deadline = SystemClock.uptimeMillis() + timeoutMs
        var r = js(scenario, script)
        while (r == "null" && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(200)
            r = js(scenario, script)
        }
        return r
    }

    private fun awaitReady(scenario: ActivityScenario<MainActivity>) =
        assertEquals("1", poll(scenario, "document.querySelector('#app[data-ready=\"1\"]') ? 1 : null", 30_000))

    // argsJs: JS-Argumentliste, z. B. "'fokus'".
    private fun bridgeCall(scenario: ActivityScenario<MainActivity>, method: String, argsJs: String = ""): JSONObject {
        js(scenario, "window.__st = null; window.pywebview.api.$method($argsJs).then(r => { window.__st = r; });")
        val raw = poll(scenario, "window.__st", 30_000)
        assertNotEquals("Bruecke ohne Antwort: $method", "null", raw)
        return JSONObject(raw)
    }

    private fun shell(cmd: String): String {
        val pfd = InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand(cmd)
        return ParcelFileDescriptor.AutoCloseInputStream(pfd).use { String(it.readBytes()) }
    }

    companion object {
        const val COPY_TEXT = "SELFTEST-COPY-1"
        const val BG_LIGHT = "#f4fafe"
        const val BG_DARK = "#062030"
    }
}
