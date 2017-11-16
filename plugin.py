"""
<plugin key="AAPIPModule" name="Crow Runner Alarm" author="febalci" version="1.0.9">
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="192.168.1.55"/>
        <param field="Port" label="Port" width="50px" required="true" default="5002"/>
        <param field="Mode2" label="STATUS Poll Period" width="40px" required="true" default="60"/>
		<param field="Mode3" label="PIR Sensors seperated by (,)" width="240px" required="true" default="1,5,6"/>
        <param field="Mode4" label="Disarm Code" width="50px" required="true" default="0000"/>		
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
# Add ZO UpdateDevice on ZA
# Add ZC UpdateDevice on ZR
# Commented out EAA, since IP Module still sends DA while in EAA

import Domoticz

class BasePlugin:
    STATUSMESSAGE = b"STATUS \r\n"
    DISARMMESSAGE = None
    ARMMESSAGE = b"ARM \r\n"
    STAYMESSAGE = b"STAY \r\n"
    telnetConn = None
    pirsensors = None
    nextConnect = 3
    oustandingPings = 0

    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        global pirsensors
        global DISARMMESSAGE
		
        if (Parameters["Mode6"] == "Debug"):
            Domoticz.Debugging(1)

        if (len(Devices) == 0):
            pirsensors = [int (x) for x in Parameters["Mode3"].split(',')]
            for zone in range(1,17): #For 16 Zones
                if zone in pirsensors: #PIR Sensor
                    Domoticz.Device(Name="Zone "+str(zone), Unit=zone, TypeName="Switch", Switchtype=8).Create()
                else: #Door Contact
                    Domoticz.Device(Name="Zone "+str(zone), Unit=zone, TypeName="Switch", Switchtype=11).Create()
            self.SourceOptions = {"LevelActions": "||","LevelNames": "Disarm|Stay|Arm","LevelOffHidden": "false","SelectorStyle": "1"}
            Domoticz.Device(Name="Arm/Disarm", Unit=99, TypeName="Selector Switch", Switchtype=18, Image=13, Options=self.SourceOptions).Create()
            Domoticz.Device(Name="AlarmStatus", Unit=17, TypeName="Text").Create()

        Domoticz.Debug("Device created.")
        DumpConfigToLog()
		
        Disarmtemp = "KEYS "+Parameters["Mode4"]+"E\r\n"
        DISARMMESSAGE = Disarmtemp.encode()

        self.telnetConn = Domoticz.Connection(Name="Telnet", Transport="TCP/IP", Protocol="Line", Address=Parameters["Address"], Port=Parameters["Port"])
        self.telnetConn.Connect()
        Domoticz.Heartbeat(int(Parameters["Mode2"]))

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")
        for zonereset in range(1,17): #Reset All Switches on Connect
            UpdateDevice(zonereset,0,"False")
        UpdateDevice(17,0,"0")

        if (Status == 0):
            self.isConnected = True
            self.telnetConn.Send(Message=self.STATUSMESSAGE, Delay=0)
            Domoticz.Debug("Connected successfully to: "+Parameters["Address"]+":"+Parameters["Port"])

        else:
            self.isConnected = False
            Domoticz.Debug("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+Parameters["Port"]+" with error: "+Description)
        return

    def onMessage(self, Connection, Data, Status, Extra):
        self.oustandingPings = self.oustandingPings - 1
        strData = Data.decode("utf-8", "ignore")
        Domoticz.Debug("onMessage called with Data: '"+str(strData)+"'")

        strData = strData.strip()
        action = strData[0:2]
        detail = strData[2:]

        Domoticz.Log("Message:"+strData)

        if (action == "ZO"): #Zone Open
            UpdateDevice(int(detail),1,"True")
        elif (action == "ZC"): #Zone Closed
            UpdateDevice(int(detail),0,"False")
        elif (action == "DA"): #Disarmed Area A
            UpdateDevice(99,0,"0")
        elif (action == "SA"): #Stay Area A
            UpdateDevice(99,10,"10")
        elif (action == "AA"): #Arm Area A
            UpdateDevice(99,20,"20")
        elif (action == "ES"): #Stay Exit Delay
            UpdateDevice(99,10,"10")
#        elif (action == "EA"): #Arm Exit Delay
#            UpdateDevice(99,20,"20")
        elif (action == "ZA"): #Zone Alarm
            UpdateDevice(17,0,detail)
            UpdateDevice(int(detail),1,"True")
        elif (action == "ZR"): #Zone Restore
            UpdateDevice(17,0,"0")
            UpdateDevice(int(detail),0,"False")
        elif (action == "MF"): #Mains Fail
            Domoticz.Log("Mains Fail")
        elif (action == "MR"): #Mains Restore
            Domoticz.Log("Mains Restore")
        elif (action == "BF"): #Battery Fail
            Domoticz.Log("Battery Fail")
        elif (action == "BR"): #Battery Restore
            Domoticz.Log("Battery Restore")
        elif (action == "LF"): #Line Fail
            Domoticz.Log("Line Fail")
        elif (action == "LR"): #Line Restore
            Domoticz.Log("Line Restore")
        elif (action == "RO"): #All Zones Sealed
            Domoticz.Debug("Ready On - All Zones Sealed")
        elif (action == "NR"): #Zones Are Unsealed
            Domoticz.Debug("Not Ready - Zones Are Unsealed")
        else:
            Domoticz.Debug("Unknown: Action "+strData+" ignored.") #Debug
        return

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        Command = Command.strip()
        action, sep, params = Command.partition(' ')
        action = action.capitalize()
        params = params.capitalize()
        if (Unit == 99): #=Remote Keypad
            if (Command == 'Off'):
                self.telnetConn.Send(Message=DISARMMESSAGE, Delay=0)
                UpdateDevice(17,0,"0")
                Domoticz.Log("Send DISARM")
            elif (Command == 'Set Level'):
                if (Level == 10):
                    self.telnetConn.Send(Message=self.STAYMESSAGE, Delay=0)
                    Domoticz.Log("Send STAY")
                elif (Level == 20):
                    self.telnetConn.Send(Message=self.ARMMESSAGE, Delay=0)
                    Domoticz.Log("Send ARM")


    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")
        self.isConnected = False 

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        
        if (self.telnetConn.Connected() == True):
            if (self.oustandingPings > 3):
                Domoticz.Debug("Ping Timeout, Disconnect")
                self.telnetConn.Disconnect()
                self.nextConnect = 0
            else:
                self.telnetConn.Send(Message=self.STATUSMESSAGE, Delay=0)
                Domoticz.Debug("STATUS Message Sent")
                self.oustandingPings = self.oustandingPings + 1
        else:
            # if not connected try and reconnected every 2 heartbeats
            self.oustandingPings = 0
            self.nextConnect = self.nextConnect - 1
            if (self.nextConnect <= 0):
                self.nextConnect = 3
                self.telnetConn.Connect()
        return

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Connection, Data, Status, Extra)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue, str(sValue))
            Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
    return

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
