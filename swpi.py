###########################################################################
#     Sint Wind PI
#     Copyright 2012 by Tonino Tarsi <tony.tarsi@gmail.com>
#   
#     Please refer to the LICENSE file for conditions 
#     Visit http://www.vololiberomontecucco.it
# 
##########################################################################

"""     Main program """

import time
import sqlite3
import os
import humod 
import config
import webcam
import sys
import urllib2, urllib
import datetime
import camera
from TTLib import *
import version
import sensor_thread
import globalvars
import radio
import ntplib
import meteodata
import math
import service
import tarfile
import signal
import thread
import database

#signal.signal(signal.SIGPIPE, signal.SIG_DFL) 

################################  functions############################

def new_sms(modem, message):
	"""Event Function for new incoming SMS"""
	log( 'New message arrived: %r' % message)
	msg_num = int(message[12:].strip())
	process_sms(modem,msg_num)

def process_sms(modem, smsID):
	"""Parse SMS number smsID"""
	try:	
		global cfg
		msgID = smsID
		smslist = modem.sms_list()
		bFound = False
		for message in smslist:
			if (message[0] == msgID ):
				bFound = True
				break
		if ( not bFound ):
			print "ERROR - SMS not found"
			return();
		
		msgText =  modem.sms_read(msgID)
		msgSender = message[2]
		msgDate = message[4]
		log( "Processind SMS : " + str(msgID) + " - Text:  " +  msgText + "  - Sender :" + msgSender)
	
		command = msgText.split()
		if ( len(command) < 2 ):
			log( "Bad Command .. Deleting")
			modem.sms_del(msgID)
		pwd = command[0]
		if ( pwd != cfg.SMSPwd ):
			log( "Bad SMS Password .. deleting")
			modem.sms_del(msgID)
			return False
		cmd = command[1].upper()
		if ( len(command) == 3 ):
			param = command[2] 
		conn = sqlite3.connect('db/swpi.s3db',200)
		dbCursor = conn.cursor()
		#----------------------------------------------------------------------------------------
		#                                          SMS COMMANDS
		#	command	param	desc
		#
		#	RBT				reboot	
		#	MDB				mail database to sender
		#	MCFG			mail cfg to sender
		#	CAM		X		set camera/logging interval to X seconds
		#	LOG		[0/1]	enable [1] or disable [0] internet logging
		#	UPL		[0/1]	enable [1] or disable [0] internet uploading
		#	AON		[0/1]	set [1] or reset [0] always on internet parameter
		#	UDN		[0/1]	set [1] or reset [0] use dongle net parameter
		#	IP				send sms with current IP to sender
		#	UPD				Update software
		#	WSO		X		set calibration wind speed offset to X 
		#	WSG		X		set calibration wind speed gain to X
		#	RDB				Reset Database
		#---------------------------------------------------------------------------------------	
		
		if (len(command) == 2 and cmd == "RBT" ):
			modem.sms_del(msgID)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			log( "Receiced rebooting command  " )
			systemRestart()
		#---------------------------------------------------------------------------------------	
		if (len(command) == 2 and cmd == "RDB" ):
			modem.sms_del(msgID)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			dbCursor.execute("delete from METEO")
			conn.commit()
			log( "Database resetted  " )
		#---------------------------------------------------------------------------------------	
	
		elif (len(command) == 2 and cmd == "MDB" ):
			modem.sms_del(msgID)
			tarname = "db.tar.gz"
			tar = tarfile.open(tarname, "w:gz")
			tar.add("./db")
			tar.close()
			if SendMail(cfg, "DB", "Here your DB", tarname):
				log("DB sent by mail")
			os.remove(tarname)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
		#---------------------------------------------------------------------------------------	
		elif (len(command) == 2 and cmd == "MCFG" ):
			modem.sms_del(msgID)
			tarname = "cfg.tar.gz"
			tar = tarfile.open(tarname, "w:gz")
			tar.add("swpi.cfg")
			tar.close()
			if SendMail(cfg, "CFG", "Here your CFG", tarname):
				log("CFG sent by mail")
			os.remove(tarname)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
		#---------------------------------------------------------------------------------------	
		elif (len(command) > 2 and cmd == "SYS" ):
			modem.sms_del(msgID)
			syscmd = ''.join(command[2:])
			log( 'Executing %r' % syscmd)
			cmd_exec = os.popen(syscmd)
			output = cmd_exec.read()
			
			if ( len(output) > 250 ):
				output = output[:250]
			output = "prova"
			log( 'Sending the output back to %s output: %s' % (msgSender, output))
			modem.sms_send(msgSender, output)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			systemRestart()
		#---------------------------------------------------------------------------------------		
		elif (len(command) == 3 and cmd == "CAM" ):
			modem.sms_del(msgID)
			WebCamInterval = int(param)
			cfg.setWebCamInterval(WebCamInterval)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			log( "New CAM interval set to : " + str(cfg.WebCamInterval))
		#---------------------------------------------------------------------------------------	
		elif (len(command) == 3 and cmd == "LOG" ):
			modem.sms_del(msgID)
			if ( param == '0' or param == '1' ):
				cfg.setDataLogging(param)
				dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
				conn.commit()	
				if param == '0':	
					log( "Internet logging disabled ")
				else:
					log( "Internet logging enabled ")
		#---------------------------------------------------------------------------------------		
		elif (len(command) == 3 and cmd == "UPL" ):
			modem.sms_del(msgID)
			if ( param == '0' or param == '1' ):
				cfg.setDataUpload(param)
				dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
				conn.commit()	
				if param == '0':	
					log( "Internet Uploading disabled ")
				else:
					log( "Internet Uploading enabled ")
		#---------------------------------------------------------------------------------------				
		elif (len(command) == 3 and cmd == "AOI" ):
			modem.sms_del(msgID)
			AlwaysOnInternet = param
			cfg.setAlwaysOnInternet(AlwaysOnInternet)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			log( "New Always On Internet set to : " + cfg.AlwaysOnInternet )
			systemRestart()
		#---------------------------------------------------------------------------------------		
		elif (len(command) == 3 and cmd == "UDN" ):
			modem.sms_del(msgID)
			UseDongleNet = param
			cfg.setUseDongleNet(UseDongleNet)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			log( "UseDongleNet set to : " + cfg.UseDongleNet )
			systemRestart()
		#---------------------------------------------------------------------------------------		
		elif (len(command) == 2 and cmd == "IP" ):
			modem.sms_del(msgID)
			if ( IP != None and cfg.usedongle  ):
				try:
					modem.sms_send(msgSender, IP)
					log ("SMS sent to %s" % msgSender)
				except:
					log("Error sending IP by SMS")
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			log( "Sent IP" )
		#----------------------------------------------------------------------------		
		elif (len(command) == 3 and cmd == "WSO" ):
			modem.sms_del(msgID)
			cfg.setWindSpeed_offset(param)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			log( "Wind Speed offset set to : " + str(cfg.windspeed_offset ))
		#---------------------------------------------------------------------------------------		
		elif (len(command) == 3 and cmd == "WSG" ):
			modem.sms_del(msgID)
			cfg.setWindSpeed_gain(param)
			dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
			conn.commit()		
			log( "Wind Speed gain set to : " + str(cfg.windspeed_gain ))
		#---------------------------------------------------------------------------------------		
		elif (len(command) == 2 and cmd == "UPD" ):
			modem.sms_del(msgID)
			
			bbConnected = False
			if ( ( not internet_on()) and cfg.UseDongle and cfg.UseDongleNet ):
				log( "Trying to connect to internet with 3G dongle ....")
				time.sleep(1)
				modem.connectwvdial()
				time.sleep(2)
				waitForIP()
				bbConnected = True
			
			if ( internet_on() ):
				swpi_update()
				dbCursor.execute("insert into SMS(Number, Date,Message) values (?,?,?)", (msgSender,msgDate,msgText,))
				conn.commit()		
				
			if (bbConnected ):
				log("Try to disconnect")
				modem.disconnectwvdial()
				
	
			log( "SWPI-UPDATE" )
			systemRestart()
		#----------------------------------------------------------------------------	
			
		if conn:
			conn.close()
		
		modem.sms_del(msgID)	
		return True
	except :
		log( "D - Exept in MSG" )
		modem.sms_del(msgID)
		if conn:
			conn.close()
		return False
		
	
	return True
	
