# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'about_gui.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(495, 369)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(9, 9, 481, 33))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setGeometry(QtCore.QRect(9, 48, 481, 301))
        self.label_2.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_2.setWordWrap(True)
        self.label_2.setObjectName("label_2")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "关于"))
        self.label.setText(_translate("Dialog", "afk-arena-tools V1.0.7"))
        self.label_2.setText(_translate("Dialog", "<html><head/><body><p>这是关于AFK Arena游戏的一个辅助工具。</p><p>本工具并不涉及任何游戏内容的修改，仅仅是模拟人类进行一些比较花时间的操作，因此想着这是一个外挂的用户可以退散了。</p><p>本软件使用PyQt5制作，GUI设计使用了Qt Designer。</p><p>本软件的开源协议是BSD。</p><p>软件作者：oscarcx123</p><p>项目地址：<a href=\"https://github.com/oscarcx123/fraction-calc\"><span style=\" text-decoration: underline; color:#0057ae;\">https://github.com/oscarcx123/afk-arena-tools</span></a></p><p>既然都看到这里了，不如给项目star一下呗～</p><p><br/></p><p><br/></p></body></html>"))
