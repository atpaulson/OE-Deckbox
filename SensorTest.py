import RPi.GPIO as GPIO

#Pin Definitions
ltsensor = 11
motor = 13

#GPIO Setup:
GPIO.setmode(GPIO.BOARD)

#Sensor Setup:
GPIO.setup(motor, GPIO.OUT)
GPIO.setup(ltsensor, GPIO.IN)

#Motor output:
GPIO.output(motor, GPIO.HIGH)
GPIO.output(motor, GPIO.LOW)

#Light Sensor Output:
print('Sensor Status = ', GPIO.input(ltsensor))