################################################## CALL ##############################################################	
def answer_call(modem, message):
	#global ws
	try:
		if (  globalvars.bCapturingCamera ):
			log("Not answering because capturing camera images")
			return
		
		if (  globalvars.meteo_data.last_measure_time == None or  globalvars.meteo_data.status != 0 ):
			log("Not answering because no valid meteo data yet")
			return		
				
		
		if ( len(message) > 7 and message[:6] == '+CLIP:' ):
			callingNumber = message[6:].split(',')[0]
		else:
			callingNumber = 'Error'
		log( "Receiving call from : " + callingNumber )
		
		delay = (datetime.datetime.now() - globalvars.meteo_data.last_measure_time)
		delay_seconds = int(delay.total_seconds())
		log("Answering with data of %d seconds old" % delay_seconds	)	
		
			
		#prepare list of messages
		listOfMessages = []
		
		listOfMessages.append("./audio/silence05s.raw") 
		listOfMessages.append("./audio/hello.raw")
		
		if ( cfg.sensor_type.upper() == "SIMULATE" ):
			listOfMessages.append("./audio/simulate.raw")
			
		if (delay_seconds > 600 ):
			listOfMessages.append("./audio/some_problem.raw") 

		if( globalvars.meteo_data.rain_rate != None and globalvars.meteo_data.rain_rate >= 0.001 ):
			listOfMessages.append("./audio/raining.raw")
		
		# Wind Speed and Direction
		listOfMessages.append("./audio/winddirection.raw")
		listOfMessages.append("./audio/" + str(globalvars.meteo_data.wind_dir_code) + ".raw")		
		listOfMessages.append("./audio/from.raw")
		listOfMessages.append("./audio/" + str(int(globalvars.meteo_data.wind_ave)) + ".raw")
		listOfMessages.append("./audio/to.raw")
		
		listOfMessages.append("./audio/" + str(int(globalvars.meteo_data.wind_gust)) + ".raw")
		listOfMessages.append("./audio/km.raw")
	
		# Temperature
		if ( globalvars.meteo_data.temp_out != None ):
			listOfMessages.append("./audio/silence05s.raw") 
			if ( globalvars.meteo_data.temp_out < 0) :
				listOfMessages.append("./audio/minus.raw") 
	
