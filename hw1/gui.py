from utils import *
from query import ele_query
from element import *


class Example(QWidget):

    def __init__(self):
        super().__init__()
        self.name_edit = None
        self.elem = None
        self.res2 = QLabel('N/A')
        self.res3 = QLabel('N/A')
        self.res4 = QLabel('N/A')
        self.res5 = QLabel('N/A')
        self.res6 = QLabel('N/A')
        self.res7 = QLabel('N/A')
        self.res8 = QLabel('N/A')
        self.res9 = QLabel('N/A')
        self.res10 = QLabel('N/A')
        self.res11 = QLabel('N/A')
        self.res12 = QLabel('N/A')
        self.res13 = QLabel('N/A')
        self.state = QLabel('请输入')
        self.initUI()

    def initUI(self):
        grid = QGridLayout()
        # grid.setSpacing(100)
        ok_button = QPushButton('确认')
        label1 = QLabel('请输入元素名,中文名或元素符号均可以')
        ok_button.clicked.connect(self.getinfo)
        self.name_edit = QLineEdit()
        grid.addWidget(label1, 1, 0)
        grid.addWidget(ok_button, 2, 1)
        grid.addWidget(self.name_edit, 2, 0)

        label2 = QLabel('元素名称')
        label3 = QLabel('元素序数')
        label4 = QLabel('元素重量')
        label5 = QLabel('熔点')
        label6 = QLabel('沸点')
        label7 = QLabel('地壳占比')
        label8 = QLabel('流星占比')
        label9 = QLabel('海洋占比')
        label10 = QLabel('太阳占比')
        label11 = QLabel('宇宙占比')
        label12 = QLabel('发现时间')
        label13 = QLabel('化合物')
        label_state = QLabel('状态')

        grid.addWidget(label2, 4, 0)
        grid.addWidget(label3, 5, 0)
        grid.addWidget(label4, 6, 0)
        grid.addWidget(label5, 7, 0)
        grid.addWidget(label6, 8, 0)
        grid.addWidget(label7, 9, 0)
        grid.addWidget(label8, 10, 0)
        grid.addWidget(label9, 11, 0)
        grid.addWidget(label10, 12, 0)
        grid.addWidget(label11, 13, 0)
        grid.addWidget(label12, 14, 0)
        grid.addWidget(label13, 15, 0)
        grid.addWidget(label_state, 3, 0)

        grid.addWidget(self.res2, 4, 1)
        grid.addWidget(self.res3, 5, 1)
        grid.addWidget(self.res4, 6, 1)
        grid.addWidget(self.res5, 7, 1)
        grid.addWidget(self.res6, 8, 1)
        grid.addWidget(self.res7, 9, 1)
        grid.addWidget(self.res8, 10, 1)
        grid.addWidget(self.res9, 11, 1)
        grid.addWidget(self.res10, 12, 1)
        grid.addWidget(self.res11, 13, 1)
        grid.addWidget(self.res12, 14, 1)
        grid.addWidget(self.res13, 15, 1)
        grid.addWidget(self.state, 3, 1)

        self.setLayout(grid)
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('元素性质查询器')
        self.show()

    def getinfo(self):
        self.state.setText("查询中")
        QApplication.processEvents()
        try:
            self.elem = ele_query(self.name_edit.text())
        except:
            self.state.setText('元素姓名不匹配')
        else:
            self.state.setText("查询成功")
            self.res2.setText(self.elem.name)
            self.res3.setText(self.elem.number)
            self.res4.setText(self.elem.weight+"u")
            if self.elem.melting_point == 'N/A':
                self.res5.setText('N/A')
            else:
                melting_point = str(float(self.elem.melting_point)-273.15)
                self.res5.setText(melting_point + "°C" if len(melting_point) < 10 else "{:.2f}".format(float(melting_point)) + "°C")
            boiling_point = str(float(self.elem.boiling_point)-273.15)
            self.res6.setText(boiling_point+"°C" if len(boiling_point) < 10 else "{:.2f}".format(float(boiling_point))+"°C")
            self.res7.setText(self.elem.crust+"%")
            if self.elem.meteor == 'N/A':
                self.res8.setText('N/A')
            else:
                self.res8.setText(self.elem.meteor+"%")
            self.res9.setText(self.elem.ocean+"%")
            self.res10.setText(self.elem.solar+"%")
            self.res11.setText(self.elem.universe+"%")
            self.res12.setText('公元'+self.elem.discover+'年' if self.elem.discover[0] != '-' else '公元前'+self.elem.discover[1:]+'年')
            self.res13.setText(','.join(self.elem.compound))


def main():
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
