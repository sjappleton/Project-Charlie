#import files

import wiringpi as wp
import board
import busio
import digitalio
import adafruit_max31865
import variable
import threading
from threading import Timer
from heaterPWM import SoftwarePWM
from pid import PID
from kivy.app import App
from kivy.config import Config
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.properties import NumericProperty
from kivy.clock import Clock

# screen size
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '480')

# Initialize SPI bus and sensor.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D5)  # Chip select of the MAX31865 board.
sensor = adafruit_max31865.MAX31865(spi, cs, wires=3)

#initialize GPIO
wp.wiringPiSetup()
wp.pinMode(variable.pumppin, 1)
wp.pinMode(variable.valvepin, 1)
wp.digitalWrite(variable.pumppin, 1)
wp.digitalWrite(variable.valvepin, 1)


class heat_on(Image):
    pass

class coffeebutton(Button):
    pass

class steambutton(Button):
    pass

class powerbutton(Button):
    pass

class pump(Button):
    pass

class Gui(BoxLayout):

    def __init__(self, *args):
        super(Gui, self).__init__(*args)

    pump_watch = NumericProperty()
    pump_watch1 = NumericProperty(0.0)
    boilertemp1 = NumericProperty()

    def power_mode(self, *args):
        if args[1] == 'down':
            print("Power on")
            variable.power = True
            Clock.schedule_interval(self.status_update, 1 / 30)

        else:
            print("Power off")
            variable.power = False
            Clock.unschedule(self.status_update)

    def steam_mode(self, *args):

        if args[1] == 'down':
            variable.settemp = 140
            print(variable.settemp)
        else:
            variable.settemp = 105
            print(variable.settemp)

    def status_update(self, dt):
        # Read temperature.
        self.boilertemp1 = round(variable.boilertemp, 1)

    def increment_time(self, dt):
        self.pump_watch += .2
        self.pump_watch1 = round(self.pump_watch, 1)

    def reset_time(self, dt):
        self.pump_watch = 0.0
        self.pump_watch1 = round(self.pump_watch, 1)

    def pump_on(self, *args):
        if args[1] == 'down':
            wp.digitalWrite(variable.pumppin, 0)
            wp.digitalWrite(variable.valvepin, 0)
            print("Pump is turned on")
            Clock.schedule_interval(self.increment_time, .14)
        else:
            print("Pump is turned off")
            wp.digitalWrite(variable.pumppin, 1)
            wp.digitalWrite(variable.valvepin, 1)
            Clock.unschedule(self.increment_time)
            Clock.schedule_once(self.reset_time, 20)

class v3app(App):

    def __init__(self, *args):
        super(v3app, self).__init__(*args)

    def main(self):

        variable.settemp = 105
        variable.calibrationOffset = 0 # Added to thermocouple output.
        variable.boilertemp = sensor.temperature
        variable.tempStarted = False
        variable.heaterPIDStarted = False
        self.pid = PID(5,1,0.04)
        self.pid.setSetPoint(variable.setTemp)

        if variable.tempStarted == False:
            t = threading.Thread(target=variable.boilertemp, args=(50, 200)) # 50% Duty, 60 Hz
            t.daemon = True
            t.start()
            variable.tempStarted = True
        self.startPID()

    def startPID(self):
        if variable.heaterPIDStarted == False:
            self.heaterController = SoftwarePWM(27)
            self.heaterController.pwmUpdate(0, 0.83333) # 1% steps when controlling 60 Hz mains.
            print('Initiated Heater PWM.')
            self.heaterPIDStarted = True
        if variable.power == False:
            self.heaterController.pwmUpdate(0, 0.83333)
        elif (variable.power == True):
            pidOutputReal = self.pid.update(float(variable.boilertemp))
            pidOutput = pidOutputReal
            if pidOutput > 100:
                pidOutput = 100
            elif pidOutput < 0:
                pidOutput = 0
            print('Updating PID with: '+str(variable.boilertemp))
            print('PID Output:        '+str(pidOutputReal))
            print('PID Output Fixed: '+str(int(pidOutput)))
            self.heaterController.pwmUpdate(int(pidOutput), 0.83333)
        Timer(0.416666, self.startPID).start() # Repeat twice as fast as the PWM cycle

    def build(self):
        return Gui()



if __name__ == "__main__":

    v3app().run()