#			intera =  int( math.floor(abs(globalvars.meteo_data.temp_out)) )
#			dec = int( (abs(globalvars.meteo_data.temp_out)-intera)*10 )
#			listOfMessages.append("./audio/temperature.raw")
#			listOfMessages.append("./audio/" + str(intera) + ".raw")
#			listOfMessages.append("./audio/comma.raw")
#			listOfMessages.append("./audio/" + str(dec ) + ".raw")
						
			intera = int(round( abs(globalvars.meteo_data.temp_out) ))
			listOfMessages.append("./audio/temperature.raw")
			listOfMessages.append("./audio/" + str(intera) + ".raw")
			listOfMessages.append("./audio/degree.raw")

		# Pressure
		if ( globalvars.meteo_data.abs_pressure != None ):
			thousands, rem = divmod(round(globalvars.meteo_data.abs_pressure), 1000) 
			thousands = int(thousands * 1000)
			hundreds, tens = divmod(rem, 100)
			hundreds = int(hundreds * 100)
			tens = int(round(tens))	
			listOfMessages.append("./audio/silence05s.raw") 
			listOfMessages.append("./audio/pressure.raw")
			if ( thousands != 0):
				listOfMessages.append("./audio/" + str(thousands) + ".raw")
			if ( hundreds != 0):
				listOfMessages.append("./audio/" + str(hundreds) + ".raw")
			listOfMessages.append("./audio/" + str(tens) + ".raw")
			listOfMessages.append("./audio/hpa.raw")
			
		# Humidity
		if ( globalvars.meteo_data.hum_out != None ):
			listOfMessages.append("./audio/silence05s.raw") 
			intera =  int( globalvars.meteo_data.hum_out) 
			listOfMessages.append("./audio/umidity.raw")
			listOfMessages.append("./audio/" + str(intera) + ".raw")
			listOfMessages.append("./audio/percent.raw")
		
		# Statistics
		listOfMessages.append("./audio/minday.raw")
		listOfMessages.append("./audio/" + str(int(globalvars.meteo_data.winDayMin)) + ".raw")		
		listOfMessages.append("./audio/maxday.raw")	
		listOfMessages.append("./audio/" + str(int(globalvars.meteo_data.winDayMax)) + ".raw")
		listOfMessages.append("./audio/silence05s.raw") 		
		listOfMessages.append("./audio/thanks.raw")
		listOfMessages.append("./audio/www.raw")
		listOfMessages.append("./audio/silence05s.raw") 
		listOfMessages.append("./audio/swpi.raw")
			
		modem.answerCallNew(listOfMessages)
		
		#log to database
		conn = sqlite3.connect('db/swpi.s3db',200)
		dbCursor = conn.cursor()
		dbCursor.execute("insert into CALL(Number) values (?)", (callingNumber,))
		conn.commit()
		conn.close()

	except :
		log("Error in answering %s" % sys.exc_info()[0])
		pass





