from gpiozero import LED

relais = [LED(22), LED(23), LED(24), LED(25)]

def RelaisOn(idx):
    relais[idx].on()

def RelaisOff(idx):
    relais[idx].off()


