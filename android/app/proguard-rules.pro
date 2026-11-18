# R8: Bruecken-Methoden (AndroidBridge in PyBridge.kt) nicht umbenennen/entfernen.
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
