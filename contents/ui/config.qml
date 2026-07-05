import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import Qt.labs.folderlistmodel

ColumnLayout {
    id: root

    property var configDialog
    property var wallpaperConfiguration: wallpaper.configuration
    property var parentLayout

    property string cfg_HtmlFile: "deep-ocean.html"
    property string cfg_HtmlFileDefault: "deep-ocean.html"

    property int cfg_RenderScale: 60
    property int cfg_RenderScaleDefault: 60

    property int cfg_FrameRate: 30
    property int cfg_FrameRateDefault: 30

    property bool cfg_Freeze: false
    property bool cfg_FreezeDefault: false

    signal configurationChanged()

    FolderListModel {
        id: folderModel
        folder: Qt.resolvedUrl("../html/")
        nameFilters: ["*.html"]
        showDirs: false
        showFiles: true
        sortField: FolderListModel.Name

        onCountChanged: {
            for (let i = 0; i < count; i++) {
                if (get(i, "fileName") === cfg_HtmlFile) {
                    combo.currentIndex = i
                    return
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 8

        QQC2.Label {
            text: "Animation:"
        }

        QQC2.ComboBox {
            id: combo
            Layout.fillWidth: true
            model: folderModel
            textRole: "fileBaseName"

            onActivated: {
                cfg_HtmlFile = folderModel.get(currentIndex, "fileName")
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 8

        QQC2.Label {
            text: "Render resolution:"
        }

        QQC2.Slider {
            id: scaleSlider
            Layout.fillWidth: true
            from: 10
            to: 100
            stepSize: 1
            value: cfg_RenderScale

            onMoved: cfg_RenderScale = Math.round(value)
        }

        QQC2.SpinBox {
            id: scaleSpin
            from: 10
            to: 100
            stepSize: 1
            editable: true
            value: cfg_RenderScale
            textFromValue: (value) => value + "%"
            valueFromText: (text) => parseInt(text, 10) || 0

            onValueModified: cfg_RenderScale = value
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 8

        QQC2.Label {
            text: "Target FPS:"
        }

        QQC2.SpinBox {
            id: fpsSpin
            Layout.fillWidth: true
            from: 1
            to: 360
            stepSize: 1
            value: cfg_FrameRate
            editable: true

            onValueModified: cfg_FrameRate = value
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 8

        QQC2.CheckBox {
            id: freezeCheck
            text: "Freeze animation (battery saver)"
            checked: cfg_Freeze

            onToggled: cfg_Freeze = checked
        }
    }
}
