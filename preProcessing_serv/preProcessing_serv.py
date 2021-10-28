# Запуск сервера: python preProcessing_serv.py
from flask import Flask
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

app = Flask(__name__)
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "glove"

@app.route('/')
def pP_serv():
	
	arr = [ ] # единый массив, его назнаение описано ниже

	# Подключение + Подписка на TOPICS
	def on_connect(client, userdata, flags, rc):
		if rc == 0:
			print("🟢 Connected to Mosquitto (" + MQTT_BROKER + ":" + MQTT_PORT + ")")
			client.subscribe(MQTT_TOPIC)
		else:
			print("🔴 Connection failed")

	# Обработка сообщений от перчатки	
	def on_message(client, userdata, msg):
		message = str(msg.payload, 'utf-8')
		print("> TOPIC: " + msg.topic + "\n" + "📩 MESSAGE: " + message)
		
		# На последней встрече с Бахадыром мы обсуждали в каком виде будут отправляться
		# данные с перчатки. JSON показался избыточным, поэтому мы договорились, что данные
		# будут просто разделены запятой. Только потом я уже понял, что по сути это и есть
		# массив. Чтобы Бахадыру лишний раз не пришлось переписывать код, то преобразование
		# в массив сделаем на стороне сервера.
		
		# Преобразование в массив
		message_arr = message.split(',')
		
		# Предварительно массив будет иметь следующюю структуру:
		# message_arr = [ R1, R2, R3, R4, R5, AG1, AG2, AG3, IO_button], где
		# Rn - показания резисторов изгиба каждого пальца
		# AGn - показания акселерометра и гироскопа 
		# IO_button - кнопка 0 или 1. На неё возложена большая задача. Данные c IO_button = 0,
		# напрямую транслируются на роборуку. При IO_button = 1 алгоритм переходит в режим обучения.
		# Формируется единый массив arr = [ [], [], ... ]. При поступлении пакета с IO_button = 0,
		# запись в массив прекращается и считается, что он готов к обработке. По завершению обработки
		# единый массив должен быть отправлен на dS_serv.
		
		# Если поступил массив с IO_button = 0
		if message_arr[8] == 0:
			# Eсли единый массив ещё не заполнялся или был очищен
			if len(arr) == 0:
				publish.single("dS_serv", payload = msg.payload, hostname = "127.0.0.1", port = 1883)
			# Если единый массив сформирован
			else:
				# Обработка единого массива через алгоритм сглаживания
				# proc_arr_1 = smoothAlg(arr)
				
				# На данный момент сглаживание производится на стороне перчатки. Поэтому код выше был
				# закомментирован. В дальнейшем, конечно же, обработка будет на сервере.
				
				# Отправка обработанного массива на dS_serv
				publish.single("pP_serv", payload = arr, hostname = "127.0.0.1", port = 1883)
				print("📧 SEND: " + arr)
				# Очистка единого массива
				arr.clear()

		# Если поступил массив с IO_button = 1
		else:
			# Формирование единого массива
			arr.append(message_arr)

	client = mqtt.Client()
	client.on_connect = on_connect
	client.on_message = on_message
	client.connect(MQTT_BROKER, MQTT_PORT, 60)
	client.loop_forever()
	
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002) # https://codex.so/python-flask