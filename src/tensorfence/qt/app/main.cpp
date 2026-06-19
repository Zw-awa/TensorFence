#include <QApplication>
#include <QLabel>

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    QLabel label("TensorFence Qt UI skeleton");
    label.setWindowTitle("TensorFence");
    label.resize(420, 180);
    label.setAlignment(Qt::AlignCenter);
    label.show();

    return app.exec();
}