##################################################################################
v = version.Version("VERSION").getVersion()
log( "Starting SINT WIND PI  ... ")
############################ MAIN ###############################################
print "************************************************************************"
print "*                      Sint Wind PI "+v+"                           *"
print "*                                                                      *"
print "*            2012 by Tonino Tarsi  <tony.tarsi@gmail.com>              *"
print "*                                                                      *"
print "*     System will start in 10 seconds - Press Ctrl-C to cancel         *"
print "************************************************************************"
# Load Configuration
configfile = 'swpi.cfg'
if not os.path.isfile(configfile):
	cfg = config.config(configfile,False)
	log("Configurantion file created. Now edit the file :  %s and restart with command  : swpi "  % (configfile))
	exit(0)
else:
	cfg = config.config(configfile,False)
	
# give 10 seconds for interrupt the application
try:
	if not ( '-i' in sys.argv ) :
		for i in range(0,10):
			sys.stdout.write(str(10-i) + ".....")
			sys.stdout.flush()
			time.sleep(1)
		print ""
except KeyboardInterrupt:
	#print  "Stopping swpi"
	exit(0)

# Radio Voice output shoud go to the analog device
os.system( "sudo amixer cset numid=3 1 > /dev/null " )

#Make sure every executable is executable
os.system( "sudo chmod +x ./usbreset" )
#os.system( "sudo chmod +x ./swpi.sh" )
#os.system( "sudo chmod +x ./swpi-update.sh" )
#os.system( "sudo chmod +x ./killswpi.sh" )

# Some Globasl :-(
globalvars.bAnswering = False
globalvars.bCapturingCamera = False
globalvars.meteo_data = meteodata.MeteoData(cfg)
IP = None

# Start sensors thread ##
if ( cfg.use_wind_sensor ):
	wind_sensor_thread = sensor_thread.WindSensorThread(cfg)
	wind_sensor_thread.start()

bConnected = False

# Init Dongle
if cfg.usedongle :
	modem = humod.Modem(cfg.dongleDataPort,cfg.dongleAudioPort,cfg.dongleCtrlPort,cfg)
	modem.enable_textmode(True)
	modem.enable_clip(True)	
	modem.enable_nmi(True)
	sms_action = (humod.actions.PATTERN['new sms'], new_sms)
	call_action = (humod.actions.PATTERN['incoming callclip'], answer_call)
	actions = [sms_action , call_action]
	modem.prober.start(actions) # Starts the prober.
	print ""
	log( "Modem Model : "  + modem.show_model())
	log(  "Revision : "  + modem.show_revision())
	log(  "Modem Serial Number : " + modem.show_sn())
	log(  "Pin Status : " + modem.get_pin_status())
	log(  "Device Center : " + modem.get_service_center()[0] + " " + str(modem.get_service_center()[1]))
	log(  "Signal quality : " + str(modem.get_rssi()))

	log( "Checking new sms messages...")
	smslist = modem.sms_list()
	for message in smslist:
		smsID = message[0]
		process_sms(modem,smsID)

	if ( ( not internet_on()) and cfg.UseDongleNet ):
		log( "Trying to connect to internet with 3G dongle ....")
		time.sleep(1)
		modem.connectwvdial()
		time.sleep(2)
		waitForIP()
		if ( not cfg.AlwaysOnInternet ) :
			bConnected = True

