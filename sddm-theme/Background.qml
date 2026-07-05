/*
    SPDX-FileCopyrightText: 2016 Boudhayan Gupta <bgupta@kde.org>

    SPDX-License-Identifier: LGPL-2.0-or-later

    Extended to support "web" backgrounds (an HTML/CSS/JS animation
    rendered through WebEngineView), on top of the original image/color
    modes - see plasma-css-wallpaper's template.html for the animation
    conventions (?fps=, ?scale=, ?frozen=) this reuses.
*/

import QtQuick
import QtWebEngine

FocusScope {
    id: sceneBackground

    property var sceneBackgroundType
    property alias sceneBackgroundColor: sceneColorBackground.color
    property alias sceneBackgroundImage: sceneImageBackground.source

    // "web" background configuration.
    property string sceneBackgroundWebFile: ""
    property int    sceneBackgroundWebFps: 30
    property int    sceneBackgroundWebScale: 60

    Rectangle {
        id: sceneColorBackground
        anchors.fill: parent
    }

    Image {
        id: sceneImageBackground
        anchors.fill: parent
        sourceSize.width: parent.width
        sourceSize.height: parent.height
        fillMode: Image.PreserveAspectCrop
        smooth: true;
    }

    Item {
        id: sceneWebBackground
        anchors.fill: parent
        visible: false

        // Render at a fraction of the greeter's actual pixel size, then
        // let Qt Quick scale the result back up - same trade-off as the
        // Plasma wallpaper plugin's "Render resolution" setting, since
        // continuous animation inside WebEngineView is the dominant GPU
        // cost regardless of visual complexity, not something you want
        // running expensively on a screen nobody may even be looking at.
        readonly property real renderScale: sceneBackgroundWebScale / 100

        WebEngineView {
            x: 0
            y: 0
            width: parent.width * sceneWebBackground.renderScale
            height: parent.height * sceneWebBackground.renderScale
            scale: 1 / sceneWebBackground.renderScale
            transformOrigin: Item.TopLeft

            url: sceneBackgroundWebFile.length > 0
                 ? (Qt.resolvedUrl(sceneBackgroundWebFile)
                    + "?fps=" + sceneBackgroundWebFps
                    + "&scale=" + sceneBackgroundWebScale
                    + "&frozen=0")
                 : ""
            settings.scrollAnimatorEnabled: false
            settings.pluginsEnabled: false
            settings.webGLEnabled: false
            settings.showScrollBars: false
            backgroundColor: "black"

            // Purely decorative background: the greeter's own login form
            // handles all input, this must never intercept it.
            enabled: false
        }
    }

    states: [
        State {
            name: "imageBackground"
            when: sceneBackgroundType === "image"
            PropertyChanges { target: sceneColorBackground; visible: false }
            PropertyChanges { target: sceneImageBackground; visible: true }
            PropertyChanges { target: sceneWebBackground; visible: false }
        },
        State {
            name: "webBackground"
            when: sceneBackgroundType === "web"
            PropertyChanges { target: sceneColorBackground; visible: false }
            PropertyChanges { target: sceneImageBackground; visible: false }
            PropertyChanges { target: sceneWebBackground; visible: true }
        },
        State {
            name: "colorBackground"
            when: sceneBackgroundType !== "image" && sceneBackgroundType !== "web"
            PropertyChanges { target: sceneColorBackground; visible: true }
            PropertyChanges { target: sceneImageBackground; visible: false }
            PropertyChanges { target: sceneWebBackground; visible: false }
        }
    ]
}
