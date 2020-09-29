import time
import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.dates as mdates
import datetime 
import os
import glob
import scipy.io
import argparse

class SerialPlotter():
    def __init__(self, args) -> None:
        plt.style.use('fivethirtyeight')

        self.fig = plt.figure()

        graph_keys = [
            "voltage",
            "current",
            "power"
        ]

        graph_unit = [
            "V",
            "A",
            "W"
        ]

        color = [
            "blue",
            "red",
            "yellow"
        ]

        self.datastore = {
            'time': [],
            'voltage' : [],
            'current' : [],
            'power' : [],
            'capacity': [],
            'temperature' : []
        }

        if(args.file):
            data = self.load_mat(args.file[0])
            for key in self.datastore:
                self.datastore[key] = data[key][0].tolist()

        self.axis = []
        self.line = []

        for i, key in enumerate(graph_keys):
            self.axis.append(self.fig.add_subplot(3,1,i+1))
            self.axis[-1].legend(loc=1)
            self.axis[-1].xaxis_date()
            self.axis[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self.axis[-1].set_ylabel(graph_unit[i])
            line, = self.axis[-1].plot(self.datastore['time'], self.datastore[key],'-',  linewidth=1, color=color[i])
            line.set_label(key)
            self.line.append(line)

        self.axis[2].set_xlabel("Time")
        self.axis[0].set_title('Power Chart')

        self.ser = serial.Serial(
            port='COM13',
            baudrate=9600
        )

        self.ser.isOpen()

        os.chdir("./outputs")
        self.setFileName()

        ani = FuncAnimation(plt.gcf(), self.animate, 1000)
        plt.tight_layout()
        plt.show()

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
            self.success_message('Saved data to out.mat')
        except Exception as e:
            self.error_message('Saving Data ' + str(e))

    def load_mat(self, filename):
        mat = scipy.io.loadmat(filename)
        return mat

    def animate(self, i):
        
        out = []    
        while self.ser.inWaiting() > 0:
            out.append(self.ser.read(1))

        if(len(out) > 32 and out[0] == b'\xff'):
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
            self.datastore['voltage'].append(int.from_bytes(out[5] + out[6], byteorder="big") * 1E-1)
            self.datastore['current'].append(int.from_bytes(out[8] + out[9], byteorder="big") * 1E-3)
            self.datastore['power'].append(self.datastore['voltage'][-1] * self.datastore['current'][-1])
            if(len(self.datastore['capacity']) != 0):
                oldcap = self.datastore['capacity'][-1]
            else:
                oldcap = 0
            self.datastore['capacity'].append(oldcap + self.datastore['power'][-1] * 1)

            zero = datetime.datetime(2000,1,1)
            seconds = int.from_bytes(out[29], byteorder="big")
            minutes = int.from_bytes(out[28], byteorder="big")
            hours = int.from_bytes(out[26] + out[27], byteorder="big")

            dt = datetime.timedelta(hours=hours,minutes=minutes,seconds=seconds)
            tim = zero + dt
            zero = mdates.date2num(zero)
            tim = mdates.date2num(tim)-zero

            self.datastore['time'].append(tim)
            self.datastore['temperature'].append(int.from_bytes(out[25], byteorder="big"))

        # if counter >40:
        #     '''
        #     This helps in keeping the graph fresh and refreshes values after every 40 timesteps
        #     '''
        #     x_values.pop(0)
        #     y_values.pop(0)
        #     #counter = 0
        # clears the values of the graph

        graph_keys = [
            "voltage",
            "current",
            "power"
        ]

        for i, l in enumerate(self.line):
            l.set_data(self.datastore['time'], self.datastore[graph_keys[i]])
            plt.draw()


        time.sleep(.25) # keep refresh rate of 0.25 seconds

        if len(self.datastore['time']) != 0 and len(self.datastore['time'])%60 == 0:
            print("Saved: " + os.getcwd() + '\\' + self.filename)
            scipy.io.savemat(os.getcwd() + '\\' + self.filename, self.datastore)
            self.counter = 0

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-f', "--file", dest="file", type=str, help='.mat filename', nargs=1)
# parser.add_argument('-p', '--plot_type',dest='plot_type', type=str, nargs=1, choices=plot_type)
# parser.add_argument('-c', '--compensate',dest='compensate', type=str, nargs=4, metavar=('marker_1_start', 'marker_1_stop', 'marker_2_start', 'marker_2_stop'))
# parser.add_argument('-f', '--filter',dest='filter', action='store_const', const=True)
# parser.add_argument('-s', '--slice',dest='slice', type=str, nargs=2, metavar=('start','stop'), help='Take a slice')
args = parser.parse_args()

SerialPlotter(args)