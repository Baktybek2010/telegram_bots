from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64

# Инициализация клиента с ключом
client = genai.Client(api_key="AIzaSyCuLmQG8qzZc6CfGS21a1n9c-lCwX84p94")

# Генерация изображений
response = client.models.generate_images(
    model='imagen-4.0-generate-001',
    prompt='Robot holding a red skateboard',
    config=types.GenerateImagesConfig(
        number_of_images=4
    )
)

# Конвертация и показ изображений
for idx, generated_image in enumerate(response.generated_images):
    # generated_image.image_base64 содержит base64-код изображения
    image_bytes = base64.b64decode(generated_image.image_base64)
    image = Image.open(BytesIO(image_bytes))

    # Сохраняем локально (опционально)
    image.save(f"robot_{idx + 1}.png")

    # Показываем изображение
    image.show()
