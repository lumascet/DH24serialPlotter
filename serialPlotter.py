from operator import truediv
import time
import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import MultiCursor
import matplotlib.dates as mdates
import datetime 
import numpy as np
import os
import glob
import scipy.io
import argparse
from bisect import bisect_left

class SerialPlotter():
    def __init__(self, args) -> None:
        self.ser = serial.Serial(
            port='COM13',
            baudrate=9600
        )

        self.ser.isOpen()

        plt.style.use('bmh')
        self.fig = plt.figure()

        self.graph_keys = [
            "voltage",
            "current",
            "power"
        ]

        self.graph_unit = [
            "V",
            "A",
            "W"
        ]

        self.graph_color = [
            "blue",
            "red",
            "orange"
        ]

        self.datastore = {
            'time': [],
            'voltage' : [],
            'current' : [],
            'power' : [],
            'capacity': [],
            'energy' : [],
            'temperature' : []
        }

        if(args.file):
            self.data = self.load_mat(args.file[0])
            for key in self.datastore:
                self.datastore[key] = self.data[key][0].tolist()

        while len(self.datastore['time']) == 0:
            self.parseSerial()

        self.lasttriggered = 0
        self.axis = []
        self.line = []
        self.data = []
        self.datalegends = []

        self.data.append(self.datastore['time'])

        for i, key in enumerate(self.graph_keys):
            if(i>0):        
                # all plots share the same x axes, thus during zooming and panning 
                # we will see always the same x section of each graph
                ax = plt.subplot(3, 1, i+1, sharex=ax)             
            else:
                ax = plt.subplot(3, 1, i+1)
            #ax.legend(loc=1)
            ax.xaxis_date()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.set_ylabel(self.graph_unit[i])

            self.axis.append(ax)
            line, = ax.plot(self.datastore['time'], self.datastore[key],'-', linewidth=1, color=self.graph_color[i])

            self.data.append(self.datastore[key])
            #line.set_label(key)
            self.line.append(line)

        self.props = dict(boxstyle='round', edgecolor='black', facecolor='wheat', alpha=1.5)

        self.multi = MultiCursor(self.fig.canvas, self.axis , color='g', lw=1)

        self.fig.canvas.mpl_connect('motion_notify_event', self.show_Legend)

        self.axis[2].set_xlabel("Time")
        self.axis[0].set_title('Power Chart')

        os.chdir("./outputs")
        self.setFileName()

        ani = FuncAnimation(plt.gcf(), self.animate, 1000)
        
        plt.show()

        # exiting
        self.save_mat()

    def setFileName(self):
        self.files= []
        for file in glob.glob("*.mat"):
            self.files.append(file)
        
        i = 0
        while True:
            self.filename = "out_" + time.strftime("%Y-%m-%d_%H-%M-%S") + "_"+ str(i) + ".mat"
            if self.filename not in self.files:
                break
            i += 1

    def save_mat(self):
        try:
            print(os.getcwd() + '\\' + self.filename)
            scipy.io.savemat(os.getcwd() + '\\' + self.filename, self.datastore)
        except Exception as e:
            print('Saving Data ' + str(e))

    def load_mat(self, filename):
        mat = scipy.io.loadmat(filename)
        return mat

    def take_closest(self, myList, myNumber):
        """
        Assumes myList is sorted. Returns closest value to myNumber.

        If two numbers are equally close, return the smallest number.
        """
        pos = bisect_left(myList, myNumber)
        if pos == 0:
            return myList[0]
        if pos == len(myList):
            return myList[-1]
        before = myList[pos - 1]
        after = myList[pos]
        if after - myNumber < myNumber - before:
            return after, pos
        else:
            return before, pos-1


    def show_Legend(self, event): 
        #get mouse coordinates
        mouseXdata = event.xdata

        #10 Hz cooldown
        if(time.time() - self.lasttriggered < 0.5):
            return
        
        self.lasttriggered = time.time()

        if(mouseXdata == None):
            return

        # the value of the closest data point to the current mouse position shall be shown
        closestXValue, posClosestXvalue = self.take_closest(self.data[0], mouseXdata)


        # for d in self.datalegends:
        #     # this remove is required because otherwise after a resizing of the window there is 
        #     # an artifact of the last label, which lies behind the new one
        #     d.remove()
            
        i = 1
        for ax in self.axis:
            datalegend = ax.text(1.05, 0.5, round(self.data[i][posClosestXvalue],2),  fontsize=10,
                                        verticalalignment='top', bbox=self.props, transform=ax.transAxes)               
            ax.draw_artist(datalegend)
            self.datalegends.append(datalegend)
            i +=1

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()




    def animate(self, i):
        
        if(not self.parseSerial()):
            return

        # if counter >40:
        #     '''
        #     This helps in keeping the graph fresh and refreshes values after every 40 timesteps
        #     '''
        #     x_values.pop(0)
        #     y_values.pop(0)
        #     #counter = 0
        # clears the values of the graph

        # for i, key in enumerate(self.graph_keys):
        #     self.axis[i].plot(self.datastore['time'], self.datastore[key],'-', label=self.graph_keys[i],  linewidth=1, color=self.graph_color[i])
        
        for i in range(3):
            self.line.pop(0).remove()

        for i, key in enumerate(self.graph_keys):
            line, = self.axis[i].plot(self.datastore['time'], self.datastore[key],'-',  linewidth=1, color=self.graph_color[i])

            self.line.append(line)
        # for i, l in enumerate(self.line):
        #     l.set_data(self.datastore['time'], self.datastore[self.graph_keys[i]])

        self.fig.canvas.draw()
        # self.fig.canvas.flush_events()


        time.sleep(.25) # keep refresh rate of 0.25 seconds

        if len(self.datastore['time']) != 0 and len(self.datastore['time'])%60 == 0:
            self.save_mat()
            self.counter = 0

    def parseSerial(self):
        out = []    
        while self.ser.inWaiting() > 0:
            out.append(self.ser.read(1))

        if(len(out) > 0):
            while out[0] != b'\xff':
                out.pop(0)
                if(len(out) == 0):
                    break
        if(len(out) >= 32 and out[0] == b'\xff'):
            # for i in range(len(out)):
            #     print(str(i)+"\t", end = '')
            # print("")
            # for i in range(len(out)):
            #     raw = out[i]
            #     print(int.from_bytes(raw, byteorder="big"), end = ',\t')
            # print("")
            # for i in range(len(out)//2):
            #     raw = out[i*2] + out[i*2+1] 
            #     print(int.from_bytes(raw, byteorder="big"), end = ',\t')
            # print("")
            # for i in range(len(out)//2-1):
            #     raw = out[i*2+1] + out[i*2+2] 
            #     print(int.from_bytes(raw, byteorder="big"), end = ',\t')

            zero = datetime.datetime(2000,1,1)
            seconds = int.from_bytes(out[29], byteorder="big")
            minutes = int.from_bytes(out[28], byteorder="big")
            hours = int.from_bytes(out[26] + out[27], byteorder="big")

            dt = datetime.timedelta(hours=hours,minutes=minutes,seconds=seconds)
            tim = zero + dt
            zero = mdates.date2num(zero)
            tim = mdates.date2num(tim)-zero

            if(len(self.datastore['time'])>0 and self.datastore['time'][-1] == tim):
                return False

            self.datastore['time'].append(tim)

            self.datastore['voltage'].append(int.from_bytes(out[5] + out[6], byteorder="big") * 1E-1)
            self.datastore['current'].append(int.from_bytes(out[8] + out[9], byteorder="big") * 1E-3)
            self.datastore['power'].append(self.datastore['voltage'][-1] * self.datastore['current'][-1])
            if(len(self.datastore['capacity']) != 0):
                oldcap = self.datastore['capacity'][-1]
                oldegy = self.datastore['energy'][-1]
            else:
                oldcap = 0
                oldegy = 0
            self.datastore['capacity'].append(oldcap + self.datastore['current'][-1] / 3600)
            self.datastore['energy'].append(oldegy + self.datastore['power'][-1] / 3600)


            self.datastore['temperature'].append(int.from_bytes(out[25], byteorder="big"))

            return True
        return False

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-f', "--file", dest="file", type=str, help='.mat filename', nargs=1)
# parser.add_argument('-p', '--plot_type',dest='plot_type', type=str, nargs=1, choices=plot_type)
# parser.add_argument('-c', '--compensate',dest='compensate', type=str, nargs=4, metavar=('marker_1_start', 'marker_1_stop', 'marker_2_start', 'marker_2_stop'))
# parser.add_argument('-f', '--filter',dest='filter', action='store_const', const=True)
# parser.add_argument('-s', '--slice',dest='slice', type=str, nargs=2, metavar=('start','stop'), help='Take a slice')
args = parser.parse_args()

SerialPlotter(args)