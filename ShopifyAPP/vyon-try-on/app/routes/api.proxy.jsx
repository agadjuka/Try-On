import { json } from "@remix-run/node";
import { authenticate } from "../shopify.server";

export async function action({ request }) {
  // 1. Аутентификация запроса от виджета
  let proxy;
  try {
    proxy = await authenticate.public.appProxy(request);
  } catch (error) {
    return json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!proxy) {
    return json({ error: "Unauthorized" }, { status: 401 });
  }

  // 2. Получаем JSON с виджета (вместо файлов)
  const body = await request.json();
  const { model_base64, garment_url_1 } = body;

  if (!model_base64 || !garment_url_1) {
    return json({ error: "Отсутствует фото или ссылка на товар" }, { status: 400 });
  }

  // 3. Превращаем Base64-текст обратно в бинарный файл
  const base64Data = model_base64.split(',')[1];
  const mimeType = model_base64.split(';')[0].split(':')[1];
  const buffer = Buffer.from(base64Data, 'base64');
  const blob = new Blob([buffer], { type: mimeType });

  // 4. Собираем правильный multipart/form-data для твоего ИИ-сервера
  const forwardFormData = new FormData();
  forwardFormData.append("model", blob, "user_photo.jpg");
  forwardFormData.append("garment_url_1", garment_url_1);

  const EXTERNAL_API_URL = "https://vyon-878549529762.asia-southeast1.run.app/api/v1/try-on";
  const EXTERNAL_API_KEY = "c625f9ac9286cb4a856c439dd4619b5b78a191173d748dbf5f32215228fdaff1";

  try {
    // 5. Отправляем на твой Cloud Run
    const response = await fetch(EXTERNAL_API_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${EXTERNAL_API_KEY}`,
      },
      body: forwardFormData,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => null);
      return json({ error: "Ошибка ИИ-сервера", details: text }, { status: 502 });
    }

    const data = await response.json();
    // Возвращаем task_id на фронтенд
    return json(data);
    
  } catch (error) {
    return json({ error: "Не удалось связаться с сервером ИИ" }, { status: 500 });
  }
}