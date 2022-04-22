import os
# import assets_qrc
# from random import randint
from PyQt5.QtWidgets import QFileDialog, QMainWindow,QApplication,QTableWidgetItem,QMessageBox,QHeaderView
from PyQt5 import uic
from PyQt5.QtCore import Qt,QThread,pyqtSignal, QTimer,QDate,QTime,QObject
from PyQt5.QtGui import QRegion,QGuiApplication
import xlsxwriter as xlsx
import socket
import sys
from datetime import datetime
import pyqtgraph as pg
from lib.asyncSleep import delay
from collections import deque
from lib.MultiGas import DFRobot_MultiGasSensor_I2C
from model import Sensor,creat_table,db_close
import smbus
view_path = 'main.ui'
application_path =os.path.dirname(os.path.abspath(__file__)) 
curren_path = os.path.join(application_path,os.pardir)

CHECK_INTERVAL = 1500
INTERNET_INTERVAL = 5000
SENSOR_INTERVAL = 5000
SO2_ADDRESS = 0x74
NO2_ADDRESS = 0x75
CO_ADDRESS = 0x76
#set up i2c 

def convertTime(time):
    t = datetime.fromtimestamp(time)
    # print(time)
    return t.strftime(' %d/%m/%Y %H:%M:%S')
def checkInternet():
    host='1.1.1.1'
    port = 53
    timeout = 3
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return 1
    except socket.error:
        return 0

def checkDevice(bus,device):
    try:
        bus.read_byte(device)
        return 1
    except Exception as ex: # exception if read_byte fails
        print(ex)
        return 0

class TimeAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLabel(text='Thời gian', units=None)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%H:%M:%S") for value in values]
class sensorThread(QThread):
    updateDt = pyqtSignal(object)
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threadActive = True
        self.interval = SENSOR_INTERVAL
        self.steps = self.interval/10
        bus= smbus.SMBus(1)
        self.SO2 = DFRobot_MultiGasSensor_I2C(SO2_ADDRESS,bus)
        self.NO2 = DFRobot_MultiGasSensor_I2C(NO2_ADDRESS,bus)
        self.CO = DFRobot_MultiGasSensor_I2C(CO_ADDRESS,bus)
        

    def readSensor(self,sensor):
        i=0
        res=-1
        while i<=4:
            res= sensor.read_gas_concentration()
            delay(0.1)
            if res==-1:
                i=i+1
            else:
                break
        return float(res)
    def run(self):
        while (False == self.SO2.change_acquire_mode(self.SO2.PASSIVITY)):
            print("wait So2 acquire mode success!")
            delay(0.5)
        print("change SO2 mode success!")
        while (False == self.NO2.change_acquire_mode(self.NO2.PASSIVITY)):
            print("wait No2 acquire mode success!")
            delay(0.5)
        print("change NO2 mode success!")
        while (False == self.CO.change_acquire_mode(self.CO.PASSIVITY)):
            print("wait Co2 acquire mode success!")
            delay(0.5)
        print("change CO mode success!")
        self.SO2.set_temp_compensation(self.SO2.ON)
        self.NO2.set_temp_compensation(self.NO2.ON)
        self.CO.set_temp_compensation(self.CO.ON)
        delay(1)
        while self.threadActive == True:
            so2 = round(self.readSensor(self.SO2),2)
            co = round(self.readSensor(self.CO),2)
            no2 = round(self.readSensor(self.NO2),2)
            dt ={
                'so2':so2,
                'co':co,
                'no2':no2,
                'time':int(datetime.now().timestamp())
            }
            self.updateDt.emit(dt)
            i=0
            while i<self.steps and self.threadActive == True:
                i=i+1
                self.msleep(10)
    def stop(self):
        self.threadActive = False
        self.terminate()
        self.wait()

class internetThread(QThread):
    updateStatus = pyqtSignal(int)
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threadActive = True
        self.interval = INTERNET_INTERVAL
        self.steps = self.interval/10
        
    def run(self):
        while self.threadActive == True:
            internet_status = checkInternet()
            self.updateStatus.emit(internet_status)
            i=0
            while i<self.steps and self.threadActive == True:
                i=i+1
                self.msleep(10)
    def stop(self):
        self.threadActive = False
        self.terminate()
        self.wait()

