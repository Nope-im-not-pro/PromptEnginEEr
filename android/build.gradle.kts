// Versionen gepinnt; Kompatibilitaet laut Chaquopy-Tabelle (17.0: AGP 7.3 - 9.2).
// AGP 9 kompiliert Kotlin eingebaut (built-in Kotlin); der Kotlin-Plugin-Eintrag
// pinnt nur die KGP-Version auf dem Build-Classpath und wird nicht angewendet.
plugins {
    id("com.android.application") version "9.2.1" apply false
    id("org.jetbrains.kotlin.android") version "2.4.10" apply false
    id("com.chaquo.python") version "17.0.0" apply false
}
