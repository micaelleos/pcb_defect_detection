import type { User } from "firebase/auth";

const MAX_IMAGE_SIDE = 1600;

export interface Detection {
  class_name: string;
  confidence: number;
  box: { x_min: number; y_min: number; x_max: number; y_max: number };
}

export interface PredictResponse {
  width: number;
  height: number;
  detections: Detection[];
}

/** Reduz a foto antes do envio e aplica a rotação do EXIF. */
export async function resizeImage(file: File): Promise<Blob> {
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  const scale = Math.min(1, MAX_IMAGE_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Não foi possível processar a imagem."))),
      "image/jpeg",
      0.92,
    );
  });
}

export async function predict(image: Blob, user: User): Promise<PredictResponse> {
  const body = new FormData();
  body.append("file", image, "pcb.jpg");

  let response: Response;
  try {
    response = await fetch("/api/predict", {
      method: "POST",
      headers: { Authorization: `Bearer ${await user.getIdToken()}` },
      body,
    });
  } catch {
    throw new Error("Não foi possível conectar ao serviço. Verifique sua internet e tente novamente.");
  }
  if (!response.ok) {
    throw new Error(ERROR_MESSAGES[response.status] ?? "Não foi possível analisar a imagem. Tente novamente.");
  }
  return response.json();
}

const ERROR_MESSAGES: Record<number, string> = {
  400: "Não conseguimos ler este arquivo. Envie uma foto em JPG ou PNG.",
  401: "Sua sessão expirou. Saia e entre novamente.",
  413: "A imagem é grande demais. Tente uma foto menor.",
  503: "O serviço de análise está indisponível no momento. Tente novamente em instantes.",
};
