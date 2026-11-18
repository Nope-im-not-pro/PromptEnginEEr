// AGP 9: Kotlin eingebaut (built-in Kotlin), kein org.jetbrains.kotlin.android hier.
import java.util.Properties

plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

// Single Source: Python-Quellen und View liegen im Repo-Root, Gradle spiegelt vor jedem Build.
val repoRoot = rootProject.projectDir.parentFile
val genPy = layout.buildDirectory.dir("generated/python")
val genAssets = layout.buildDirectory.dir("generated/assets")

val syncPython by tasks.registering(Sync::class) {
    from(repoRoot) {
        include("android_entry.py", "controllers/**", "services/**", "models/**")
        exclude("**/__pycache__/**")
    }
    into(genPy)
}
val syncStatic by tasks.registering(Sync::class) {
    from(repoRoot.resolve("static")) { into("static") }
    into(genAssets)
}

android {
    namespace = "de.nopeimnotpro.promptengineer"
    compileSdk = 36
    defaultConfig {
        applicationId = "de.nopeimnotpro.promptengineer"
        minSdk = 26
        targetSdk = 36
        versionCode = 10401          // MAJOR*10000 + MINOR*100 + PATCH
        versionName = "1.4.1"
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }  // Geraete + Emulator
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        testInstrumentationRunnerArguments["clearPackageData"] = "true"
    }
    // AGP 9 verbietet Provider im SourceSet-API -> fester Pfad; Task-Abhaengigkeit ueber preBuild.
    sourceSets["main"].assets.directories.add(genAssets.get().asFile.path)
    buildFeatures { buildConfig = true }   // BuildConfig.DEBUG -> WebView-Debugging nur im Debug-Build
    // Release-Signatur nur aus lokaler, nicht versionierter Datei (Schluessel: storeFile, storePassword, keyAlias, keyPassword).
    val keystoreProps = rootProject.file("keystore.properties")
    if (keystoreProps.exists()) {
        val props = Properties().apply { keystoreProps.inputStream().use { load(it) } }
        signingConfigs.create("release") {
            storeFile = rootProject.file(props.getProperty("storeFile"))
            storePassword = props.getProperty("storePassword")
            keyAlias = props.getProperty("keyAlias")
            keyPassword = props.getProperty("keyPassword")
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = if (keystoreProps.exists()) {
                signingConfigs.getByName("release")
            } else {
                logger.warn("Release mit Debug-Signatur: nicht verteilbar")
                signingConfigs.getByName("debug")
            }
        }
    }
    testOptions {
        execution = "ANDROIDX_TEST_ORCHESTRATOR"
    }
}

chaquopy {
    defaultConfig {
        version = "3.11"
        buildPython("py", "-3.11")   // Windows-Launcher, wie .venv
        pip {
            install("httpx==0.28.1")
            install("python-dotenv==1.2.4")
        }
    }
    sourceSets { getByName("main") { srcDir(genPy) } }
}

tasks.named("preBuild") { dependsOn(syncPython, syncStatic) }
// Chaquopy-Merge haengt nicht an preBuild -> explizite Abhaengigkeit (Gradle-Validierung).
tasks.matching { it.name.matches(Regex("merge\\w*PythonSources")) }.configureEach { dependsOn(syncPython) }

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("androidx.core:core-ktx:1.18.0")
    implementation("androidx.activity:activity:1.13.0")
    implementation("androidx.webkit:webkit:1.17.1")
    implementation("androidx.core:core-splashscreen:1.2.0")
    implementation("com.google.android.material:material:1.14.0")

    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    androidTestUtil("androidx.test:orchestrator:1.6.1")
}
