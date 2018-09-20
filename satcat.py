#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""satcat.py - a simple interface between CAT capable radio and MacDoppler's UDP interface.
   Originally built for Kenwood TH-D7 but readily modifiable for others.

   Only dependency outside of standard Python 2.7 is appJar: http://appjar.info/
   Version: 1.01 - Fixed excessive radio updates
   Version: 1.0

   Copyright (c) 2018 Jeff Karpinski

   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:

   The above copyright notice and this permission notice shall be included in all
   copies or substantial portions of the Software.

   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
   SOFTWARE.   
"""

import socket
import serial
from appJar import gui
from serial.tools.list_ports import comports

#Put radio setup commands here, including setting VFO and power modes.
Radio_Start = [
"DL 1",     #dual band
"DUP 1",    #duplex
"BEP 0",    #no beeps
"VMC 0,0",  #VFO mode band A
"VMC 1,0",  #VFO mode band B
"PC 0,0",   #power high band A
"PC 1,0"    #power high band B
]

#Put radio cleanup commands here.
Radio_Stop = [
"BEP 4",    #beeps on
"SQ 0,04",  #squelch on band A
"SQ 1,04"   #squelch on band B
]

Radio_BandA = "BC 0"       #switch to band A
Radio_BandB = "BC 1"       #switch to band B
Radio_SQonA = "SQ 0,04"    #sqelch on band A
Radio_SQoffA = "SQ 0,00"   #sqelch off band A
Radio_SQonB = "SQ 1,04"    #sqelch on band B
Radio_SQoffB = "SQ 1,00"   #sqelch off band B
Radio_TNCA = "DTB 0"       #data on band A
Radio_TNCB = "DTB 1"       #data on band B

# Tune commands for each band
# $FRQ = 8 digit frequency, leading zero buffered
# $TON = tone on (1) or off (0)
# $CON = CTCSS on (1) or off (0)
# $TFRQ = 2 digit tone index, leading zero buffered
# $CFRQ = 2 digit CTCSS index, leading zero buffered
Radio_TunA = "BUF 0,$FRQ000,0,0,0,$TON,$CON,,$TFRQ,,$CFRQ,000000000,0"
Radio_TunB = "BUF 1,$FRQ000,0,0,0,$TON,$CON,,$TFRQ,,$CFRQ,000000000,0"

UDP_IP = ""                                         #UI field (MacDoppler IP address)
UDP_Port = 9932                                     #UI field (MacDoppler port)
Serial_Port = ""                                    #UI field (serial port of radio)
Uplink_Band = "A"                                   #UI field (radio band to use for uplink)
available_ports = [p.device for p in comports()]    #list of valid com ports for UI
ser = serial.Serial()                               #stand up serial instance to config later
radio_active = 0                                    #boolean to know if radio cleanup is needed 
Tone_Codes = {                                      #tone lookup table for UI
"0":"N/A","1":"67.0","2":"71.9","3":"74.4","4":"77.0","5":"79.7","6":"82.5",
"7":"85.4","8":"88.5","9":"91.5","10":"94.8","11":"97.4","12":"100.0","13":"103.5",
"14":"107.2","15":"110.9","16":"114.8","17":"118.8","18":"123.0","19":"127.3","20":"131.8",
"21":"136.5","22":"141.3","23":"146.2","24":"151.4","25":"156.7","26":"162.2","27":"167.9",
"28":"173.8","29":"179.9","30":"186.2","31":"192.8","32":"203.5","33":"210.7","34":"218.1",
"35":"225.7","36":"233.6","37":"241.8","38":"250.3"
}

def round5(x, base=5):    #TH-D7A can only tune in 5kHz increments
    return int(base * round(float(x)/base))

def launch():    #main process thread
    global radio_active
    radio_active = 1
    lastdata = ""
    app.queueFunction(app.setLabel,"stat","Setup")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_Port))
    ser.baudrate = 9600
    ser.port = Serial_Port
    ser.timeout = 1
    ser.close()
    ser.open()

    for x in Radio_Start:
        ser.write(b''+x+'\r\n')
        read_val = ser.read(size=128)
        print read_val

    if Uplink_Band == "A":
        ser.write(b''+Radio_TNCB+'\r\n')
        read_val = ser.read(size=128)
        print read_val
        ser.write(b''+Radio_SQoffB+'\r\n')
        read_val = ser.read(size=128)
        print read_val
        ser.write(b''+Radio_SQonA+'\r\n')
        read_val = ser.read(size=128)
        print read_val
        ser.write(b''+Radio_BandA+'\r\n')
        read_val = ser.read(size=128)
        print read_val
    else:
        ser.write(b''+Radio_TNCA+'\r\n')
        read_val = ser.read(size=128)
        print read_val
        ser.write(b''+Radio_SQoffA+'\r\n')
        read_val = ser.read(size=128)
        print read_val
        ser.write(b''+Radio_SQonB+'\r\n')
        read_val = ser.read(size=128)
        print read_val
        ser.write(b''+Radio_BandB+'\r\n')
        read_val = ser.read(size=128)
        print read_val

    while True:
        app.queueFunction(app.setLabel,"stat","Listening")
        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        #print "received message:", data
        response = data.strip()
        indx_radio = response.find("Sat Radio Report",0)

        if (indx_radio != -1):
            indx_dfreq = response.find("Down Mhz:",indx_radio)
            indx_dfreq_beg = indx_dfreq+9
            indx_dfreq_end = response.find(",",indx_dfreq_beg)
            indx_dmode = response.find("Down Mode:",indx_radio)
            indx_dmode_beg = indx_dmode+10
            indx_dmode_end = response.find(",",indx_dmode_beg)
            indx_ufreq = response.find("Up MHz:",indx_radio)
            indx_ufreq_beg = indx_ufreq+7
            indx_ufreq_end = response.find(",",indx_ufreq_beg)
            indx_umode = response.find("Up Mode:",indx_radio)
            indx_umode_beg = indx_umode+8
            indx_umode_end = response.find(",",indx_umode_beg)
            indx_tone = response.find("tone:",indx_radio)
            indx_tone_beg = indx_tone+5
            indx_tone_end = response.find(",",indx_tone_beg)
            indx_ctone = response.find("ctone:",indx_radio)
            indx_ctone_beg = indx_ctone+6
            indx_ctone_end = response.find(",",indx_ctone_beg)
            indx_sname = response.find("SatName:",indx_radio)
            indx_sname_beg = indx_sname+8
            indx_sname_end = response.find("]",indx_sname_beg)
            dfreq = response[indx_dfreq_beg:indx_dfreq_end]
            dfreqr = round5(float(dfreq)*1000)
            dmode = response[indx_dmode_beg:indx_dmode_end]
            ufreq = response[indx_ufreq_beg:indx_ufreq_end]
            ufreqr = round5(float(ufreq)*1000)
            umode = response[indx_umode_beg:indx_umode_end]
            tone = response[indx_tone_beg:indx_tone_end]
            ctone = response[indx_ctone_beg:indx_ctone_end]
            sname = response[indx_sname_beg:indx_sname_end]
            newdata = '{:08}'.format(ufreqr)+'{:08}'.format(dfreqr)+tone+ctone

            if newdata != lastdata:
                app.queueFunction(app.setLabel,"stat","Radio")
                lastdata = newdata

                if Uplink_Band == "A":
                    u = Radio_TunA
                    d = Radio_TunB
                else:
                    u = Radio_TunB
                    d = Radio_TunA

                u = u.replace("$FRQ",'{:08}'.format(ufreqr))
                d = d.replace("$FRQ",'{:08}'.format(dfreqr))

                if int(tone) > 0:
                    u = u.replace("$TON","1")
                else:
                    u = u.replace("$TON","0")

                u = u.replace("$CON","0")
                u = u.replace("$CFRQ","01")

                if int(tone) > 1:
                    u = u.replace("$TFRQ",'{:02}'.format(int(tone)+1))  #TH-D7A quirk shifts index up 1>1
                else:
                    u = u.replace("$TFRQ","01")

                if int(ctone) > 0:
                    d = d.replace("$CON","1")
                else:
                    d = d.replace("$CON","0")

                d = d.replace("$TON","0")
                d = d.replace("$TFRQ","01")

                if int(ctone) > 1:
                    d = d.replace("$CFRQ",'{:02}'.format(int(ctone)+1))
                else:
                    d = d.replace("$CFRQ","01")

                ser.write(b''+u+'\r\n')
                read_val = ser.read(size=128)
                print read_val
                ser.write(b''+d+'\r\n')
                read_val = ser.read(size=128)
                print read_val
            app.queueFunction(app.setLabel,"sname",sname)
            app.queueFunction(app.setLabel,"ctone",Tone_Codes.get(ctone))
            app.queueFunction(app.setLabel,"tone",Tone_Codes.get(tone))
            app.queueFunction(app.setLabel,"umode",umode)
            app.queueFunction(app.setLabel,"ufreq",ufreq)
            app.queueFunction(app.setLabel,"dmode",dmode)
            app.queueFunction(app.setLabel,"dfreq",dfreq)
            app.queueFunction(app.setMessage,"dcode",data)

def press(name):    #button event handler
    global UDP_IP
    global UDP_Port
    global Serial_Port
    global Uplink_Band

    if name == "Start":
        UDP_IP = app.getEntry("ip")
        UDP_Port = int(app.getEntry("udp"))
        Serial_Port = app.getOptionBox("port")
        Uplink_Band = app.getOptionBox("ulb")
        app.disableOptionBox("port")
        app.disableEntry("ip")
        app.disableEntry("udp")
        app.disableButton("Start")
        app.disableOptionBox("ulb")
        app.thread(launch)
    else:

        if radio_active:

            for x in Radio_Stop:
                ser.write(b''+x+'\r\n')
                read_val = ser.read(size=128)
                print read_val

            ser.close()
        app.stop()

app = gui("SatCAT")
app.setSize("600x300")
app.addLabel("001","Serial Port",0,0)
app.setLabelAlign("001","right")
app.addOptionBox("port",available_ports,0,1)
app.addLabel("002","MacDoppler IP",1,0)
app.setLabelAlign("002","right")
app.addEntry("ip",1,1)
app.setEntry("ip",UDP_IP)
app.setEntryTooltip("ip","Leave blank for local MacDoppler instance")
app.setEntryMaxLength("ip", 15)
app.addLabel("003","UDP Port#",2,0)
app.setLabelAlign("003","right")
app.addEntry("udp",2,1)
app.setEntry("udp",UDP_Port)
app.setEntryTooltip("udp","Default: 9932")
app.setEntryMaxLength("udp", 5)
app.addLabel("004","Satellite:",0,2)
app.setLabelAlign("004","right")
app.addLabel("sname","None",0,3)
app.setLabelAlign("sname","left")
app.setLabelBg("sname","grey")
app.setLabelRelief("sname","sunken")
app.addLabel("005","Uplink:",1,2)
app.setLabelAlign("005","right")
app.addLabel("ufreq","000.00000",1,3)
app.setLabelBg("ufreq","grey")
app.setLabelRelief("ufreq","sunken")
app.addLabel("umode","FM",1,4)
app.setLabelAlign("umode","left")
app.addLabel("006","Tone:",2,2)
app.setLabelAlign("006","right")
app.addLabel("tone","N/A",2,3)
app.setLabelAlign("tone","right")
app.setLabelBg("tone","grey")
app.setLabelRelief("tone","sunken")
app.addLabel("007","Hz",2,4)
app.setLabelAlign("007","left")
app.addLabel("008","Downlink:",3,2)
app.setLabelAlign("008","right")
app.addLabel("dfreq","000.00000",3,3)
app.setLabelBg("dfreq","grey")
app.setLabelRelief("dfreq","sunken")
app.addLabel("dmode","FM",3,4)
app.setLabelAlign("dmode","left")
app.addLabel("009","CTCSS:",4,2)
app.setLabelAlign("009","right")
app.addLabel("ctone","N/A",4,3)
app.setLabelAlign("ctone","right")
app.setLabelBg("ctone","grey")
app.setLabelRelief("ctone","sunken")
app.addLabel("010","Hz",4,4)
app.setLabelAlign("010","left")
app.addLabel("011","Decode:",4,1)
app.setLabelAlign("011","left")
app.addLabel("012","Radio Uplink Band:",3,0)
app.setLabelAlign("012","right")
app.addOptionBox("ulb",["A","B"],3,1)
app.addMessage("dcode","None",5,1)
app.setMessageAspect("dcode", 200)
app.setMessageBg("dcode","grey")
app.setMessageRelief("dcode","sunken")
app.addButtons(["Start", "Cancel"], press,6,1)
app.addLabel("stat","Idle",6,3)
app.go()
