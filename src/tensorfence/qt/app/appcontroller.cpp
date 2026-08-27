#include "appcontroller.h"

#include <QFileInfo>
#include <QDesktopServices>
#include <QDir>
#include <QSettings>
#include <QUrl>

namespace tensorfence::qt {

AppController::AppController(QObject *parent) : QObject(parent) {
    QSettings settings;
    const QString savedCliPath = settings.value(QStringLiteral("runtime/cliPath")).toString();
    if (!savedCliPath.isEmpty() && QFileInfo::exists(savedCliPath)) {
        cliPath_ = QFileInfo(savedCliPath).absoluteFilePath();
        workspacePill_ = QStringLiteral("CLI 已恢复");
        statusPrimary_ = QStringLiteral("已恢复本机 CLI");
        statusSecondary_ = cliPath_;
    } else if (!savedCliPath.isEmpty()) {
        statusPrimary_ = QStringLiteral("上次 CLI 路径已失效");
        statusSecondary_ = savedCliPath;
        workspacePill_ = QStringLiteral("需重新选择 CLI");
    }
    wslDistro_ = settings.value(QStringLiteral("runtime/wslDistro"), wslDistro_).toString();
    wslTargetName_ = settings.value(QStringLiteral("runtime/wslTargetName"), wslTargetName_).toString();
    wslCondaPath_ = settings.value(QStringLiteral("runtime/wslCondaPath"), wslCondaPath_).toString();
    wslEnvironment_ = settings.value(QStringLiteral("runtime/wslEnvironment"), wslEnvironment_).toString();
    wslPythonPath_ = settings.value(QStringLiteral("runtime/wslPythonPath"), wslPythonPath_).toString();
}

QString AppController::currentPage() const { return currentPage_; }
QString AppController::currentFocus() const { return currentFocus_; }
QString AppController::currentPath() const { return currentPath_; }
QString AppController::recentAction() const { return recentAction_; }
QString AppController::statusPrimary() const { return statusPrimary_; }
QString AppController::statusSecondary() const { return statusSecondary_; }
QString AppController::workspacePill() const { return workspacePill_; }
QStringList AppController::recentFiles() const { return recentFiles_; }
QString AppController::cliPath() const { return cliPath_; }
QString AppController::contractPath() const { return contractPath_; }
QString AppController::modelPath() const { return modelPath_; }
QString AppController::fp16ArtifactPath() const { return fp16ArtifactPath_; }
QString AppController::int8ArtifactPath() const { return int8ArtifactPath_; }
QString AppController::reportPath() const { return reportPath_; }
QString AppController::imagePath() const { return imagePath_; }
QString AppController::wslDistro() const { return wslDistro_; }
QString AppController::wslTargetName() const { return wslTargetName_; }
QString AppController::wslCondaPath() const { return wslCondaPath_; }
QString AppController::wslEnvironment() const { return wslEnvironment_; }
QString AppController::wslPythonPath() const { return wslPythonPath_; }
QString AppController::commandOutput() const { return commandOutput_; }
bool AppController::commandRunning() const { return process_ != nullptr; }

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

void AppController::setCliPath(const QString &path) {
    const QFileInfo info(path);
    if (!info.exists() || !info.isFile()) {
        emit bannerRequested(QStringLiteral("CLI 路径不存在或不是文件"), QStringLiteral("warning"));
        return;
    }
    cliPath_ = info.absoluteFilePath();
    QSettings settings;
    settings.setValue(QStringLiteral("runtime/cliPath"), cliPath_);
    settings.sync();
    updateRecentFiles(cliPath_);
    setStatus(QStringLiteral("已配置本机 CLI"), cliPath_);
    workspacePill_ = QStringLiteral("CLI 已就绪");
    emit recentFilesChanged();
    emit bannerRequested(QStringLiteral("已配置本机 CLI：%1").arg(info.fileName()), QStringLiteral("success"));
    emit stateChanged();
}

void AppController::setSessionPath(const QString &role, const QString &path) {
    const QFileInfo info(path);
    if (!info.exists() || !info.isFile()) {
        emit bannerRequested(QStringLiteral("所选文件不存在"), QStringLiteral("warning"));
        return;
    }
    const QString absolutePath = info.absoluteFilePath();
    if (role == QStringLiteral("contract")) {
        contractPath_ = absolutePath;
    } else if (role == QStringLiteral("model")) {
        modelPath_ = absolutePath;
    } else if (role == QStringLiteral("fp16")) {
        fp16ArtifactPath_ = absolutePath;
    } else if (role == QStringLiteral("int8")) {
        int8ArtifactPath_ = absolutePath;
    } else if (role == QStringLiteral("report")) {
        reportPath_ = absolutePath;
    } else if (role == QStringLiteral("image")) {
        imagePath_ = absolutePath;
    } else {
        emit bannerRequested(QStringLiteral("未知文件角色"), QStringLiteral("warning"));
        return;
    }
    updateRecentFiles(absolutePath);
    const QString displayName = roleDisplayName(role);
    updateContext(currentFocus_, absolutePath, QStringLiteral("已载入 %1").arg(displayName));
    setStatus(QStringLiteral("已载入 %1").arg(displayName), info.fileName());
    workspacePill_ = QStringLiteral("输入已更新");
    emit recentFilesChanged();
    emit bannerRequested(QStringLiteral("已载入 %1：%2").arg(displayName, info.fileName()), QStringLiteral("success"));
    emit stateChanged();
}

void AppController::setWslConfiguration(const QString &targetName, const QString &distro, const QString &condaPath, const QString &environment, const QString &pythonPath) {
    if (targetName.trimmed().isEmpty() || distro.trimmed().isEmpty() || (condaPath.trimmed().isEmpty() != environment.trimmed().isEmpty())) {
        emit bannerRequested(QStringLiteral("目标名和 WSL 发行版不能为空；Conda 路径和环境名需同时填写或同时留空"), QStringLiteral("warning"));
        return;
    }
    wslTargetName_ = targetName.trimmed();
    wslDistro_ = distro.trimmed();
    wslCondaPath_ = condaPath.trimmed();
    wslEnvironment_ = environment.trimmed();
    wslPythonPath_ = pythonPath.trimmed();
    QSettings settings;
    settings.setValue(QStringLiteral("runtime/wslDistro"), wslDistro_);
    settings.setValue(QStringLiteral("runtime/wslTargetName"), wslTargetName_);
    settings.setValue(QStringLiteral("runtime/wslCondaPath"), wslCondaPath_);
    settings.setValue(QStringLiteral("runtime/wslEnvironment"), wslEnvironment_);
    settings.setValue(QStringLiteral("runtime/wslPythonPath"), wslPythonPath_);
    settings.sync();
    QStringList arguments = {QStringLiteral("target"), QStringLiteral("upsert"), QStringLiteral("--name"), wslTargetName_,
        QStringLiteral("--profile"), QStringLiteral("rknn-host"), QStringLiteral("--transport"), QStringLiteral("wsl"),
        QStringLiteral("--wsl-distro"), wslDistro_, QStringLiteral("--global")};
    if (!wslCondaPath_.isEmpty()) {
        arguments << QStringLiteral("--conda-path") << wslCondaPath_ << QStringLiteral("--conda-env") << wslEnvironment_;
    }
    if (!wslPythonPath_.isEmpty()) {
        arguments << QStringLiteral("--python") << wslPythonPath_;
    }
    runCli(QStringLiteral("保存 WSL / RKNN 环境"), arguments, QDir::currentPath());
}

void AppController::discoverWslEnvironment() {
    if (wslTargetName_.trimmed().isEmpty()) {
        emit bannerRequested(QStringLiteral("请先保存 WSL 目标配置"), QStringLiteral("warning"));
        return;
    }
    runCli(
        QStringLiteral("检查 WSL / RKNN 环境"),
        {QStringLiteral("environment"), QStringLiteral("check"), QStringLiteral("--target"), wslTargetName_, QStringLiteral("--format"), QStringLiteral("json")},
        QDir::currentPath());
}

void AppController::runContractValidation() {
    if (contractPath_.isEmpty()) {
        emit bannerRequested(QStringLiteral("请先选择契约文件"), QStringLiteral("warning"));
        return;
    }
    runCli(QStringLiteral("静态校验"), {QStringLiteral("check-contract"), contractPath_}, QFileInfo(contractPath_).absolutePath());
}

void AppController::runCaptureValidation() {
    if (contractPath_.isEmpty() || fp16ArtifactPath_.isEmpty() || int8ArtifactPath_.isEmpty()) {
        emit bannerRequested(QStringLiteral("需要契约、FP16 artifact 和 INT8 artifact"), QStringLiteral("warning"));
        return;
    }
    runCli(
        QStringLiteral("证据一致性校验"),
        {QStringLiteral("validate-capture"), QStringLiteral("--contract"), contractPath_,
         QStringLiteral("--artifact"), QStringLiteral("rknn-fp16=") + fp16ArtifactPath_,
         QStringLiteral("--artifact"), QStringLiteral("rknn-int8=") + int8ArtifactPath_},
        QFileInfo(contractPath_).absolutePath());
}

void AppController::runModelProbe() {
    if (contractPath_.isEmpty() || modelPath_.isEmpty()) {
        emit bannerRequested(QStringLiteral("需要契约文件和 ONNX 模型"), QStringLiteral("warning"));
        return;
    }
    const QDir modelDirectory = QFileInfo(modelPath_).absoluteDir();
    const QString outputDirectory = modelDirectory.filePath(QStringLiteral("tensorfence-probe"));
    runCli(
        QStringLiteral("模型输出契约探查"),
        {QStringLiteral("probe-model"), QStringLiteral("--model"), modelPath_, QStringLiteral("--contract"), contractPath_,
         QStringLiteral("--out"), outputDirectory},
        modelDirectory.absolutePath());
}

void AppController::runRknnInference() {
    if (contractPath_.isEmpty() || modelPath_.isEmpty() || imagePath_.isEmpty()) {
        emit bannerRequested(QStringLiteral("需要契约、RKNN 模型和测试图片"), QStringLiteral("warning"));
        return;
    }
    if (QFileInfo(modelPath_).suffix().compare(QStringLiteral("rknn"), Qt::CaseInsensitive) != 0) {
        emit bannerRequested(QStringLiteral("执行 RKNN 需要选择 .rknn 模型"), QStringLiteral("warning"));
        return;
    }
    const QDir outputDirectory = QFileInfo(modelPath_).absoluteDir();
    const QString artifact = outputDirectory.filePath(QFileInfo(modelPath_).completeBaseName() + QStringLiteral(".tensorfence-rknn.npz"));
    QStringList arguments = {QStringLiteral("rknn-run"), QStringLiteral("--contract"), contractPath_,
        QStringLiteral("--model"), modelPath_, QStringLiteral("--image"), imagePath_, QStringLiteral("--out"), artifact,
        QStringLiteral("--environment-target"), wslTargetName_, QStringLiteral("--wsl-distro"), wslDistro_};
    if (!wslCondaPath_.isEmpty()) {
        arguments << QStringLiteral("--wsl-conda") << wslCondaPath_ << QStringLiteral("--wsl-env") << wslEnvironment_;
    }
    if (!wslPythonPath_.isEmpty()) {
        arguments << QStringLiteral("--wsl-python") << wslPythonPath_;
    }
    runCli(QStringLiteral("WSL RKNN 推理"), arguments, outputDirectory.absolutePath());
}

void AppController::openReport() {
    if (reportPath_.isEmpty()) {
        emit bannerRequested(QStringLiteral("请先选择报告"), QStringLiteral("warning"));
        return;
    }
    if (!QDesktopServices::openUrl(QUrl::fromLocalFile(reportPath_))) {
        emit bannerRequested(QStringLiteral("无法用系统查看器打开报告"), QStringLiteral("warning"));
        return;
    }
    setStatus(QStringLiteral("已打开报告"), QFileInfo(reportPath_).fileName());
    emit bannerRequested(QStringLiteral("已交给系统查看器：%1").arg(QFileInfo(reportPath_).fileName()), QStringLiteral("success"));
    emit stateChanged();
}

void AppController::notifyUnavailable(const QString &feature) {
    const QString message = QStringLiteral("%1 尚未接入；请先在 WSL 或板端采集 artifact 后导入").arg(feature);
    recentAction_ = feature + QStringLiteral(" 未接入");
    setStatus(feature + QStringLiteral(" 尚未接入"), QStringLiteral("当前仅支持采集产物导入"));
    emit bannerRequested(message, QStringLiteral("warning"));
    emit stateChanged();
}

bool AppController::ensureCliConfigured() {
    if (process_ != nullptr) {
        emit bannerRequested(QStringLiteral("已有诊断任务正在运行"), QStringLiteral("warning"));
        return false;
    }
    if (cliPath_.isEmpty() || !QFileInfo::exists(cliPath_)) {
        emit bannerRequested(QStringLiteral("请在工程环境页选择本机 TensorFence CLI 或 Python"), QStringLiteral("warning"));
        return false;
    }
    return true;
}

void AppController::runCli(const QString &label, const QStringList &arguments, const QString &workingDirectory) {
    if (!ensureCliConfigured()) {
        return;
    }
    const QFileInfo cliInfo(cliPath_);
    QStringList effectiveArguments = arguments;
    const QString executableName = cliInfo.completeBaseName().toLower();
    if (executableName.startsWith(QStringLiteral("python")) || executableName == QStringLiteral("py")) {
        effectiveArguments.prepend(QStringLiteral("tensorfence"));
        effectiveArguments.prepend(QStringLiteral("-m"));
    }

    commandOutput_ = QStringLiteral("$ %1 %2\n").arg(cliPath_, effectiveArguments.join(QLatin1Char(' ')));
    emit commandOutputChanged();
    process_ = new QProcess(this);
    process_->setWorkingDirectory(workingDirectory);
    process_->setProcessChannelMode(QProcess::SeparateChannels);
    connect(process_, &QProcess::readyReadStandardOutput, this, [this]() {
        appendCommandOutput(QString::fromLocal8Bit(process_->readAllStandardOutput()));
    });
    connect(process_, &QProcess::readyReadStandardError, this, [this]() {
        appendCommandOutput(QString::fromLocal8Bit(process_->readAllStandardError()));
    });
    connect(process_, &QProcess::errorOccurred, this, [this, label](QProcess::ProcessError error) {
        appendCommandOutput(process_->errorString() + QLatin1Char('\n'));
        setStatus(label + QStringLiteral(" 启动失败"), process_->errorString());
        emit bannerRequested(label + QStringLiteral(" 启动失败"), QStringLiteral("warning"));
        if (error == QProcess::FailedToStart) {
            workspacePill_ = QStringLiteral("诊断失败");
            process_->deleteLater();
            process_ = nullptr;
            emit stateChanged();
        }
    });
    connect(process_, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
        [this, label](int exitCode, QProcess::ExitStatus exitStatus) {
            appendCommandOutput(QString::fromLocal8Bit(process_->readAllStandardOutput()));
            appendCommandOutput(QString::fromLocal8Bit(process_->readAllStandardError()));
            const bool success = exitStatus == QProcess::NormalExit && exitCode == 0;
            setStatus(success ? label + QStringLiteral(" 完成") : label + QStringLiteral(" 失败"),
                      QStringLiteral("退出码 %1").arg(exitCode));
            workspacePill_ = success ? QStringLiteral("诊断完成") : QStringLiteral("诊断失败");
            emit bannerRequested(success ? label + QStringLiteral(" 完成") : label + QStringLiteral(" 失败"),
                                 success ? QStringLiteral("success") : QStringLiteral("warning"));
            process_->deleteLater();
            process_ = nullptr;
            emit stateChanged();
        });
    recentAction_ = label;
    setStatus(label + QStringLiteral(" 运行中"), QStringLiteral("CLI"));
    workspacePill_ = QStringLiteral("诊断运行中");
    emit bannerRequested(label + QStringLiteral(" 已启动"), QStringLiteral("info"));
    process_->start(cliPath_, effectiveArguments);
    emit stateChanged();
}

void AppController::appendCommandOutput(const QString &text) {
    if (text.isEmpty()) {
        return;
    }
    commandOutput_.append(text);
    emit commandOutputChanged();
}

QString AppController::roleDisplayName(const QString &role) const {
    if (role == QStringLiteral("contract")) {
        return QStringLiteral("契约");
    }
    if (role == QStringLiteral("model")) {
        return QStringLiteral("ONNX 模型");
    }
    if (role == QStringLiteral("fp16")) {
        return QStringLiteral("FP16 证据");
    }
    if (role == QStringLiteral("int8")) {
        return QStringLiteral("INT8 证据");
    }
    if (role == QStringLiteral("report")) {
        return QStringLiteral("诊断报告");
    }
    if (role == QStringLiteral("image")) {
        return QStringLiteral("测试图片");
    }
    return role;
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
