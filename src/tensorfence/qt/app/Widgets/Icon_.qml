import QtQuick 2.15

Item {
    id: root

    property string icon: ""
    property color color: theme.subTextColor
    property bool mirror: false

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            const ctx = getContext("2d")
            const w = width
            const h = height
            const s = Math.min(w, h)
            const pad = s * 0.18

            if (ctx.resetTransform) {
                ctx.resetTransform()
            } else if (ctx.setTransform) {
                ctx.setTransform(1, 0, 0, 1, 0, 0)
            }
            ctx.clearRect(0, 0, w, h)
            ctx.translate(w / 2, h / 2)
            if (root.mirror) {
                ctx.scale(-1, 1)
            }
            ctx.translate(-w / 2, -h / 2)
            ctx.strokeStyle = root.color
            ctx.fillStyle = root.color
            ctx.lineWidth = Math.max(1.6, s * 0.1)
            ctx.lineCap = "round"
            ctx.lineJoin = "round"

            function line(x1, y1, x2, y2) {
                ctx.beginPath()
                ctx.moveTo(x1, y1)
                ctx.lineTo(x2, y2)
                ctx.stroke()
            }

            function rect(x, y, rw, rh, fill) {
                ctx.beginPath()
                ctx.rect(x, y, rw, rh)
                if (fill) {
                    ctx.fill()
                } else {
                    ctx.stroke()
                }
            }

            function roundRect(x, y, rw, rh, r, fill) {
                ctx.beginPath()
                ctx.moveTo(x + r, y)
                ctx.lineTo(x + rw - r, y)
                ctx.quadraticCurveTo(x + rw, y, x + rw, y + r)
                ctx.lineTo(x + rw, y + rh - r)
                ctx.quadraticCurveTo(x + rw, y + rh, x + rw - r, y + rh)
                ctx.lineTo(x + r, y + rh)
                ctx.quadraticCurveTo(x, y + rh, x, y + rh - r)
                ctx.lineTo(x, y + r)
                ctx.quadraticCurveTo(x, y, x + r, y)
                if (fill) {
                    ctx.fill()
                } else {
                    ctx.stroke()
                }
            }

            function triangle(points, fill) {
                ctx.beginPath()
                ctx.moveTo(points[0][0], points[0][1])
                for (let i = 1; i < points.length; i++) {
                    ctx.lineTo(points[i][0], points[i][1])
                }
                ctx.closePath()
                if (fill) {
                    ctx.fill()
                } else {
                    ctx.stroke()
                }
            }

            switch (root.icon) {
            case "add":
                line(w / 2, pad, w / 2, h - pad)
                line(pad, h / 2, w - pad, h / 2)
                break
            case "close":
            case "no":
                line(pad, pad, w - pad, h - pad)
                line(w - pad, pad, pad, h - pad)
                break
            case "pin":
                triangle([[w * 0.35, h * 0.18], [w * 0.65, h * 0.18], [w * 0.58, h * 0.48], [w * 0.42, h * 0.48]], false)
                line(w * 0.5, h * 0.48, w * 0.5, h * 0.82)
                line(w * 0.43, h * 0.8, w * 0.57, h * 0.8)
                break
            case "lock":
                ctx.beginPath()
                ctx.arc(w * 0.5, h * 0.38, s * 0.16, Math.PI, 0)
                ctx.stroke()
                roundRect(w * 0.26, h * 0.42, w * 0.48, h * 0.36, s * 0.08, false)
                break
            case "lock_open":
                ctx.beginPath()
                ctx.arc(w * 0.44, h * 0.38, s * 0.16, Math.PI * 1.05, Math.PI * 1.92)
                ctx.stroke()
                roundRect(w * 0.26, h * 0.42, w * 0.48, h * 0.36, s * 0.08, false)
                break
            case "arrow_to_left":
                line(w * 0.68, h * 0.22, w * 0.34, h * 0.5)
                line(w * 0.34, h * 0.5, w * 0.68, h * 0.78)
                break
            case "arrow_to_center":
                line(w * 0.24, h * 0.5, w * 0.44, h * 0.5)
                line(w * 0.38, h * 0.36, w * 0.52, h * 0.5)
                line(w * 0.38, h * 0.64, w * 0.52, h * 0.5)
                line(w * 0.76, h * 0.5, w * 0.56, h * 0.5)
                line(w * 0.62, h * 0.36, w * 0.48, h * 0.5)
                line(w * 0.62, h * 0.64, w * 0.48, h * 0.5)
                break
            case "split_view":
                roundRect(w * 0.18, h * 0.18, w * 0.22, h * 0.64, s * 0.06, false)
                roundRect(w * 0.6, h * 0.18, w * 0.22, h * 0.64, s * 0.06, false)
                break
            case "folder":
                ctx.beginPath()
                ctx.moveTo(w * 0.18, h * 0.34)
                ctx.lineTo(w * 0.42, h * 0.34)
                ctx.lineTo(w * 0.5, h * 0.24)
                ctx.lineTo(w * 0.82, h * 0.24)
                ctx.lineTo(w * 0.82, h * 0.74)
                ctx.lineTo(w * 0.18, h * 0.74)
                ctx.closePath()
                ctx.stroke()
                break
            case "menu":
                line(w * 0.22, h * 0.28, w * 0.78, h * 0.28)
                line(w * 0.22, h * 0.5, w * 0.78, h * 0.5)
                line(w * 0.22, h * 0.72, w * 0.78, h * 0.72)
                break
            case "run":
                triangle([[w * 0.34, h * 0.24], [w * 0.74, h * 0.5], [w * 0.34, h * 0.76]], true)
                break
            case "save":
                roundRect(w * 0.22, h * 0.2, w * 0.56, h * 0.6, s * 0.05, false)
                rect(w * 0.32, h * 0.24, w * 0.3, h * 0.16, false)
                line(w * 0.32, h * 0.58, w * 0.68, h * 0.58)
                break
            default:
                roundRect(w * 0.24, h * 0.24, w * 0.52, h * 0.52, s * 0.08, false)
                break
            }
        }
    }

    onIconChanged: canvas.requestPaint()
    onColorChanged: canvas.requestPaint()
    onMirrorChanged: canvas.requestPaint()
    onWidthChanged: canvas.requestPaint()
    onHeightChanged: canvas.requestPaint()
}
