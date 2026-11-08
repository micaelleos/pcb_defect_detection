# Detecção de defeitos em PCBs

Site em que o usuário faz login, fotografa uma PCB e vê os defeitos encontrados por um modelo YOLO implementado em Keras.

```
Navegador (React) --login--> Firebase Auth
      | POST /api/predict + token de ID
      v
Firebase Hosting --rewrite /api/**--> Cloud Run (FastAPI + Keras)
```

| Pasta | Conteúdo |
| --- | --- |
| `notebooks/` | Notebook de criação do modelo |
| `backend/` | API FastAPI para o Cloud Run |
| `backend/models/` | Modelo (`pcb_yolo.tflite`, fora do git) e `labels.json` |
| `frontend/` | Site em React, Vite e TypeScript |

## Modelo

YOLOv8 Small do KerasCV, treinado no PKU-Market-PCB (entrada de 640x640 com proporção preservada) e exportado para TFLite. Detecta `missing_hole`, `mouse_bite`, `open_circuit`, `short`, `spur` e `spurious_copper`.

- O `.tflite` contém só a rede; a decodificação das caixas e o NMS estão em `backend/app/detector.py`.
- O modelo depende de Flex ops (`FlexConv2D`), por isso o backend fixa `tensorflow-cpu==2.18.1`. Python 3.13 ou superior não tem essa versão, e nesse caso `/api/predict` responde 503. Para inferência fora do Docker, use Python 3.12.
- O dataset tem imagens de ângulo reto e iluminação controlada, então fotos de celular podem ter desempenho inferior.

## Execução local

Backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
FIREBASE_PROJECT_ID=SEU-PROJETO .venv/bin/uvicorn app.main:app --port 8080
```

Frontend (o Vite encaminha `/api` para a porta 8080):

```bash
cd frontend
cp .env.example .env.local   # preencha com os dados do app web do Firebase
npm install
npm run dev
```

## Deploy

Pré-requisitos: projeto Firebase no plano Blaze (exigido pelo Cloud Run) e login com Google ativado em Authentication.

```bash
cp .firebaserc.example .firebaserc   # informe o ID do projeto

gcloud run deploy pcb-defect-api \
  --source backend \
  --region us-central1 \
  --allow-unauthenticated \
  --cpu 2 --memory 4Gi \
  --min-instances 0 --max-instances 2 \
  --set-env-vars FIREBASE_PROJECT_ID=SEU-PROJETO

npm --prefix frontend run build
firebase deploy --only hosting
```

O `--allow-unauthenticated` libera o acesso no nível do Cloud Run; quem protege `/api/predict` é a validação do token do Firebase na aplicação.

Observações:

- O `backend/.gcloudignore` existe para que `backend/models/pcb_yolo.tflite` seja enviado no deploy, mesmo estando fora do git.
- O Firebase Hosting encerra requisições após 60 segundos. Se a primeira requisição (cold start com carga do modelo) passar disso, use `--min-instances 1`, que tem custo contínuo.
