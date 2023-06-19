import base64
import json
import os
import socket
import ssl


def request(socket, request):
    # Отправляет запрос в сокет и получает ответ
    socket.send((request + '\n').encode())
    recv_data = socket.recv(65535).decode()
    return recv_data


def read_attachments():
    attachments = []
    attachment_files = config.get('attachments', [])
    for attachment_file in attachment_files:
        if os.path.isfile(attachment_file):
            # Читает файл вложения в двоичном режиме
            with open(attachment_file, 'rb') as file:
                filename = os.path.basename(attachment_file)
                # Кодирует содержимое файла в base64
                content = base64.b64encode(file.read()).decode('utf-8')
                attachments.append((filename, content))
        else:
            print(f"Файл вложения '{attachment_file}' не найден.")

    return attachments


def message_prepare():
    with open('msg.txt', encoding='utf-8') as file_msg:
        boundary_msg = "bound.40629"
        headers = f'from: {config["from"]}\n'
        headers += f'to: {", ".join(config["to"])}\n'  # Несколько получателей, разделенных запятой
        subject = config["subject"]
        # Кодирует тему сообщения в base64 в формате UTF-8
        headers += f'subject: =?utf-8?B?{base64.b64encode(subject.encode()).decode()}?=\n'
        headers += 'MIME-Version: 1.0\n'
        headers += 'Content-Type: multipart/mixed;\n' \
                   f'    boundary={boundary_msg}\n'

        message_body = f'--{boundary_msg}\n'
        message_body += 'Content-Type: text/plain; charset=utf-8\n\n'
        msg = file_msg.read()
        message_body += msg + '\n'

        attachments = read_attachments()

        for attachment in attachments:
            filename, content = attachment
            extension = os.path.splitext(filename)[1].lower()
            content_type = ''
            if extension == '.png':
                content_type = 'image/png'
            elif extension == '.jpg' or extension == '.jpeg':
                content_type = 'image/jpeg'
            elif extension == '.pdf':
                content_type = 'application/pdf'
            elif extension == '.docx':
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif extension == '.xlsx':
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                print(
                    f"Неподдерживаемое расширение файла для вложения '{filename}'")
                continue

            message_body += f'--{boundary_msg}\n'
            message_body += f'Content-Disposition: attachment;\n'
            message_body += f'   filename="{filename}"\n'
            message_body += 'Content-Transfer-Encoding: base64\n'
            message_body += f'Content-Type: {content_type};\n'
            message_body += f'   name="{filename}"\n\n'
            message_body += content + '\n'

        message_body += f'--{boundary_msg}--'

        message = headers + '\n' + message_body + '\n.\n'
        return message


host_addr = 'smtp.yandex.ru'
port = 465

with open('config.json', 'r', encoding='utf-8') as json_file:
    config = json.load(json_file)

with open("pswd.txt", "r", encoding="UTF-8") as file:
    password = file.read().strip()

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

try:
    with socket.create_connection((host_addr, port)) as sock:
        with ssl_context.wrap_socket(sock,
                                     server_hostname=host_addr) as client:
            print(client.recv(1024))
            # Отправляет приветственное сообщение
            print(request(client, f'ehlo {config["from"]}'))
            base64login = base64.b64encode(config["from"].encode()).decode()

            base64password = base64.b64encode(password.encode()).decode()
            # Отправляет запросы для авторизации
            print(request(client, 'AUTH LOGIN'))
            print(request(client, base64login))
            print(request(client, base64password))
            # Отправляет команду MAIL FROM с указанием отправителя
            print(request(client, f'MAIL FROM:{config["from"]}'))
            # Отправляет команды RCPT TO для каждого получателя
            for recipient in config["to"]:
                print(request(client, f"RCPT TO:{recipient}"))
            # Отправляет команду DATA
            print(request(client, 'DATA'))
            # Подготавливает и отправляет сообщение
            print(request(client, message_prepare()))
            # Отправляет команду QUIT для завершения сеанса
            print(request(client, 'QUIT'))
except socket.error as e:
    print(f"Ошибка сети: {e}")
