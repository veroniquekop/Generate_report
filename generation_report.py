import requests
from reportlab.lib.pagesizes import A4
from PIL import Image as PILImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Image, Spacer, Paragraph, PageBreak
import json
from io import BytesIO
from requests_toolbelt.multipart.encoder import MultipartEncoder
import base64
import time

with open('json_new_params.json', 'r') as file:
    data = json.load(file)
    print(data)

X_Key = "Key C261C83AEE72AB587AF5D5E576466F72"
X_Secret = "Secret 9D31AD79BD718F75D5E67DEBB1DA6849"

headers = {
    'X-Key': X_Key,
    'X-Secret': X_Secret,
    'Content-type': 'multipart/form-data; boundary=ebf9f03029db4c2799ae16b5428b06bd'
}

doc = SimpleDocTemplate("generation_report.pdf", pagesize=A4)
styles = getSampleStyleSheet()
max_width_px = 1024
max_height_px = 1024
story = []

for item in data:
    style = item.get('style')
    prompt_text = item.get('prompt')
    width = float(item.get('width'))
    height = float(item.get('height'))
    name = item.get('name')

    api_url = 'https://api-key.fb2.ait.lol/key/api/v1/text2image/run'
    payload = {
        "type": "GENERATE",
        "generateParams": {"query": prompt_text},
        'width': width,
        'height': height,
        'style': style
    }
    multipart_data = MultipartEncoder(
        fields={
            'params': ('params', json.dumps(payload), 'application/json'),
            'model_id': str(34)
        },
        boundary='ebf9f03029db4c2799ae16b5428b06bd'
    )
    try:
        response = requests.post(api_url, data=multipart_data, headers=headers)


        if response.status_code == 201:
            response_json = response.json()
            uuid_value = response_json.get('uuid')

            if uuid_value:
                status_url = f'https://api-key.fb2.ait.lol/key/api/v1/text2image/status/{uuid_value}'
                get_response = requests.get(status_url, headers=headers)

                if get_response.status_code == 200:
                    try:
                        get_response_json = get_response.json()

                        while get_response_json.get('status') != 'DONE':
                            time.sleep(1)
                            get_response = requests.get(status_url, headers=headers)
                            get_response_json = get_response.json()

                    except json.decoder.JSONDecodeError as json_err:
                        print("Ошибка декодирования JSON: ", json_err)
                        print("Полученный ответ: ", get_response.text)
                        continue

                    images = get_response_json.get('images')[0]

                    image_bytes = BytesIO(base64.b64decode(images))
                    img_pil = PILImage.open(image_bytes)

                    new_width, new_height = img_pil.size

                    if new_width > max_width_px or new_height > max_height_px:
                        width_ratio = max_width_px/new_width
                        height_ratio = max_height_px/new_height
                        resize_ratio = min(width_ratio, height_ratio)
                        new_width = int(new_width * resize_ratio)
                        new_height = int(new_height * resize_ratio)
                        img_pil = img_pil.resize((new_width, new_height), PILImage.LANCZOS)

                    scale_factor = 0.5
                    new_width = int(new_width * scale_factor)
                    new_height = int(new_height * scale_factor)

                    image_buffer = BytesIO()
                    img_pil.save(image_buffer, format='PNG')
                    image_buffer.seek(0)

                    img = Image(image_buffer, width=new_width, height=new_height)
                    img.hAlign = 'CENTER'

                    prompt_style = styles[style] if style in styles else styles["Normal"]
                    prompt_text = item['prompt']
                    width = float(item['width'])
                    height = float(item['height'])
                    text = (
                        f"Prompt: {prompt_text}.\n"
                        f"Width: {width}px,\n Height: {height}px,\n"
                        f"ID: {name}"
                    )
                    text_paragraph = Paragraph(text, prompt_style)
                    story.append(img)
                    story.append(Spacer(3, 15))
                    story.append(text_paragraph)
                    story.append(PageBreak())

    except requests.exceptions.RequestException as request_err:
        print("Ошибка запроса: ", request_err)

doc.build(story)

