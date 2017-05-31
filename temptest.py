import smbus
from time import sleep

bus = smbus.SMBus(1)

Temp = []
Pres = []
Humi = []
tt = 0.0


# Write Sensor I2C
def writeSensor(reg_addr, data):
	bus.write_byte_data(0x76, reg_addr, data)


# Get Calibration Data
def getCalibration():
	calib = []

	for i in range(0x88, 0x88+24):
		calib.append(bus.read_byte_data(0x76, i))
	calib.append(bus.read_byte_data(0x76, 0xA1))
	for i in range(0xE1, 0xE1+7):
		calib.append(bus.read_byte_data(0x76, i))

	Temp.append((calib[1] << 8) | calib[0])
	Temp.append((calib[3] << 8) | calib[2])
	Temp.append((calib[5] << 8) | calib[4])
	Pres.append((calib[7] << 8) | calib[6])
	Pres.append((calib[9] << 8) | calib[8])
	Pres.append((calib[11]<< 8) | calib[10])
	Pres.append((calib[13]<< 8) | calib[12])
	Pres.append((calib[15]<< 8) | calib[14])
	Pres.append((calib[17]<< 8) | calib[16])
	Pres.append((calib[19]<< 8) | calib[18])
	Pres.append((calib[21]<< 8) | calib[20])
	Pres.append((calib[23]<< 8) | calib[22])
	Humi.append( calib[24] )
	Humi.append((calib[26]<< 8) | calib[25])
	Humi.append( calib[27] )
	Humi.append((calib[28]<< 4) | (0x0F & calib[29]))
	Humi.append((calib[30]<< 4) | ((calib[29] >> 4) & 0x0F))
	Humi.append( calib[31] )

	for i in range(1,2):
		if Temp[i] & 0x8000:
			Temp[i] = (-Temp[i] ^ 0xFFFF) + 1

	for i in range(1,8):
		if Pres[i] & 0x8000:
			Pres[i] = (-Pres[i] ^ 0xFFFF) + 1

	for i in range(0,6):
		if Humi[i] & 0x8000:
			Humi[i] = (-Humi[i] ^ 0xFFFF) + 1


# Read Now Temperature,Pressure,Humidity
def readData():
	data = []
	for i in range(0xF7, 0xF7+8):
		data.append(bus.read_byte_data(0x76, i))
	pres = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
	temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
	humi = (data[6] << 8)  |  data[7]

	t2 = adjustTemp(temp)
	p2 = adjustPres(pres)
	h2 = adjustHumi(humi)

	print "temp : %6.2f C" % t2
	print "pressure : %7.2f hPa" % p2
	print "hum : %6.2f %%" % h2
	print ""


# Adjust Pressure by Calibration
def adjustPres(nowpres):
	global  tt
	pressure = 0.0

	v1 = (tt / 2.0) - 64000.0
	v2 = (((v1 / 4.0) * (v1 / 4.0)) / 2048) * Pres[5]
	v2 = v2 + ((v1 * Pres[4]) * 2.0)
	v2 = (v2 / 4.0) + (Pres[3] * 65536.0)
	v1 = (((Pres[2] * (((v1 / 4.0) * (v1 / 4.0)) / 8192)) / 8) \
	     + ((Pres[1] * v1) / 2.0)) / 262144
	v1 = ((32768 + v1) * Pres[0]) / 32768

	if v1 == 0:
		return 0
	pressure = ((1048576 - nowpres) - (v2 / 4096)) * 3125
	if pressure < 0x80000000:
		pressure = (pressure * 2.0) / v1
	else:
		pressure = (pressure / v1) * 2
	v1 = (Pres[8] * (((pressure / 8.0) * (pressure / 8.0)) \
	     / 8192.0)) / 4096
	v2 = ((pressure / 4.0) * Pres[7]) / 8192.0
	pressure = pressure + ((v1 + v2 + Pres[6]) / 16.0)

	return pressure/100


# Adjust Temperature by Calibration
def adjustTemp(nowtemp):
	global tt
	v1 = (nowtemp / 16384.0 - Temp[0] / 1024.0) * Temp[1]
	v2 = (nowtemp / 131072.0 - Temp[0] / 8192.0) \
	    * (nowtemp / 131072.0 - Temp[0] / 8192.0) * Temp[2]
	tt = v1 + v2
	temperature = tt / 5120.0

	return temperature


# Adjust Humidity by Calibration
def adjustHumi(nowhumi):
	global tt
	var_h = tt - 76800.0
	if var_h != 0:
		var_h = (nowhumi - (Humi[3] * 64.0 + Humi[4]/16384.0 \
		        * var_h)) * (Humi[1] / 65536.0 * (1.0 \
		        + Humi[5] / 67108864.0 * var_h * (1.0 \
		        + Humi[2] / 67108864.0 * var_h)))
	else:
		return 0
	var_h = var_h * (1.0 - Humi[0] * var_h / 524288.0)
	if var_h > 100.0:
		var_h = 100.0
	elif var_h < 0.0:
		var_h = 0.0

	return var_h


# Initialize Sensor
def setup():
	Tovs = 1     # Temperature oversampling x 1
	Povs = 1     # Pressure oversampling x 1
	Hovs = 1     # Humidity oversampling x 1
	mode   = 3   # Normal mode
	stby   = 5   # Tstandby 1000ms
	filter = 0   # Filter off
	spion = 0    # 3-wire SPI Disable

	ctrl_meas_reg = (Tovs << 5) | (Povs << 2) | mode
	config_reg    = (stby << 5) | (filter << 2) | spion
	ctrl_hum_reg  = Hovs

	writeSensor(0xF2, ctrl_hum_reg)
	writeSensor(0xF4, ctrl_meas_reg)
	writeSensor(0xF5, config_reg)


# Main
setup()
getCalibration()

try:
	while True:
		readData()
		sleep(3.0)
except KeyboardInterrupt:
	pass
