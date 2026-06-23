#pragma once

#include <QObject>
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

    Q_INVOKABLE void navigateTo(const QString &pageKey);
    Q_INVOKABLE void activateWorkflow(const QString &workflowId);
    Q_INVOKABLE void handleDroppedUrls(const QVariantList &urls);
    Q_INVOKABLE void openPath(const QString &path);
    Q_INVOKABLE void acknowledgeAction(const QString &label);

signals:
    void stateChanged();
    void recentFilesChanged();
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
};

}  // namespace tensorfence::qt
