# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'help_gui.ui'
#
# Created by: PyQt5 UI code generator 5.13.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(746, 454)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(9, 9, 731, 33))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setGeometry(QtCore.QRect(9, 48, 731, 221))
        self.label_2.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_2.setWordWrap(True)
        self.label_2.setObjectName("label_2")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "帮助"))
        self.label.setText(_translate("Dialog", "afk-arena-tools 帮助"))
        self.label_2.setText(_translate("Dialog", "<html><head/><body><p>【正在施工中。。。。。。】</p><p>Q：软件如何使用？</p><p>A：直接点对应的按钮即可。</p><p>P.S. 本人是计算机业余爱好者，编程能力有限，出错在所难免，如果有问题可以去项目地址提issue，有能力修复的可以直接提Pull Request。</p><p>软件作者：oscarcx123</p><p>项目地址：<a href=\"https://github.com/oscarcx123/fraction-calc\"><span style=\" text-decoration: underline; color:#0057ae;\">https://github.com/oscarcx123/afk-arena-tools</span></a></p></body></html>"))
