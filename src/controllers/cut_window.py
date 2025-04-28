import os
import threading
import traceback

from PIL import Image
from PyQt5.QtCore import QPoint, QRect, Qt, QTimer, QSize
from PyQt5.QtGui import QCursor, QPixmap, QPainter, QColor, QFont
from PyQt5.QtWidgets import QDialog, QFileDialog, QPushButton, QVBoxLayout, QLabel, QWidget, QScrollArea, QGridLayout, QSizePolicy
from models.signals import signal
import models.core.file
import models.core.image
import models.core.scraper
from models.base.file import delete_file, split_path
from models.config.config import config
from views.posterCutTool import Ui_Dialog_cut_poster


class DraggableButton(QPushButton):
    def __init__(
        self,
        title,
        parent,
        cutwindow,
    ):
        super().__init__(title, parent)
        self.iniDragCor = [0, 0]
        self.cutwindow = cutwindow

    def mousePressEvent(self, e):
        # self.show_traceback_log("ppp",e.pos())
        self.iniDragCor[0] = e.x()
        self.iniDragCor[1] = e.y()

    def mouseMoveEvent(self, e):
        x = e.x() - self.iniDragCor[0]
        y = e.y() - self.iniDragCor[1]
        cor = QPoint(x, y)
        target = self.mapToParent(cor)
        if target.x() < 0:
            target.setX(0)
        if target.y() < 0:
            target.setY(0)
        self.move(target)  # 需要maptoparent一下才可以的,否则只是相对位置。

        # 更新实际裁剪位置
        self.cutwindow.getRealPos()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.m_drag = False


class CutWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.Ui = Ui_Dialog_cut_poster()  # 实例化 Ui
        self.Ui.setupUi(self)  # 初始化Ui
        self.m_drag = True  # 允许拖动
        self.m_DragPosition = 0  # 拖动位置
        self.show_w = self.Ui.label_backgroud_pic.width()  # 图片显示区域的宽高
        self.show_h = self.Ui.label_backgroud_pic.height()  # 图片显示区域的宽高
        self.keep_side = "height"
        self.pic_new_w = self.show_w
        self.pic_new_h = self.show_h
        self.pic_w = self.show_w
        self.pic_h = self.show_h
        self.Ui.pushButton_select_cutrange = DraggableButton("拖动选择裁剪范围", self.Ui.label_backgroud_pic, self)
        self.Ui.pushButton_select_cutrange.setObjectName("pushButton_select_cutrange")
        self.Ui.pushButton_select_cutrange.setGeometry(QRect(420, 0, 379, 539))
        self.Ui.pushButton_select_cutrange.setCursor(QCursor(Qt.OpenHandCursor))
        self.Ui.pushButton_select_cutrange.setAcceptDrops(True)
        self.Ui.pushButton_select_cutrange.setStyleSheet(
            "background-color: rgba(200, 200, 200, 80);\n"
            "font-size:13px;\n"
            "font-weight:normal;"
            "color: rgba(0, 0, 0, 255);\n"
            "border:2px solid rgba(0, 55, 255, 255);\n"
        )
        self.set_style()
        self.Ui.horizontalSlider_left.valueChanged.connect(self.change_postion_left)
        self.Ui.horizontalSlider_right.valueChanged.connect(self.change_postion_right)
        self.Ui.pushButton_open_pic.clicked.connect(self.open_image)
        self.Ui.pushButton_cut_close.clicked.connect(self.to_cut_and_close)
        self.Ui.pushButton_cut.clicked.connect(self.to_cut)
        self.Ui.pushButton_close.clicked.connect(self.close)
        self.showimage()

    def set_style(self):
        # 控件美化 裁剪弹窗
        self.Ui.widget.setStyleSheet("""
            * {
                font-family: Consolas, 'PingFang SC', 'Microsoft YaHei UI', 'Noto Color Emoji', 'Segoe UI Emoji';
            }
            QPushButton{
                color:black;
                font-size:14px;
                background-color:#CCCCCC;
                border-radius:20px;
                padding: 2px, 2px;
            }
            QPushButton:hover{
                color: white;
                background-color:#4C6EFF;
                font-weight:bold;
            }
            QPushButton:pressed{
                background-color:#4C6EE0;
                border-color:black;
                border-width:12px;
                font-weight:bold;
            }
            QPushButton#pushButton_cut_close{
                color: white;
                font-size:14px;
                background-color:#5E95CC;
                border-radius:25px;
                padding: 2px, 2px;
            }
            QPushButton:hover#pushButton_cut_close{
                color: white;
                background-color:#4C6EFF;
                font-weight:bold;
            }
            QPushButton:pressed#pushButton_cut_close{
                background-color:#4C6EE0;
                border-color:black;
                border-width:14px;
                font-weight:bold;
            }
            """)

    def change_postion_left(self):
        # abc: 0-10000
        abc = self.Ui.horizontalSlider_left.value()
        # 当前裁剪框位置. 左上角坐标 + 尺寸
        x, y, width, height = self.Ui.pushButton_select_cutrange.geometry().getRect()
        height = (abc + 1) / 10000 * self.pic_h
        self.rect_h_w_ratio = height / width  # 更新高宽比
        self.Ui.label_cut_ratio.setText(str(f"{self.rect_h_w_ratio:.2f}"))
        self.Ui.pushButton_select_cutrange.setGeometry(x, y, width, height)  # 显示裁剪框
        self.getRealPos()  # 显示裁剪框实际位置

    def change_postion_right(self):
        abc = self.Ui.horizontalSlider_right.value()
        x, y, width, height = self.Ui.pushButton_select_cutrange.geometry().getRect()
        width = (abc + 1) / 10000 * self.pic_w
        self.rect_h_w_ratio = height / width  # 更新高宽比
        self.Ui.label_cut_ratio.setText(str(f"{self.rect_h_w_ratio:.2f}"))
        self.Ui.pushButton_select_cutrange.setGeometry(x, y, width, height)  # 显示裁剪框
        self.getRealPos()  # 显示裁剪框实际位置

    # 打开图片选择框
    def open_image(self):
        img_path, img_type = QFileDialog.getOpenFileName(
            None, "打开图片", "", "*.jpg *.png;;All Files(*)", options=self.parent().options
        )
        if img_path:
            self.showimage(img_path)

    # 显示要裁剪的图片
    def showimage(self, img_path="", json_data={}):
        # self.Ui.Dialog_cut_poster.setText(' ')                                # 清空背景
        self.Ui.label_backgroud_pic.setText(" ")  # 清空背景

        # 初始化数据
        self.Ui.checkBox_add_sub.setChecked(False)
        self.Ui.radioButton_add_no.setChecked(True)
        self.Ui.radioButton_add_no_2.setChecked(True)
        self.pic_h_w_ratio = 1.5
        self.rect_h_w_ratio = 536.6 / 379  # 裁剪框默认高宽比
        self.show_image_path = img_path
        self.cut_thumb_path = ""  # 裁剪后的thumb路径
        self.cut_poster_path = ""  # 裁剪后的poster路径
        self.cut_fanart_path = ""  # 裁剪后的fanart路径
        self.Ui.label_origin_size.setText(str(f"{str(self.pic_w)}, {str(self.pic_h)}"))  # 显示原图尺寸

        # 获取水印设置
        poster_mark = config.poster_mark
        mark_type = config.mark_type
        pic_name = config.pic_name

        # 显示图片及水印情况
        if img_path and os.path.exists(img_path):
            # 显示背景
            pic = QPixmap(img_path)
            self.pic_w = pic.width()
            self.pic_h = pic.height()
            self.Ui.label_origin_size.setText(str(f"{str(self.pic_w)}, {str(self.pic_h)}"))  # 显示原图尺寸
            self.pic_h_w_ratio = self.pic_h / self.pic_w  # 原图高宽比
            # abc = int((self.rect_h_w_ratio - 1) * 10000)
            # self.Ui.horizontalSlider_left.setValue(abc)  # 裁剪框左侧调整条的值（最大10000）
            # self.Ui.horizontalSlider_right.setValue(10000 - abc)  # 裁剪框右侧调整条的值（最大10000）和左侧的值反过来

            # 背景图片等比缩放并显示
            if self.pic_h_w_ratio <= self.show_h / self.show_w:  # 水平撑满（图片高/宽 <= 显示区域高/显示区域宽）
                self.pic_new_w = self.show_w  # 图片显示的宽度=显示区域宽度
                self.pic_new_h = int(self.pic_new_w * self.pic_h / self.pic_w)  # 计算出图片显示的高度
            else:  # 垂直撑满
                self.pic_new_h = self.show_h  # 图片显示的高度=显示区域高度
                self.pic_new_w = int(self.pic_new_h * self.pic_w / self.pic_h)  # 计算出图片显示的宽度

            pic = QPixmap.scaled(pic, self.pic_new_w, self.pic_new_h, aspectRatioMode=Qt.KeepAspectRatio)  # 图片缩放
            self.Ui.label_backgroud_pic.setGeometry(0, 0, self.pic_new_w, self.pic_new_h)  # 背景区域大小位置设置
            self.Ui.label_backgroud_pic.setPixmap(pic)  # 背景区域显示缩放后的图片

            # 获取nfo文件名，用来设置裁剪后图片名称和裁剪时的水印状态
            img_folder, img_fullname = split_path(img_path)
            img_name, img_ex = os.path.splitext(img_fullname)

            # 如果没有json_data，则通过图片文件名或nfo文件名获取，目的是用来获取水印
            if not json_data:
                # 根据图片文件名获取获取水印情况
                temp_path = img_path
                # 如果图片没有番号信息，则根据nfo文件名获取水印情况
                if "-" not in img_name:
                    file_list = os.listdir(img_folder)
                    for each in file_list:
                        if ".nfo" in each:
                            temp_path = os.path.join(img_folder, each)
                            break
                (
                    json_data,
                    movie_number,
                    folder_old_path,
                    file_name,
                    file_ex,
                    sub_list,
                    file_show_name,
                    file_show_path,
                ) = models.core.file.get_file_info(temp_path, copy_sub=False)

            self.setWindowTitle(json_data.get("number") + " 封面图片裁剪")  # 设置窗口标题

            # 获取水印信息
            has_sub = json_data["has_sub"]
            mosaic = json_data["mosaic"]
            definition = json_data["definition"]

            # 获取裁剪后的的poster和thumb路径
            poster_path = os.path.join(img_folder, "poster.jpg")
            if pic_name == 0:  # 文件名-poster.jpg
                if "-" in img_name:
                    poster_path = (
                        img_path.replace("-fanart", "").replace("-thumb", "").replace("-poster", "").replace(img_ex, "")
                        + "-poster.jpg"
                    )
            thumb_path = poster_path.replace("poster.", "thumb.")
            fanart_path = poster_path.replace("poster.", "fanart.")
            self.cut_thumb_path = thumb_path  # 裁剪后的thumb路径
            self.cut_poster_path = poster_path  # 裁剪后的poster路径
            self.cut_fanart_path = fanart_path  # 裁剪后的fanart路径

            # poster添加水印
            if poster_mark:
                if definition and "hd" in mark_type:
                    if definition == "4K" or definition == "UHD":
                        self.Ui.radioButton_add_4k.setChecked(True)
                    elif definition == "8K" or definition == "UHD8":
                        self.Ui.radioButton_add_8k.setChecked(True)
                if has_sub and "sub" in mark_type:
                    self.Ui.checkBox_add_sub.setChecked(True)
                if mosaic == "有码" or mosaic == "有碼":
                    if "youma" in mark_type:
                        self.Ui.radioButton_add_censored.setChecked(True)
                elif "破解" in mosaic:
                    if "umr" in mark_type:
                        self.Ui.radioButton_add_umr.setChecked(True)
                    elif "uncensored" in mark_type:
                        self.Ui.radioButton_add_uncensored.setChecked(True)
                elif "流出" in mosaic:
                    if "leak" in mark_type:
                        self.Ui.radioButton_add_leak.setChecked(True)
                    elif "uncensored" in mark_type:
                        self.Ui.radioButton_add_uncensored.setChecked(True)
                elif mosaic == "无码" or mosaic == "無碼":
                    self.Ui.radioButton_add_uncensored.setChecked(True)
        # 显示裁剪框
        # 计算裁剪框大小
        if self.pic_h_w_ratio <= 1.5:  # 高宽比小时，固定高度，水平移动
            self.keep_side = "height"
            self.rect_h = self.pic_new_h  # 裁剪框的高度 = 图片缩放显示的高度
            self.rect_w = int(self.rect_h / self.rect_h_w_ratio)  # 计算裁剪框的宽度
            self.rect_x = self.pic_new_w - self.rect_w  # 裁剪框左上角位置的x值
            self.rect_y = 0  # 裁剪框左上角位置的y值
        else:  # 高宽比大时，固定宽度，竖向移动
            self.keep_side = "width"
            self.rect_w = self.pic_new_w  # 裁剪框的宽度 = 图片缩放显示的宽度
            self.rect_h = int(self.rect_w * self.rect_h_w_ratio)  # 计算裁剪框的高度
            self.rect_x = 0  # 裁剪框左上角的x值
            self.rect_y = int((self.pic_new_h - self.rect_h) / 2)  # 裁剪框左上角的y值（默认垂直居中）
        self.Ui.pushButton_select_cutrange.setGeometry(
            QRect(self.rect_x, self.rect_y, self.rect_w, self.rect_h)
        )  # 显示裁剪框
        self.getRealPos()  # 显示裁剪框实际位置

    # 计算在原图的裁剪位置
    def getRealPos(self):
        # 边界处理
        pic_new_w = self.pic_new_w
        pic_new_h = self.pic_new_h
        px, py, pw, ph = self.Ui.pushButton_select_cutrange.geometry().getRect()  # 获取裁剪框大小位置
        pw1 = int(pw / 2)  # 裁剪框一半的宽度
        ph1 = int(ph / 2)  # 裁剪框一半的高度
        if px <= -pw1:  # 左边出去一半
            px = -pw1
        elif px >= pic_new_w - pw1:  # x右边出去一半
            px = pic_new_w - pw1
        if py <= -ph1:  # 上面出去一半
            py = -ph1
        elif py >= pic_new_h - ph1:  # 下面出去一半
            py = pic_new_h - ph1

        # 更新显示裁剪框
        self.Ui.pushButton_select_cutrange.setGeometry(px, py, pw, ph)

        # 计算实际裁剪位置(裁剪时用的是左上角和右下角的坐标)
        if self.keep_side == "height":
            self.c_h = self.pic_h
            self.c_w = self.pic_w * pw / self.pic_new_w
            self.c_x = self.pic_w * px / self.pic_new_w  # 左上角坐标x
            self.c_y = self.pic_w * py / self.pic_new_w  # 左上角坐标y
        else:
            self.c_w = self.pic_w
            self.c_h = self.pic_h * ph / self.pic_new_h
            self.c_x = self.pic_h * px / self.pic_new_h
            self.c_y = self.pic_h * py / self.pic_new_h
        self.c_x2 = self.c_x + self.c_w  # 右下角坐标x
        self.c_y2 = self.c_y + self.c_h  # 右下角坐标y

        # 在原图以外的区域不裁剪
        if self.c_x < 0:
            self.c_w += self.c_x
            self.c_x = 0
        if self.c_y < 0:
            self.c_h += self.c_y
            self.c_y = 0
        if self.c_x2 > self.pic_w:
            self.c_w += self.pic_w - self.c_x2
            self.c_x2 = self.pic_w
        if self.c_y2 > self.pic_h:
            self.c_h += self.pic_h - self.c_y2
            self.c_y2 = self.pic_h

        self.c_x = int(self.c_x)
        self.c_y = int(self.c_y)
        self.c_x2 = int(self.c_x2)
        self.c_y2 = int(self.c_y2)
        self.c_w = int(self.c_w)
        self.c_y = int(self.c_y)

        # 显示实际裁剪位置
        self.Ui.label_cut_postion.setText(f"{str(self.c_x)}, {str(self.c_y)}, {str(self.c_x2)}, {str(self.c_y2)}")

        # 显示实际裁剪尺寸
        self.Ui.label_cut_size.setText(f"{str(self.c_w)}, {str(self.c_h)}")

        return self.c_x, self.c_y, self.c_x2, self.c_y2

    def to_cut_and_close(self):
        t = threading.Thread(target=self.to_cut)
        t.start()
        self.close()

    def to_cut(self):
        img_path = self.show_image_path  # 被裁剪的图片

        # 路径为空时，跳过
        if not img_path or not os.path.exists(img_path):
            return
        thumb_path = self.cut_thumb_path  # 裁剪后的thumb路径
        self.parent().img_path = img_path  # 裁剪后更新图片url，这样再次点击时才可以重新加载并裁剪

        # 读取配置信息
        mark_list = []
        if self.Ui.radioButton_add_4k.isChecked():
            mark_list.append("4K")
        elif self.Ui.radioButton_add_8k.isChecked():
            mark_list.append("8K")
        if self.Ui.checkBox_add_sub.isChecked():
            mark_list.append("字幕")
        if self.Ui.radioButton_add_censored.isChecked():
            mark_list.append("有码")
        elif self.Ui.radioButton_add_umr.isChecked():
            mark_list.append("破解")
        elif self.Ui.radioButton_add_leak.isChecked():
            mark_list.append("流出")
        elif self.Ui.radioButton_add_uncensored.isChecked():
            mark_list.append("无码")

        # 裁剪poster
        try:
            img = Image.open(img_path)
        except:
            self.parent().show_log_text(f"{traceback.format_exc()}\n Open Pic: {img_path}")
            return False
        img = img.convert("RGB")
        img_new_png = img.crop((self.c_x, self.c_y, self.c_x2, self.c_y2))
        try:
            if os.path.exists(self.cut_poster_path):
                delete_file(self.cut_poster_path)
        except Exception as e:
            self.parent().show_log_text(" 🔴 Failed to remove old poster!\n    " + str(e))
            return False
        img_new_png.save(self.cut_poster_path, quality=95, subsampling=0)
        # poster加水印
        if config.poster_mark == 1:
            models.core.image.add_mark_thread(self.cut_poster_path, mark_list)

        # 清理旧的thumb
        if "thumb" in config.download_files:
            if thumb_path != img_path:
                if os.path.exists(thumb_path):
                    delete_file(thumb_path)
                img.save(thumb_path, quality=95, subsampling=0)
            # thumb加水印
            if config.thumb_mark == 1:
                models.core.image.add_mark_thread(thumb_path, mark_list)
        else:
            thumb_path = img_path

        # 清理旧的fanart
        if ",fanart" in config.download_files:
            if self.cut_fanart_path != img_path:
                if os.path.exists(self.cut_fanart_path):
                    delete_file(self.cut_fanart_path)
                img.save(self.cut_fanart_path, quality=95, subsampling=0)
            # fanart加水印
            if config.fanart_mark == 1:
                models.core.image.add_mark_thread(self.cut_fanart_path, mark_list)

        img.close()
        img_new_png.close()

        # 在主界面显示预览
        self.parent().set_pixmap_thread(self.cut_poster_path, thumb_path, poster_from="cut", cover_from="local")
        self.parent().change_to_mainpage.emit("")
        return True

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = e.globalPos() - self.pos()
            self.setCursor(QCursor(Qt.OpenHandCursor))  # 按下左键改变鼠标指针样式为手掌

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.m_drag = False
            self.setCursor(QCursor(Qt.ArrowCursor))  # 释放左键改变鼠标指针样式为箭头

    def mouseMoveEvent(self, e):
        if Qt.LeftButton and self.m_drag:
            if self.m_DragPosition:
                self.move(e.globalPos() - self.m_DragPosition)
                e.accept()


        # self.show_traceback_log('main',e.x(),e.y())
