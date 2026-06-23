#include "appcontroller.h"

#include <QFileInfo>
#include <QUrl>

namespace tensorfence::qt {

AppController::AppController(QObject *parent) : QObject(parent) {}

QString AppController::currentPage() const { return currentPage_; }
QString AppController::currentFocus() const { return currentFocus_; }
QString AppController::currentPath() const { return currentPath_; }
QString AppController::recentAction() const { return recentAction_; }
QString AppController::statusPrimary() const { return statusPrimary_; }
QString AppController::statusSecondary() const { return statusSecondary_; }
QString AppController::workspacePill() const { return workspacePill_; }
QStringList AppController::recentFiles() const { return recentFiles_; }

void AppController::navigateTo(const QString &pageKey) {
    currentPage_ = pageKey;
    if (pageKey == QStringLiteral("home")) {
        currentFocus_ = QStringLiteral("开始使用");
    } else if (pageKey == QStringLiteral("contracts")) {
        currentFocus_ = QStringLiteral("契约文件");
    } else if (pageKey == QStringLiteral("reports")) {
        currentFocus_ = QStringLiteral("诊断报告");
    } else if (pageKey == QStringLiteral("compare")) {
        currentFocus_ = QStringLiteral("阶段对比");
    } else if (pageKey == QStringLiteral("settings")) {
        currentFocus_ = QStringLiteral("工程环境");
    }
    setStatus(currentFocus_, QString());
    emit stateChanged();
}

void AppController::activateWorkflow(const QString &workflowId) {
    if (workflowId == QStringLiteral("draft")) {
        navigateTo(QStringLiteral("contracts"));
        recentAction_ = QStringLiteral("生成草稿");
        emit bannerRequested(QStringLiteral("生成草稿"), QStringLiteral("success"));
    } else if (workflowId == QStringLiteral("inspect")) {
        navigateTo(QStringLiteral("reports"));
        recentAction_ = QStringLiteral("图像检查");
        emit bannerRequested(QStringLiteral("图像检查"), QStringLiteral("info"));
    } else {
        navigateTo(QStringLiteral("compare"));
        recentAction_ = workflowId == QStringLiteral("probe") ? QStringLiteral("模型探查") : QStringLiteral("阶段对比");
        emit bannerRequested(recentAction_, QStringLiteral("info"));
    }
    emit stateChanged();
}

void AppController::handleDroppedUrls(const QVariantList &urls) {
    QStringList accepted;
    QStringList rejected;
    for (const QVariant &item : urls) {
        const QUrl url = item.toUrl();
        if (!url.isLocalFile()) {
            continue;
        }
        const QString path = url.toLocalFile();
        if (isSupportedPath(path)) {
            accepted.append(path);
        } else {
            rejected.append(path);
        }
    }

    if (!accepted.isEmpty()) {
        for (const QString &path : accepted) {
            updateRecentFiles(path);
        }
        openPath(accepted.first());
        workspacePill_ = QStringLiteral("已接收 %1 个文件").arg(accepted.size());
        emit recentFilesChanged();
    }

    if (!rejected.isEmpty()) {
        emit bannerRequested(QStringLiteral("忽略了 %1 个不支持的文件").arg(rejected.size()), QStringLiteral("warning"));
    }

    emit stateChanged();
}

void AppController::openPath(const QString &path) {
    const RouteInfo route = routeFile(path);
    if (!route.valid) {
        recentAction_ = QStringLiteral("文件类型不支持");
        setStatus(QStringLiteral("文件类型不支持"), path);
        emit bannerRequested(QStringLiteral("文件类型不支持"), QStringLiteral("warning"));
        emit stateChanged();
        return;
    }

    currentPage_ = route.pageKey;
    updateContext(route.title, route.path, route.feedback);
    setStatus(route.feedback, QStringLiteral("已载入"));
    updateRecentFiles(path);
    workspacePill_ = QStringLiteral("已就绪");
    emit recentFilesChanged();
    emit bannerRequested(route.feedback, route.warning ? QStringLiteral("warning") : QStringLiteral("success"));
    emit stateChanged();
}

void AppController::acknowledgeAction(const QString &label) {
    recentAction_ = label;
    setStatus(label, QString());
    emit bannerRequested(label, QStringLiteral("info"));
    emit stateChanged();
}

void AppController::setStatus(const QString &primary, const QString &secondary) {
    statusPrimary_ = primary;
    statusSecondary_ = secondary;
}

void AppController::updateContext(const QString &focus, const QString &path, const QString &action) {
    currentFocus_ = focus;
    currentPath_ = path;
    recentAction_ = action;
}

void AppController::updateRecentFiles(const QString &path) {
    recentFiles_.removeAll(path);
    recentFiles_.prepend(path);
    while (recentFiles_.size() > 8) {
        recentFiles_.removeLast();
    }
}

AppController::RouteInfo AppController::routeFile(const QString &path) const {
    const QFileInfo info(path);
    const QString suffix = info.suffix().toLower();
    const QString fileName = info.fileName().toLower();

    if (suffix == QStringLiteral("yaml") || suffix == QStringLiteral("yml")) {
        return {QStringLiteral("contracts"), QStringLiteral("契约文件"), QStringLiteral("已载入契约文件"), path, true, false};
    }
    if (suffix == QStringLiteral("onnx") || suffix == QStringLiteral("rknn") || suffix == QStringLiteral("npz")) {
        return {QStringLiteral("compare"), QStringLiteral("阶段对比"), QStringLiteral("已载入对比输入"), path, true, false};
    }
    if (suffix == QStringLiteral("md") || suffix == QStringLiteral("html")) {
        return {QStringLiteral("reports"), QStringLiteral("诊断报告"), QStringLiteral("已载入诊断报告"), path, true, false};
    }
    if (suffix == QStringLiteral("json")) {
        if (fileName == QStringLiteral("tensor_diffs.json") || fileName == QStringLiteral("final_summary.json")) {
            return {QStringLiteral("compare"), QStringLiteral("阶段对比"), QStringLiteral("已载入阶段摘要"), path, true, false};
        }
        return {QStringLiteral("reports"), QStringLiteral("诊断报告"), QStringLiteral("已载入 JSON 报告"), path, true, true};
    }
    return {};
}

bool AppController::isSupportedPath(const QString &path) const {
    return routeFile(path).valid;
}

}  // namespace tensorfence::qt
