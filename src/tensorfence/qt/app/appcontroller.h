#pragma once

#include <QObject>
#include <QProcess>
#include <QString>
#include <QStringList>
#include <QVariantList>

namespace tensorfence::qt {

class AppController : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString currentPage READ currentPage NOTIFY stateChanged)
    Q_PROPERTY(QString currentFocus READ currentFocus NOTIFY stateChanged)
    Q_PROPERTY(QString currentPath READ currentPath NOTIFY stateChanged)
    Q_PROPERTY(QString recentAction READ recentAction NOTIFY stateChanged)
    Q_PROPERTY(QString statusPrimary READ statusPrimary NOTIFY stateChanged)
    Q_PROPERTY(QString statusSecondary READ statusSecondary NOTIFY stateChanged)
    Q_PROPERTY(QString workspacePill READ workspacePill NOTIFY stateChanged)
    Q_PROPERTY(QStringList recentFiles READ recentFiles NOTIFY recentFilesChanged)
    Q_PROPERTY(QString cliPath READ cliPath NOTIFY stateChanged)
    Q_PROPERTY(QString contractPath READ contractPath NOTIFY stateChanged)
    Q_PROPERTY(QString modelPath READ modelPath NOTIFY stateChanged)
    Q_PROPERTY(QString fp16ArtifactPath READ fp16ArtifactPath NOTIFY stateChanged)
    Q_PROPERTY(QString int8ArtifactPath READ int8ArtifactPath NOTIFY stateChanged)
    Q_PROPERTY(QString reportPath READ reportPath NOTIFY stateChanged)
    Q_PROPERTY(QString commandOutput READ commandOutput NOTIFY commandOutputChanged)
    Q_PROPERTY(bool commandRunning READ commandRunning NOTIFY stateChanged)

public:
    explicit AppController(QObject *parent = nullptr);

    QString currentPage() const;
    QString currentFocus() const;
    QString currentPath() const;
    QString recentAction() const;
    QString statusPrimary() const;
    QString statusSecondary() const;
    QString workspacePill() const;
    QStringList recentFiles() const;
    QString cliPath() const;
    QString contractPath() const;
    QString modelPath() const;
    QString fp16ArtifactPath() const;
    QString int8ArtifactPath() const;
    QString reportPath() const;
    QString commandOutput() const;
    bool commandRunning() const;

    Q_INVOKABLE void navigateTo(const QString &pageKey);
    Q_INVOKABLE void activateWorkflow(const QString &workflowId);
    Q_INVOKABLE void handleDroppedUrls(const QVariantList &urls);
    Q_INVOKABLE void openPath(const QString &path);
    Q_INVOKABLE void acknowledgeAction(const QString &label);
    Q_INVOKABLE void setCliPath(const QString &path);
    Q_INVOKABLE void setSessionPath(const QString &role, const QString &path);
    Q_INVOKABLE void runContractValidation();
    Q_INVOKABLE void runCaptureValidation();
    Q_INVOKABLE void runModelProbe();
    Q_INVOKABLE void openReport();
    Q_INVOKABLE void notifyUnavailable(const QString &feature);

signals:
    void stateChanged();
    void recentFilesChanged();
    void commandOutputChanged();
    void bannerRequested(const QString &message, const QString &tone);

private:
    struct RouteInfo {
        QString pageKey;
        QString title;
        QString feedback;
        QString path;
        bool valid = false;
        bool warning = false;
    };

    void setStatus(const QString &primary, const QString &secondary = QString());
    void updateContext(const QString &focus, const QString &path, const QString &action);
    void updateRecentFiles(const QString &path);
    void runCli(const QString &label, const QStringList &arguments, const QString &workingDirectory);
    bool ensureCliConfigured();
    void appendCommandOutput(const QString &text);
    QString roleDisplayName(const QString &role) const;
    RouteInfo routeFile(const QString &path) const;
    bool isSupportedPath(const QString &path) const;

    QString currentPage_ = QStringLiteral("home");
    QString currentFocus_ = QStringLiteral("开始使用");
    QString currentPath_ = QStringLiteral("尚未选择文件");
    QString recentAction_ = QStringLiteral("就绪");
    QString statusPrimary_ = QStringLiteral("就绪");
    QString statusSecondary_;
    QString workspacePill_ = QStringLiteral("待处理");
    QStringList recentFiles_;
    QString cliPath_;
    QString contractPath_;
    QString modelPath_;
    QString fp16ArtifactPath_;
    QString int8ArtifactPath_;
    QString reportPath_;
    QString commandOutput_;
    QProcess *process_ = nullptr;
};

}  // namespace tensorfence::qt