class _ImagePreviewDialog(QDialog):
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setWindowTitle("大图展示")

        layout = QVBoxLayout(self)

        # 加载大图
        self.pixmap = QPixmap(image_path)

        # 创建 QLabel 用于显示图像
        self.image_label = QLabel()
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 获取图片信息
        image_info = f"文件名: {image_path.split('/')[-1]}\n"
        image_info += f"尺寸: {self.pixmap.width()}x{self.pixmap.height()} 像素\n"

        info_label = QLabel(image_info)
        info_label.setAlignment(Qt.AlignCenter)

        # 将图片和信息添加到布局中
        layout.addWidget(self.image_label)
        layout.addWidget(info_label)

        # 设置对话框的最小大小
        self.setMinimumSize(500, 500)  # 设置一个合理的最小尺寸

        # 初始化显示图片
        self.update_image_display()

    def update_image_display(self):
        """根据窗口大小动态更新图片显示"""
        if self.image_label and self.pixmap:
            scaled_pixmap = self.pixmap.scaled(
                self.size().width(),
                self.size().height() - 50,  # 留出空间给信息标签
                Qt.KeepAspectRatio,
            )
            self.image_label.setPixmap(scaled_pixmap)
        signal.close_re_outtime_selected_img.emit()

    def resizeEvent(self, event):
        """当对话框大小改变时保持宽高比并更新图片显示"""
        super(_ImagePreviewDialog, self).resizeEvent(event)
        # 计算新的宽度和高度，保持宽高比
        aspect_ratio = self.pixmap.width() / self.pixmap.height()
        new_width = int(self.size().height() * aspect_ratio)
        new_height = int(self.size().width() / aspect_ratio)

        # 调整窗口大小以保持比例
        if new_width <= self.size().width():
            self.resize(new_width, self.size().height())
        else:
            self.resize(self.size().width(), new_height)

        self.update_image_display()