# Get network IP
if (internet_on() ):
	IP = getIP()
	if IP != None:
		log("Connected with IP :" + IP)
else:
	log("Running without internet connection")


# Set Time from NTP ( using a thread to avoid strange freezing )
if ( cfg.set_system_time_from_ntp_server_at_startup ):
	thread.start_new_thread(SetTimeFromNTP, (cfg.ntp_server,)) 

# Send mail with IP information ( using a thread to avoid strange freezing )
if ( IP != None and cfg.use_mail and cfg.mail_ip ):
	thread.start_new_thread(SendMail,(cfg,"IP","My IP today is : " + IP ,"")) 
	
# Send mail with IP information
#if ( IP != None and cfg.use_mail and cfg.mail_ip ):
#	if ( SendMail(cfg,"IP","My IP today is : " + IP ,"") ):
#		log ("Mail sent to :" + cfg.mail_to )
#	else:
#		log ("ERROR sending mail" )

# Send SMS with IP information
if ( IP != None and cfg.usedongle and cfg.send_IP_by_sms  ):
	try:
		modem.sms_send(cfg.number_to_send, IP)
		log ("SMS sent to %s" % cfg.number_to_send)
	except:
		log("Error sending IP by SMS")


# Start radio thread
if ( cfg.useradio ):
	radio = radio.RadioThread(cfg)
	radio.start()
	
# Start service thread if necessary
service.run_all_service_thread(cfg)

if bConnected:
	log("Try to disconnect")
	modem.disconnectwvdial()
	
# Wait for valid data
if ( cfg.use_wind_sensor ) :
	while ( globalvars.meteo_data.status == -999 ) :
		time.sleep(1)

# clear all sd cards at startup
if ( cfg.clear_all_sd_cards_at_startup):
	camera.ClearAllCameraSDCards(cfg)		

# Start main thread
############################ MAIN  LOOP###############################################

