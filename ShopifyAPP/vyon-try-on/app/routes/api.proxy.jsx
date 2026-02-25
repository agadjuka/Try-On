import { json } from "@remix-run/node";
import { authenticate } from "../shopify.server";

const EXTERNAL_API_URL =
  "https://vyon-878549529762.asia-southeast1.run.app/api/v1/try-on";
const EXTERNAL_API_KEY =
  "c625f9ac9286cb4a856c439dd4619b5b78a191173d748dbf5f32215228fdaff1";

// POST /apps/vyon-api/api/proxy
export async function action({ request }) {
  try {
    await authenticate.public.appProxy(request);

    const formData = await request.formData();

    const externalFormData = new FormData();
    externalFormData.append("model", formData.get("model"));
    externalFormData.append("garment_url_1", formData.get("garment_url_1"));

    const externalResponse = await fetch(EXTERNAL_API_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${EXTERNAL_API_KEY}`,
      },
      body: externalFormData,
    });

    const text = await externalResponse.text();
    let data;

    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }

    return json(data, { status: externalResponse.status });
  } catch (error) {
    return json(
      {
        error: "Ошибка при создании задачи",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    );
  }
}

// GET /apps/vyon-api/api/proxy?task_id=...
export async function loader({ request }) {
  try {
    await authenticate.public.appProxy(request);

    const url = new URL(request.url);
    const taskId = url.searchParams.get("task_id");

    if (!taskId) {
      return json(
        { error: "Параметр task_id обязателен" },
        { status: 400 },
      );
    }

    const externalResponse = await fetch(
      `${EXTERNAL_API_URL}/${encodeURIComponent(taskId)}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${EXTERNAL_API_KEY}`,
        },
      },
    );

    const text = await externalResponse.text();
    let data;

    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }

    return json(data, { status: externalResponse.status });
  } catch (error) {
    return json(
      {
        error: "Ошибка при получении статуса задачи",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    );
  }
}