class _SelectImageData(object):
    select_image_paths = []
    all_images = []


class _ImageLabel(QLabel):
    """自定义标签类，用于显示图像和处理选择状态"""

    image_data: _SelectImageData

    def __init__(
            self,
            image_path,
            image_data: _SelectImageData = _SelectImageData(),
    ):
        super().__init__()
        self.image_data = image_data
        self.image_path = image_path
        self.selected = image_path in image_data.select_image_paths
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                raise ValueError(f"无法加载图片: {image_path}")
            # 获取原始尺寸
            original_width = pixmap.width()
            original_height = pixmap.height()

            # 根据宽高判断缩放比例
            if original_width > original_height:
                # 如果宽度大于高度，将宽度缩放为 100，并按比例计算高度
                scaled_height = int((100 / original_width) * original_height)
                scaled_pixmap = pixmap.scaled(100, scaled_height, Qt.KeepAspectRatio)
                self.setFixedSize(QSize(100, scaled_height))  # 设置固定大小
            else:
                # 如果高度大于或等于宽度，将高度缩放为 100，并按比例计算宽度
                scaled_width = int((100 / original_height) * original_width)
                scaled_pixmap = pixmap.scaled(scaled_width, 100, Qt.KeepAspectRatio)
                self.setFixedSize(QSize(scaled_width, 100))  # 设置固定大小

            # 设置缩放后的图像
            self.setPixmap(scaled_pixmap)
            self.setStyleSheet("border: 1px solid gray;")

            self.mouseDoubleClickEvent = (lambda event, img=image_path: self.show_large_image())
        except Exception as e:
            # print(e)  # 记录错误或显示占位符图片
            # 显示文本提示
            self.setText("无法加载图片")
            self.setStyleSheet("border: 1px solid gray; font-size: 12px; color: red;")

    def paintEvent(self, event):
        """重写绘制事件以添加选中标记"""
        super().paintEvent(event)
        if self.selected:
            painter = QPainter(self)
            # 在右上角绘制背景框
            painter.setPen(QColor(0, 128, 255))
            painter.setBrush(QColor(0, 128, 255, 200))  # 半透明填充
            rect_width = 30
            rect_height = 20
            x_pos = self.width() - rect_width
            y_pos = 0

            painter.drawRect(x_pos, y_pos, rect_width, rect_height)  # 绘制背景框

            # 设置字体并绘制索引
            painter.setPen(QColor(255, 255, 255))  # 白色字体
            painter.setFont(QFont("Arial", 10))  # 字体和大小
            painter.drawText(x_pos + 5, y_pos + 15, str(len(self.image_data.select_image_paths)))  # 从1开始编号
        signal.close_re_outtime_selected_img.emit()

    def mousePressEvent(self, event):
        """处理鼠标按下事件，切换选中状态"""
        if event.button() == Qt.LeftButton:  # 左键点击
            self.toggle_selection()

    def toggle_selection(self):
        """切换选中状态并更新显示"""
        self.selected = not self.selected
        if self.selected:
            self.image_data.select_image_paths.append(self.image_path)
        else:
            self.image_data.select_image_paths.remove(self.image_path)
        signal.close_re_outtime_selected_img.emit()
        self.update()  # 更新界面

    def show_large_image(self):
        """展示大图和基本信息"""
        signal.close_re_outtime_selected_img.emit()
        _ImagePreviewDialog(self.image_path, self).exec()


