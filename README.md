# triad_serv

Каждая из папок - отдельный Flask-сервер со своим окружением. Так я себе представляю разделение на микросервисы. Всё взаимодействие происходит по схеме "издатель-посредник-подписчик", определённой протоколом MQTT.

![png](https://raw.githubusercontent.com/anisimovdd/triad_serv/master/triad_serv.png)

# preProcessing_serv ( x.x.x.x : 5002 )

1.	Подключается к Mosquitto и подписывается на TOPIC = "glove":

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
		
# dataStore_serv (192:168:0:15)

1. 	Получает обработанный массив от preProcessing_serv;
2. 	Записывает массив в переменные для конкретного типа события:
	
		# curl -i -X POST -H 'Content-Type: application/json' -d '{proc_arr_1}' http://192:168:0:15:5000/event_1
		data_1 = request.json
		
3. При получении запроса от eventHandling_serv отправляет массив прямиком В ВЕНУ роборуки:
		
		# curl -i -X GET -H 'Content-Type: application/json' -d '{\"req_1\": \"1\"}' http://192:168:0:15:5000/event_1
		curl -i -X POST -H 'Content-Type: application/json' -d '{data_1}' http://[robo-hand-IP]/
					
Получив массив data_1 роборука должна перевести JSON во внутренние комманды и произвести требуемое действие

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
