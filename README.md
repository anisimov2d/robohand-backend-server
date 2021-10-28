# triad_serv

Каждая из папок - отдельный Flask-сервер со своим окружением. Так я себе представляю разделение на микросервисы. Всё взаимодействие происходит по схеме "издатель-посредник-подписчик", определённой протоколом MQTT.

![png](https://raw.githubusercontent.com/anisimovdd/triad_serv/master/triad_serv.png)

# preProcessing_serv ( x.x.x.x : 5002 )

1.	Подключается к Mosquitto и подписывается на MQTT_TOPIC = "glove":

		def on_connect(client, userdata, flags, rc):
		if rc == 0:
			print("🟢 Connected to Mosquitto (" + MQTT_BROKER + ":" + MQTT_PORT + ")")
			client.subscribe(MQTT_TOPIC)
		else:
			print("🔴 Connection failed")

2.	Преобразует полученные от перчатки данные в массив:
		
		message = str(msg.payload, 'utf-8')
		print("> TOPIC: " + msg.topic + "\n" + "📩 MESSAGE: " + message)		
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

3.	Основываясь на значении IO_button происходит разделение режима обучения и прямой трансляции. Режим обучения подразумевает формирование единого массива arr, его обработку и отправку на dataStore_serv:
		
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
		
# dataStore_serv ( x.x.x.x : 5000 )

1.	Подключается к Mosquitto и подписывается на MQTT_TOPIC = [("pP_serv", 0), ("eH_serv", 0)]:

		def on_connect(client, userdata, flags, rc):
		if rc == 0:
			print("🟢 Connected to Mosquitto (" + MQTT_BROKER + ":" + MQTT_PORT + ")")
			client.subscribe(MQTT_TOPIC)
		else:
			print("🔴 Connection failed")
			
2.	При получении данных от preProcessing_serv добавляет их к общему массиву arr:
		
		if msg.topic == "pP_serv":
			# Добавить в общий массив
			arr.append(msg.payload)

3.	При получении запроса от eventHandling_serv извлекает необходимый массив из общего массива. Поочерёдно отправляет элементы соответствующего массива на роборуку:

		else:
			# Событие 1 -- пожать руку
			if msg.payload == "event_1":
				event_1_arr = arr[0]
				# Преобразуем в строку с разделением запятой и передаём на роборуку
				for e in event_1_arr
					e_str = ','.join(map(str, e))
					publish.single("dS_serv", payload = e_str, hostname = "127.0.0.1", port = 1883)
					print("📧 SEND: " + e_str)
			
			# Событие 2 -- взять предмет
			elif msg.payload == "event_2":
				event_2_arr = arr[1]
				# ... тот же код
			
			# Событие 3 -- показать жест
			elif msg.payload == "event_3":
				event_3_arr = arr[2]
				# ... тот же код
			
			# Неизвестное событие
			else:
				print("Неизвестное событие")

# eventHandling_serv (192:168:0:20)

1. 	Получает данные с датчиков роборуки:
		
		# curl -i -X POST -H 'Content-Type: application/json' -d '{\"sensor_1\": \"85\"}' http://192:168:0:20:5000/event_1
		sensor_1 = request.json
		
2. 	Проверяет триггер-условие;
3. 	Отправляет запрос в dataStore_serv, чтобы получить массив:

		min_int = 12 # крайние значения диапазона,
		max_int = 45 # полученные опытным путём
						
		if (min_int < sensor_1 < max_int)
			curl -i -X GET -H 'Content-Type: application/json' -d '{\"req_1\": \"1\"}' http://192:168:0:15:5000/event_1
		else
			abort 400
