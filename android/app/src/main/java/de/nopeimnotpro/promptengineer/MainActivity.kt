package de.nopeimnotpro.promptengineer

import android.app.UiModeManager
import android.content.Context
import android.content.res.Configuration
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewFeature
import java.io.ByteArrayInputStream

class MainActivity : AppCompatActivity() {
    lateinit var webView: WebView; private set
    private lateinit var container: FrameLayout
    @Volatile private var pageFinished = false

    // Theme vor attachBaseContext2 (D4/D5): AppCompat legt dort die persistente Override-Config (uiMode) an.
    // Spaeter gesetzt -> nur fluechtiges Resources.updateConfiguration, Override bleibt System-Modus.
    override fun attachBaseContext(newBase: Context) {
        // Fehler -> System folgen, nie Absturz.
        val theme = try {
            (newBase.applicationContext as App).entry.callAttr("get_theme", newBase.filesDir.absolutePath).toString()
        } catch (_: Throwable) { "system" }
        applyNightMode(theme, newBase)
        super.attachBaseContext(newBase)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        val splash = installSplashScreen()
        val app = application as App
        super.onCreate(savedInstanceState)
        splash.setKeepOnScreenCondition { !pageFinished }

        val assetLoader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this)).build()
        val shim = assets.open("bridge.js").bufferedReader().use { it.readText() }
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        webView = WebView(this)
        webView.settings.apply { javaScriptEnabled = true; domStorageEnabled = false; allowFileAccess = false; allowContentAccess = false }
        // Kein Auto-Abdunkeln: Seite steuert Farben selbst ueber prefers-color-scheme / data-theme.
        if (WebViewFeature.isFeatureSupported(WebViewFeature.ALGORITHMIC_DARKENING)) {
            WebSettingsCompat.setAlgorithmicDarkeningAllowed(webView.settings, false)
        }
        webView.webChromeClient = WebChromeClient()   // sonst liefert confirm() stumm false
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean =
                !(request.url.scheme == "https" && request.url.host == ASSET_HOST)
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse =
                assetLoader.shouldInterceptRequest(request.url) ?: WebResourceResponse(
                    "text/plain", "utf-8", 403, "Forbidden", emptyMap(), ByteArrayInputStream(ByteArray(0)))
            override fun onPageFinished(view: WebView, url: String?) {
                view.evaluateJavascript(shim, null)
                pageFinished = true
            }
        }
        webView.addJavascriptInterface(PyBridge(webView, app.entry, { app.api }, ::onThemeChanged), "AndroidBridge")

        container = FrameLayout(this)
        container.addView(webView, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
        ViewCompat.setOnApplyWindowInsetsListener(container) { v, insets ->
            val i = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime() or WindowInsetsCompat.Type.displayCutout())
            v.setPadding(i.left, i.top, i.right, i.bottom)
            WindowInsetsCompat.CONSUMED
        }
        applySystemColors()
        setContentView(container)
        webView.loadUrl(START_URL)
    }

    // configChanges inkl. uiMode: kein recreate bei Rotation/Theme-Wechsel.
    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        applySystemColors()
    }

    // PyBridge ruft nach erfolgreichem set_theme (bereits per webView.post); runOnUiThread haelt den Vertrag explizit.
    private fun onThemeChanged(theme: String) = runOnUiThread {
        applyNightMode(theme, this)
        applySystemColors()
    }

    private fun applyNightMode(theme: String, ctx: Context) {
        val (compat, system) = when (theme) {
            "light" -> AppCompatDelegate.MODE_NIGHT_NO to UiModeManager.MODE_NIGHT_NO
            "dark" -> AppCompatDelegate.MODE_NIGHT_YES to UiModeManager.MODE_NIGHT_YES
            else -> AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM to UiModeManager.MODE_NIGHT_AUTO
        }
        // API 31+: System-Splash entsteht vor dem App-Prozess; nur der vom System pro App persistierte Modus
        // greift dort (ab naechstem Kaltstart). AppCompat 1.7.1 ruft setApplicationNightMode nicht selbst.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            ctx.getSystemService(UiModeManager::class.java)?.setApplicationNightMode(system)
        }
        AppCompatDelegate.setDefaultNightMode(compat)
    }

    private fun isNight() =
        resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES

    // Hintergrund und Leisten-Icons aus derselben Quelle (Activity-Resources); enableEdgeToEdge wertet
    // sonst decorView.resources aus, auch beim eigenen Re-Apply nach Config-Wechsel (activity 1.13).
    private fun applySystemColors() {
        val bg = ContextCompat.getColor(this, R.color.app_bg)
        container.setBackgroundColor(bg)
        webView.setBackgroundColor(bg)
        enableEdgeToEdge(
            SystemBarStyle.auto(Color.TRANSPARENT, Color.TRANSPARENT) { isNight() },
            SystemBarStyle.auto(LIGHT_SCRIM, DARK_SCRIM) { isNight() },
        )
    }

    companion object {
        const val ASSET_HOST = "appassets.androidplatform.net"
        const val START_URL = "https://$ASSET_HOST/assets/static/index.html"
        // = Default-Scrims von enableEdgeToEdge (androidx.activity 1.13).
        private val LIGHT_SCRIM = Color.argb(0xe6, 0xFF, 0xFF, 0xFF)
        private val DARK_SCRIM = Color.argb(0x80, 0x1b, 0x1b, 0x1b)
    }
}