class ImageSelectionDialog(QDialog):
    _img_data: _SelectImageData = _SelectImageData()

    def __init__(self, images: list[str], title: str = "选择图片", timeout: int = 60 * 1000):
        super().__init__()
        self._img_data.all_images = images
        self._img_data.select_image_paths = []
        self.timeout = timeout
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 300, 300)  # 设置默认窗口尺寸

        self.thumbnail_interval = 10  # 每个缩略图之间的间隔

        # 创建主布局
        main_layout = QVBoxLayout()

        # 图片的缩略图显示区域
        self.thumbnail_area = QScrollArea(self)
        self.thumbnail_area.setWidgetResizable(True)
        self.thumbnail_area.setMinimumHeight(200)  # 最小高度
        self.thumbnail_area.setMinimumWidth(200)  # 最小宽度

        self.thumbnail_widget = QWidget()
        self.thumbnail_layout = QGridLayout(self.thumbnail_widget)  # 使用网格布局
        self.thumbnail_layout.setSpacing(self.thumbnail_interval)  # 设置缩略图间隔
        self.thumbnail_area.setWidget(self.thumbnail_widget)
        main_layout.addWidget(self.thumbnail_area)

        # 创建确认按钮
        confirm_button = QPushButton("确认", self)
        confirm_button.clicked.connect(self.confirm_selection)

        # 添加确认按钮到布局，并减少与缩略图之间的间隔
        main_layout.addWidget(confirm_button, alignment=Qt.AlignRight | Qt.AlignBottom)  # 确认按钮右下对齐

        # 确保缩略图区域能够尽量填满窗口
        # self.resize_event()
        self.setLayout(main_layout)

        # 初始化定时器
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._on_timeout)  # 超时后关闭对话框
        self.start_timer()
        # self.populate_thumbnails()

        # Initialize a timer for debouncing resize events
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.populate_thumbnails)

        signal.close_re_outtime_selected_img.connect(self.reset_timer)

    def resizeEvent(self, event):
        """动态调整缩略图区域的大小"""
        super().resizeEvent(event)
        # width = self.thumbnail_area.width()
        # print("动态调整缩略图区域的大小 width", width)
        # self.populate_thumbnails()
        self.resize_timer.start(200)

    def populate_thumbnails(self):
        # 清空现有布局
        for i in reversed(range(self.thumbnail_layout.count())):
            widget = self.thumbnail_layout.itemAt(i).widget()
            widget.deleteLater()  # 删除控件
        # 获取可用宽度
        all_width = self.thumbnail_area.width()
        for i, image in enumerate(self._img_data.all_images):
            label = _ImageLabel(image, self._img_data)
            label_width = (label.width() if label.width() > 0 else 100)  # 避免为0的情况（初次创建可能为0）
            if label_width <= 0:
                label_width = 100
            images_per_row = max(1, int(all_width / (self.thumbnail_interval + label_width)))
            if images_per_row > len(self._img_data.all_images):
                images_per_row = len(self._img_data.all_images)
            row = i // images_per_row
            col = i % images_per_row
            self.thumbnail_layout.addWidget(label, row, col)

    def confirm_selection(self):
        """处理确认按钮点击事件"""
        # selected_images = [label.image_path for label in self.labels if label.selected]
        # print(f"已选择的图片: {selected_images}")  # 输出已选择的图片路径
        signal.send_ok_select_imgs(self._img_data.select_image_paths)
        self.accept()  # 确认后关闭对话框

    def start_timer(self):
        """启动计时器"""
        self.timer.start(self.timeout)

    def reset_timer(self, selected: bool = False):
        """重置计时器"""
        self.timer.stop()
        self.start_timer()

    def _on_timeout(self):
        # 超时返回所有
        signal.send_ok_select_imgs(self._img_data.all_images)
        self.reject()
