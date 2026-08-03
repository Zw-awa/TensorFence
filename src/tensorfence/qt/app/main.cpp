#include <QGuiApplication>
#include <QFile>
#include <QDateTime>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQmlError>
#include <QQuickStyle>
#include <QUrl>
#include <QStandardPaths>
#include <QTextStream>
#include <QTimer>

#include "appcontroller.h"

namespace {

void appendStartupLog(const QString &line) {
    const QString tempDir = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
    if (tempDir.isEmpty()) {
        return;
    }

    QFile file(tempDir + "/TensorFence-startup.log");
    if (!file.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text)) {
        return;
    }

    QTextStream stream(&file);
    stream.setEncoding(QStringConverter::Utf8);
    stream << QDateTime::currentDateTime().toString(Qt::ISODate) << " " << line << "\n";
}

}  // namespace

int main(int argc, char *argv[]) {
    QGuiApplication app(argc, argv);
    app.setApplicationName("TensorFence");
    app.setApplicationDisplayName("TensorFence");

    QQuickStyle::setStyle("Basic");

    tensorfence::qt::AppController controller;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("appController", &controller);
    engine.setInitialProperties({{"controller", QVariant::fromValue(&controller)}});
    QObject::connect(&engine, &QQmlApplicationEngine::warnings, &engine, [](const QList<QQmlError> &warnings) {
        for (const QQmlError &warning : warnings) {
            appendStartupLog(QStringLiteral("QML warning: %1").arg(warning.toString()));
        }
    });
    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() {
            appendStartupLog(QStringLiteral("QML object creation failed."));
            QCoreApplication::exit(-1);
        },
        Qt::QueuedConnection);
    engine.load(QUrl(QStringLiteral("qrc:/TensorFence/UI/Main.qml")));

    if (engine.rootObjects().isEmpty()) {
        appendStartupLog(QStringLiteral("No root objects were created for qrc:/TensorFence/UI/Main.qml."));
        return -1;
    }

    if (app.arguments().contains(QStringLiteral("--smoke-test"))) {
        QTimer::singleShot(1500, &app, &QCoreApplication::quit);
    }

    return app.exec();
}
