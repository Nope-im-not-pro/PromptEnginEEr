package de.nopeimnotpro.promptengineer

import android.app.Application
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class App : Application() {
    lateinit var entry: PyObject
        private set

    // AB8: erst im Bruecken-Worker ausgewertet; lazy speichert keine Exception -> naechster Aufruf versucht erneut.
    val api: PyObject by lazy { entry.callAttr("create_api", filesDir.absolutePath) }

    override fun onCreate() {
        super.onCreate()
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        entry = Python.getInstance().getModule("android_entry")
    }
}
