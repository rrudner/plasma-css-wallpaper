import QtQuick
import QtWebEngine
import org.kde.plasma.plasmoid
// Private KDE API (used by the built-in battery monitor applet) to read
// the active power-profile-daemon profile. Not a stable/public interface,
// so this could break on a future Plasma release - if PowerProfilesControl
// is ever removed/renamed, powerControl.activeProfile will just stay
// empty, which is treated as "not power-saver" (fails open, never wrong
// in the direction of leaving the wallpaper stuck frozen).
import org.kde.plasma.private.batterymonitor as BatteryMonitor

WallpaperItem {
    id: root

    // Render the page at a fraction of the screen's actual pixel size,
    // then let Qt Quick scale the result back up. Chromium only has to
    // rasterize/composite renderScale^2 of the native pixel count each
    // frame; the upscale itself is a cheap GPU blit, far cheaper than
    // Chromium doing full-resolution work every frame. Both knobs are
    // user-configurable in the wallpaper settings dialog.
    readonly property real renderScale: root.configuration.RenderScale / 100
    readonly property int frameRate: root.configuration.FrameRate

    // Frozen either because the user checked "Freeze" manually, or because
    // the system's power profile is currently "power-saver".
    readonly property bool frozen: root.configuration.Freeze || powerControl.activeProfile === "power-saver"

    BatteryMonitor.PowerProfilesControl {
        id: powerControl
    }

    // Animations are trusted to honor "frozen" themselves (stop their own
    // timers/rAF loops and show just a static frame) rather than having
    // this file forcibly tear down WebEngineView and paint flat black -
    // that would hide whatever nice static background an animation has
    // (see thinkpad-ambient.html, which keeps its grid+vignette but
    // drops the embers when frozen). An animation that ignores the
    // ?frozen= parameter simply keeps animating - same as an animation
    // that ignores ?fps= or ?scale=.
    WebEngineView {
        x: 0
        y: 0
        width: root.width  * root.renderScale
        height: root.height * root.renderScale
        scale: 1 / root.renderScale
        transformOrigin: Item.TopLeft

        // fps/scale/frozen are read by animations that choose to respect
        // them (see thinkpad-ambient.html); pages that ignore any of
        // these just get an unused query parameter. Including scale and
        // frozen here also means changing either forces WebEngineView to
        // reload/renavigate - necessary for scale, since otherwise the
        // page keeps the window.innerWidth/innerHeight it read at its
        // original load size, so animations sized against those stale
        // values stop matching the view after a resize.
        url: Qt.resolvedUrl("../html/" + root.configuration.HtmlFile)
             + "?fps=" + root.frameRate
             + "&scale=" + root.configuration.RenderScale
             + "&frozen=" + (root.frozen ? 1 : 0)
        settings.scrollAnimatorEnabled: false
        settings.pluginsEnabled: false
        settings.webGLEnabled: false
        settings.showScrollBars: false
        backgroundColor: "black"

        // Purely decorative background: disabling input lets clicks/drags
        // pass through to the desktop, so icon rubber-band selection works.
        enabled: false
    }
}
