"""PySide6 QtWebEngine read-only desktop host. No auto-install or network."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from .controller import LabController


def main() -> int:
    try:
        from PySide6.QtCore import QObject, QUrl, Slot
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWebChannel import QWebChannel
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings, QWebEngineUrlRequestInterceptor
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except (ImportError, OSError) as ex:
        print(f'GUI_STATUS=HOLD_MISSING_PYSIDE6_QTWEBENGINE {type(ex).__name__}: {ex}', flush=True)
        print('GUI_DEPENDENCIES=NOT_AUTO_INSTALLED_OFFLINE', flush=True)
        return 4

    root = Path(__file__).resolve().parent
    index = (root / 'web' / 'index.html').resolve()
    approved = QUrl.fromLocalFile(str(index))
    controller = LabController()

    class NetworkGate(QWebEngineUrlRequestInterceptor):
        def interceptRequest(self, request):
            if request.requestUrl().scheme() not in ('file', 'qrc', 'data'):
                request.block(True)

    class LocalPage(QWebEnginePage):
        def acceptNavigationRequest(self, url, nav_type, is_main_frame):
            if is_main_frame and url != approved:
                print('CP02_NAVIGATION_BLOCKED', flush=True)
                return False
            return True

    class Bridge(QObject):
        @Slot(result=str)
        def getSnapshot(self):
            return json.dumps(controller.snapshot(), ensure_ascii=False)

        @Slot(str, bool, result=str)
        def setEnabled(self, ext_id: str, enabled: bool):
            obj = controller.set_enabled(ext_id, enabled)
            print(f'CP02_EXTENSION_TOGGLE={"PASS" if obj["ok"] else "HOLD"}', flush=True)
            return json.dumps(obj, ensure_ascii=False)

        @Slot(str, result=str)
        def demo(self, kind: str):
            obj = controller.demo(kind)
            if obj['ok']:
                result = obj['report']
                print(f'CP02_DEMO_{kind.upper()}={result["status"]}', flush=True)
            else:
                print(f'CP02_DEMO_DENIED={kind}', flush=True)
            return json.dumps(obj, ensure_ascii=False)

    app = QApplication(sys.argv[:1])
    app.setApplicationName('MMD Anime Studio Lab CP02')
    profile = QWebEngineProfile.defaultProfile()
    # In-memory cache and cookies. No persistent browser state.
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
    interceptor = NetworkGate()
    profile.setUrlRequestInterceptor(interceptor)
    view = QWebEngineView()
    page = LocalPage(profile, view)
    view.setPage(page)
    settings = page.settings()
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False)
    bridge = Bridge()
    channel = QWebChannel(page)
    channel.registerObject('mmdLab', bridge)
    page.setWebChannel(channel)
    view.load(approved)
    view.setWindowTitle('MMD Anime Studio — MMD Lab CP02 Preview')
    view.resize(1330, 850)
    view.show()
    print('GUI_STATUS=STARTED_OFFLINE_SYNTHETIC_ONLY', flush=True)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