while 1:
	try:
		if ( cfg.usedongle ):  log("Signal quality : " + str(modem.get_rssi()))

		waitForHandUP()  # do to replace with lock object
		if ( cfg.webcamDevice1.upper() != "NONE" ):
			webcam1 =  webcam.webcam(1,cfg)
			img1FileName = "./img/webcam1_" + datetime.datetime.now().strftime("%d%m%Y-%H%M%S.jpg") 
			waitForHandUP()
			bwebcam1 = webcam1.capture(img1FileName)
			if ( bwebcam1 ):
				log( "Webcam 1 Captured : ok : "  + img1FileName )
				addTextandResizePhoto(img1FileName,cfg.webcamdevice1finalresolutionX,cfg.webcamdevice1finalresolutionY,cfg,v)
		if ( cfg.webcamDevice2.upper() != "NONE" ):
			webcam2 =  webcam.webcam(2,cfg)
			img2FileName = "./img/webcam2_" + datetime.datetime.now().strftime("%d%m%Y-%H%M%S.jpg")
			waitForHandUP()
			bwebcam2 = webcam2.capture(img2FileName)
			if ( bwebcam2):
				log( "Webcam 2 Capruterd : "  + img2FileName	)	
				addTextandResizePhoto(img2FileName,cfg.webcamdevice2finalresolutionX,cfg.webcamdevice2finalresolutionY,cfg,v)			
		if ( cfg.usecameradivice ):
			waitForHandUP()
			cameras = camera.PhotoCamera(cfg)
			fotos = cameras.take_pictures()
			for foto in fotos:
				addTextandResizePhoto(foto,cfg.cameradivicefinalresolutionX,cfg.cameradivicefinalresolutionY,cfg,v)
					
		bConnected = False
		
		if ( cfg.sendImagesToServer or cfg.logdata ):
			waitForHandUP()
			if ( (not internet_on()) and cfg.UseDongleNet and modem._pppd_pid == None): # connect if not
				log( "Trying to connect to internet with 3G dongle")
				modem.connectwvdial()
				IP = waitForIP()
				log("Connected with IP :" + IP)
				if ( IP != None ):
					bConnected = True
				
			if (  internet_on() ):
				waitForHandUP()
				if ( cfg.webcamDevice1.upper() != "NONE" and bwebcam1 ):
					if (cfg.sendallimagestoserver ):
						waitForHandUP()
						sendFileToServer(img1FileName,getFileName(img1FileName),cfg.ftpserver,cfg.ftpserverDestFolder,cfg.ftpserverLogin,cfg.ftpserverPassowd)
					else:
						waitForHandUP()
						sendFileToServer(img1FileName,"current1.jpg",cfg.ftpserver,cfg.ftpserverDestFolder,cfg.ftpserverLogin,cfg.ftpserverPassowd)
					if ( cfg.delete_images_on_sd ):
						os.remove(img1FileName)
						log("Deleted file : " + img1FileName )
				if ( cfg.webcamDevice2.upper() != "NONE" and bwebcam2 ):
					if (cfg.sendallimagestoserver ):
						waitForHandUP()
						sendFileToServer(img2FileName,getFileName(img2FileName),cfg.ftpserver,cfg.ftpserverDestFolder,cfg.ftpserverLogin,cfg.ftpserverPassowd)
					else:
						waitForHandUP()
						sendFileToServer(img2FileName,"current2.jpg",cfg.ftpserver,cfg.ftpserverDestFolder,cfg.ftpserverLogin,cfg.ftpserverPassowd)
					if ( cfg.delete_images_on_sd ):
						os.remove(img2FileName)
						log("Deleted file : " + img2FileName )
				if ( cfg.usecameradivice   ):
					nCamera = 0
					for foto in fotos:
						nCamera = nCamera + 1
						if (cfg.sendallimagestoserver ):
							waitForHandUP()
							sendFileToServer(foto,getFileName(foto),cfg.ftpserver,cfg.ftpserverDestFolder,cfg.ftpserverLogin,cfg.ftpserverPassowd)
						else:
							waitForHandUP()
							sendFileToServer(foto,"camera"+str(nCamera)+".jpg",cfg.ftpserver,cfg.ftpserverDestFolder,cfg.ftpserverLogin,cfg.ftpserverPassowd)				
						if ( cfg.delete_images_on_sd ):
							os.remove(foto)
						log("Deleted file : " + foto )
						
				if ( cfg.logdata and  globalvars.meteo_data.last_measure_time != None and  globalvars.meteo_data.status == 0 ) :
					logData(cfg.serverfile)

				if ( cfg.upload_data and  globalvars.meteo_data.last_measure_time != None and  globalvars.meteo_data.status == 0 ) :
					UploadData(cfg)			
			
				thenewIP = getIP()
				if ( thenewIP != None and IP != thenewIP ):
					IP = thenewIP
					log("IP has changed - New IP is : " + IP)
					if ( cfg.use_mail and cfg.mail_ip ):
						SendMail(cfg,"IP",IP,"")
				
				
				# Set Time from NTP ( using a thread to avoid strange freezing )
				if ( cfg.set_system_time_from_ntp_server_at_startup ):
					thread.start_new_thread(SetTimeFromNTP, (cfg.ntp_server,)) 
				
				if bConnected:
					log("Try to disconnect")
					modem.disconnectwvdial()
					
			else:
				log("Error. Non internet connection available")
			
		#check if all threads are alive
		if cfg.useradio:
			if ( not radio.isAlive()):
				log("Error : Something wrong with radio .. restarting")
				systemRestart()
		if True:
			if ( not wind_sensor_thread.isAlive()):
				log("Error : Something wrong with sensors .. restarting ws")
				systemRestart()		
				
		if ( cfg.WebCamInterval != 0):
			time.sleep(cfg.WebCamInterval)
			
		else:
			time.sleep(1000)	
		
	except KeyboardInterrupt:
		if cfg.usedongle:
			modem.prober.stop()
		if ( cfg.useradio):
			radio.stop()
		wind_sensor_thread.stop()
		exit(0)
			
	