class checkThread(QThread):
    updateStatus = pyqtSignal(object)
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threadActive = True
        self.interval = INTERNET_INTERVAL
        self.steps = self.interval/10
        self.bus = smbus.SMBus(1)
        
    def run(self):
        while self.threadActive == True:
            so2 = checkDevice(self.bus,SO2_ADDRESS)
            no2 = checkDevice(self.bus,NO2_ADDRESS)
            co = checkDevice(self.bus,CO_ADDRESS)
            dt={
                'so2':so2,
                'no2':no2,
                'co':co
            }
            self.updateStatus.emit(dt)
            i=0
            while i<self.steps and self.threadActive == True:
                i=i+1
                self.msleep(10)
    def stop(self):
        self.threadActive = False
        self.terminate()
        self.wait()


class Main(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(view_path,self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showMaximized()
        self.stackedWidget.setCurrentIndex(0)

        self.query = None
        self.queryResult = None
        self.pageResult = 0
        self.totalPage = 0
        self.numItem = 20
        self.bus =smbus.SMBus(1)
        self.maxRows =20
        self.maxLen=80
        self.internetStatus = 0
        self.listSensorStatus = [0]*3
        self.startSensor = False

        

        #init event button
        self.btn_home.clicked.connect(self.goHome)
        self.btn_graph.clicked.connect(self.goGraph)
        self.btn_history.clicked.connect(self.goHistory)
        self.btn_exit.clicked.connect(self.goClose)

        self.btn_search.clicked.connect(self.searchData)
        self.btn_export.clicked.connect(self.exportData)
        self.btn_next.clicked.connect(self.nextQuery)
        self.btn_prev.clicked.connect(self.prevQuery)

        #init table
        header1= self.tableSensor.horizontalHeader()
        header1.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header1.setSectionResizeMode(1, QHeaderView.Stretch)
        header1.setSectionResizeMode(2, QHeaderView.Stretch)
        header1.setSectionResizeMode(3, QHeaderView.Stretch)

        header2= self.tableSensor_2.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.Stretch)
        header2.setSectionResizeMode(1, QHeaderView.Stretch)
        header2.setSectionResizeMode(2, QHeaderView.Stretch)
        header2.setSectionResizeMode(3, QHeaderView.Stretch)

        #set up graph
        self.time_arr=deque([])
        self.so2_arr=deque([])
        self.no2_arr=deque([])
        self.co_arr=deque([])
        pg.setConfigOption('foreground', 'k')
        pen1 = pg.mkPen(color=(255, 0, 0))
        pen2 = pg.mkPen(color=(0, 255, 0))
        pen3 = pg.mkPen(color=(0, 0, 255))

        self.graphSensor = pg.PlotWidget(title='Đồ thị SO2,NO2,CO',axisItems={'bottom': TimeAxisItem(orientation='bottom')},left=u'Giá trị cảm biến')
        self.graphSensor.addLegend()
        self.graphSensor.setYRange(-1, 100)
        self.graphSensor.setMenuEnabled(False)
        self.graphSensor.setBackground('w')
        self.line_so2 = self.graphSensor.plot(self.time_arr,self.so2_arr,pen=pen1,symbol='o', symbolSize=5, symbolBrush=('r'),name='SO2')
        self.line_no2 = self.graphSensor.plot(self.time_arr,self.no2_arr,pen=pen2,symbol='o', symbolSize=5, symbolBrush=('g'),name='NO2')
        self.line_co = self.graphSensor.plot(self.time_arr,self.co_arr,pen=pen3,symbol='o', symbolSize=5, symbolBrush=('b'),name='CO')
           
        self.horizontalLayout_9.addWidget(self.graphSensor)

        #init qDateEdit
        now = datetime.now()
        qdate = QDate(now.year,now.month,now.day)
        qtime = QTime(now.hour,now.minute,now.second)
        self.date_start.setMaximumDate(qdate)
        self.date_end.setMaximumDate(qdate)
        self.date_start.setDate(qdate)
        self.date_start.setTime(qtime)
        self.date_end.setTime(qtime)
        self.date_end.setDate(qdate)
        
        #set up timer for showwing datetime
        self.timer=QTimer()
        self.timer.timeout.connect(self.showTime)
        self.timer.start(1000)

        #set up timer for heating sensor
        self.initSensor=QTimer()
        self.initSensor.timeout.connect(self.stopInit)
        self.initSensor.start(3*60*1000)

        #set up thread internet
        self.readInternet = internetThread(self)
        self.readInternet.updateStatus.connect(self.updateInternet)
        self.readInternet.start()

        #set up thread reading status sensor
        self.readStatus = checkThread(self)
        self.readStatus.updateStatus.connect(self.updateStatus)
        self.readStatus.start()

        #set up thread reading sensor data
        self.readSensor = sensorThread(self)
        self.readSensor.updateDt.connect(self.updateSensor)
        # self.readSensor.start()

        self.show()


        

    
    # event button
    def goHome(self):
        self.stackedWidget.setCurrentIndex(0)
    
    def goGraph(self):
        self.stackedWidget.setCurrentIndex(1)
    
    def goHistory(self):
        self.stackedWidget.setCurrentIndex(2)
    
    def goClose(self):
        
        self.close()
    
    def searchData(self):
        startDate = self.date_start.date()
        startTime = self.date_start.time()
        endDate = self.date_end.date()
        endTime = self.date_end.time()

        startQuery = int(datetime(startDate.year(),startDate.month(),startDate.day(),startTime.hour(),startTime.minute(),startTime.second()).timestamp())
        endQuery = int(datetime(endDate.year(),endDate.month(),endDate.day(),endTime.hour(),endTime.minute(),endTime.second()).timestamp())
        # print(startQuery,endQuery)
        try:
            self.query= Sensor.select().where(Sensor.time.between(startQuery,endQuery))
            numData = self.query.count()

            #detete all data from table
            model =  self.tableSensor_2.model()
            model.removeRows(0,model.rowCount())

            if numData ==0:
                self.pageResult =0
                self.totalPage = 0
                self.lb_pagi.setText('0/0')
                return QMessageBox.information(self, 'Thông báo', 'Không có dữ liệu cảm biến!', QMessageBox.Ok)
            else:
                self.pageResult = 1
                self.totalPage = int(numData/self.numItem)+1

                self.lb_pagi.setText(str(self.pageResult)+"/"+str(self.totalPage))

                if self.pageResult == self.totalPage:
                    self.btn_next.setEnabled(False)
                else:
                    self.btn_next.setEnabled(True)
                
                self.queryResult = self.query.paginate(self.pageResult, self.numItem)
                # print(self.queryResult)
                for item in self.queryResult:
                    rowData= [convertTime(item.time),item.so2,item.no2,item.co]
                    self.insertRow(self.tableSensor_2,rowData)

        except Exception as ex:
            print(ex)
    
    def nextQuery(self):
        self.pageResult = self.pageResult +1
        self.btn_prev.setEnabled(True)
        if self.pageResult ==self.totalPage:
            self.btn_next.setEnabled(False)
        self.lb_pagi.setText(str(self.pageResult)+"/"+str(self.totalPage))
        try:
            self.queryResult = self.query.paginate(self.pageResult, self.numItem)
            model =  self.tableSensor_2.model()
            model.removeRows(0,model.rowCount())
            for item in self.queryResult:
                rowData= [convertTime(item.time),item.so2,item.no2,item.co]
                self.insertRow(self.tableSensor_2,rowData)
        except Exception as ex:
            print(ex)
    
    def prevQuery(self):
        self.pageResult = self.pageResult -1
        if self.pageResult==0:
            self.pageResult = 1
        self.btn_next.setEnabled(True)
        if self.pageResult ==1:
            self.btn_prev.setEnabled(False)
        self.lb_pagi.setText(str(self.pageResult)+"/"+str(self.totalPage))
        try:
            self.queryResult = self.query.paginate(self.pageResult, self.numItem)
            model =  self.tableSensor_2.model()
            model.removeRows(0,model.rowCount())
            for item in self.queryResult:
                rowData= [convertTime(item.time),item.so2,item.no2,item.co]
                self.insertRow(self.tableSensor_2,rowData)
        except Exception as ex:
            print(ex)

    def exportData(self):
        # print('export data!',self.query)
        if self.query != None and len(self.query)>0:
            
            headerRow =["STT","Thời gian","Giá trị SO2(ppml)","Giá trị NO2(ppm)","Giá trị CO(ppm)"]
            options = QFileDialog.Options()
            options |=QFileDialog.DontUseNativeDialog
                # options |= QFileDialog.use
            fileName, _ = QFileDialog.getSaveFileName(self,"Lưu file",curren_path,"Excel file (*.xlsx)", options=QFileDialog.DontUseNativeDialog)
            if fileName:
                try:
                    if str(fileName).find('.xlsx') <0:
                        fileName = fileName + '.xlsx'
                    workbook = xlsx.Workbook(fileName)
                    worksheet = workbook.add_worksheet()
                    bold = workbook.add_format({'bold': True,'text_wrap': True})
                    bold.set_align('vcenter')
                    content = workbook.add_format({'text_wrap': True})
                    content.set_align('vcenter')
                    content.set_align('hcenter')

                    # add column data
                    col=0
                    for item in headerRow:
                        worksheet.write(0,col,item,bold)
                        col = col+1
                    
                    # add data
                    row=1
                    for item in self.query:
                        worksheet.write(row,0,row,content)
                        worksheet.write(row,2,item.so2,content)
                        worksheet.write(row,3,item.no2,content)
                        worksheet.write(row,4,item.co,content)
                        worksheet.write(row,1,convertTime(item.time),content)
                        row = row+1
                    
                    workbook.close()

                    QMessageBox.information(self, 'Thông báo', 'Xuất dữ liệu cảm biến thành công!', QMessageBox.Ok)
                except Exception as ex:
                    print("error export BN file:",ex)
                    QMessageBox.warning(self, 'Thông báo', 'Xuât dữ liệu cảm biến thất bại!', QMessageBox.Ok)
        else:
            return QMessageBox.warning(self, 'Thông báo', 'Không có dữ liệu để xuất file!', QMessageBox.Ok)


    
    
    


    # event from threads
    def updateSensor(self,dt):
        print('sensor data:',dt)
        
        if len(self.time_arr)>self.maxLen:
            self.time_arr.popleft()
            self.so2_arr.popleft()
            self.no2_arr.popleft()
            self.co_arr.popleft()
        self.time_arr.append(dt['time'])
        self.so2_arr.append(dt['so2'])
        self.no2_arr.append(dt['no2'])
        self.co_arr.append(dt['co'])

        #update graph
        self.line_so2.setData(self.time_arr,self.so2_arr)
        self.line_no2.setData(self.time_arr,self.no2_arr)
        self.line_co.setData(self.time_arr,self.co_arr)

        #update table
        count = self.tableSensor.rowCount()
        now = convertTime(dt['time'])
        rowData =[now,str(dt['so2']),str(dt['no2']),str(dt['co'])]
        if count>self.maxRows:
            self.tableSensor.removeRow(count-1)
        self.insertFirstRow(self.tableSensor,rowData)  

        if self.lb_so2.text()!=str(dt['so2']):
            self.lb_so2.setText(str(dt['so2']))
        if self.lb_no2.text()!=str(dt['no2']):
            self.lb_no2.setText(str(dt['no2']))
        if self.lb_co.text()!=str(dt['co']):
            self.lb_co.setText(str(dt['co']))
        #update database 
        try:
            Sensor.create(so2=dt['so2'],no2=dt['no2'],co=dt['co'],time = dt['time'])
        except Exception as ex:
            print(ex)

    def updateInternet(self,dt):
        # print('internet:',dt)
        if self.internetStatus==dt:
            return
        self.internetStatus=dt
        if dt==1:
            self.frameInternet.setToolTip('Đang kết nối')
            self.lb_internet.setStyleSheet("background-color: rgb(0, 255, 0);border-radius:8px;")
        else:
            self.frameInternet.setToolTip('Mất kết nối')
            self.lb_internet.setStyleSheet("background-color: rgb(255,0, 0);border-radius:8px;")

    def updateStatus(self,dt):
        # print('status:',dt)
        if self.startSensor == False:
            return
        so2_status = dt['so2']
        no2_status = dt['no2']
        co_status = dt['co']
 
        if self.listSensorStatus[0]!=so2_status:
            self.listSensorStatus[0]=so2_status
            if so2_status==1:
                self.lb_so2_status.setText("Đang kết nối")
                self.lb_so2_status.setStyleSheet("background-color: white;border: 2px solid #a7da46;border-radius:10px;color: rgb(0, 170, 0);")
            else:
                self.lb_so2_status.setText("Ngắt kết nối")
                self.lb_so2_status.setStyleSheet("background-color: white;border: 2px solid #a7da46;border-radius:10px;color: rgb(255,0, 0);")
        
        if self.listSensorStatus[1]!=no2_status:
            self.listSensorStatus[1]=no2_status
            if no2_status ==1:
                self.lb_no2_status.setText("Đang kết nối")
                self.lb_no2_status.setStyleSheet("background-color: white;border: 2px solid #a7da46;border-radius:10px;color: rgb(0, 170, 0);")
            else:
                self.lb_no2_status.setText("Ngắt kết nối")
                self.lb_no2_status.setStyleSheet("background-color: white;border: 2px solid #a7da46;border-radius:10px;color: rgb(255,0, 0);")

        if self.listSensorStatus[2]!=co_status:
            self.listSensorStatus[2]=co_status
            if co_status ==1:
                self.lb_co_status.setText("Đang kết nối")
                self.lb_co_status.setStyleSheet("background-color: white;border: 2px solid #a7da46;border-radius:10px;color: rgb(0, 170, 0);")
            else:
                self.lb_co_status.setText("Ngắt kết nối")
                self.lb_co_status.setStyleSheet("background-color: white;border: 2px solid #a7da46;border-radius:10px;color: rgb(255,0, 0);")



    # timer event
    def showTime(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.lb_datetime.setText(now)
    
    def stopInit(self):
        self.initSensor.stop()
        self.readSensor.start()
        self.startSensor = True

    #table handle func
    def insertRow(self,table,row_data):
        col=0
        row = table.rowCount()
        table.insertRow(row)
        for item in row_data:
            cell = QTableWidgetItem(str(item))
            cell.setTextAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
            table.setItem(row,col,cell)
            col+=1
    
    def insertFirstRow(self,table,row_data):
        col=0
        row = 0
        table.insertRow(row)
        for item in row_data:
            cell = QTableWidgetItem(str(item))
            cell.setTextAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
            table.setItem(row,col,cell)
            col+=1
    

    #close event
    def closeEvent(self,QCloseEvent):
        self.readSensor.stop()
        self.readStatus.stop()
        self.readInternet.stop()
        self.timer.stop()
        self.initSensor.stop()
        db_close()
        print('close app!')
        
    

def handleVisibleChanged():
    if not QGuiApplication.inputMethod().isVisible():
        return
    for w in QGuiApplication.allWindows():
        if w.metaObject().className() == "QtVirtualKeyboard::InputView":
            keyboard = w.findChild(QObject, "keyboard")
            if keyboard is not None:
                r = w.geometry()
                r.moveTop(int(keyboard.property("y")))
                w.setMask(QRegion(r))
                return

if __name__ == "__main__":
    creat_table()
    # os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    app = QApplication(sys.argv)
    # QGuiApplication.inputMethod().visibleChanged.connect(handleVisibleChanged)
    # window = Home("s")
    # window.show()
    win = Main()
    # win.show()
    app.exec_()
    