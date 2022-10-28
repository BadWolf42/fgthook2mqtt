import logging
import time
import os
import signal
import paho.mqtt.client as mqtt # pip3 install paho-mqtt
from http.server import BaseHTTPRequestHandler, HTTPServer
import shlex
import json

# callback when the broker responds to our connection request.
def on_mqtt_connect(client, userdata, flags, rc):
	logging.info("Connected to MQTT host")
	client.publish(f"{mqttprefix}/connected", "1", 0, True)
	# client.subscribe(f"{mqttprefix}/send")

# callback when the client disconnects from the broker.
def on_mqtt_disconnect(client, userdata, rc):
	logging.info("Disconnected from MQTT host")
	logging.info("Exit")
	exit()

# callback when a message has been received on a topic that the client subscribes to.
def on_mqtt_message(client, userdata, msg):
	try:
		logging.info(f'MQTT received : {msg.payload}')
	except Exception as e:
		pass

# function used to parse received WebHook
class ServerHandler(BaseHTTPRequestHandler):
	# def do_GET(self):
		# logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))

	def do_POST(self):
		payload = self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8')
		# logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
				# str(self.path), str(self.headers), payload)
		message = {'unparsed': payload}
		for token in shlex.split(payload):
			try:
				(key, val) = token.split('=', 1)
				message[key] = val
			except:
				pass
		payload = json.dumps(message)
		client.publish(f"{mqttprefix}/received", payload)


def shutdown(signum=None, frame=None):
	client.publish(f"{mqttprefix}/connected", "0", 0, True)
	client.disconnect()


if __name__ == "__main__":
	logging.basicConfig( format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")
	versionnumber='1.0.0'
	logging.info(f'===== hook2mqtt v{versionnumber} =====')

	# devmode is used to start container but not the code itself
	# then you can connect interactively and run this script by yourself:
	# docker exec -it hook2mqtt /bin/sh
	if os.getenv("DEVMODE",0) == "1":
		logging.info('DEVMODE mode : press Enter to continue')
		try:
			input()
			logging.info('')
		except EOFError as e:
			# EOFError means we're not in interactive so loop forever
			while 1:
				time.sleep(3600)

	hookport = os.getenv("HOOKPORT",4647)
	moreinfo = bool(os.getenv("MOREINFO"))
	heartbeat = bool(os.getenv("HEARTBEAT"))
	mqttprefix = os.getenv("PREFIX","hook2mqtt")
	mqtthost = os.getenv("HOST","localhost")
	mqttport = int(os.getenv("PORT",1883))
	mqttclientid = os.getenv("CLIENTID","hook2mqtt")
	mqttuser = os.getenv("USER")
	mqttpassword = os.getenv("PASSWORD")

	signal.signal(signal.SIGINT, shutdown)
	signal.signal(signal.SIGTERM, shutdown)

	client = mqtt.Client(mqttclientid)
	client.username_pw_set(mqttuser, mqttpassword)
	client.on_connect = on_mqtt_connect
	client.on_disconnect = on_mqtt_disconnect
	client.on_message = on_mqtt_message
	client.will_set(f"{mqttprefix}/connected", "0", 0, True)
	client.connect(mqtthost, mqttport)

	httpd = HTTPServer(('', hookport), ServerHandler)

	while True:
		time.sleep(1)
		client.loop()
		httpd.handle_request()

