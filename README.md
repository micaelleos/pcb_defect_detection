# PCB Inspect

Inspeção óptica de placas de circuito impresso (PCB) pelo navegador: o usuário faz login, fotografa a placa e vê os defeitos de fabricação marcados na imagem e classificados em seis categorias. A detecção usa um YOLOv8 Small treinado com KerasCV no dataset PKU-Market-PCB.

**App:** [pcb-inspect.web.app](https://pcb-inspect.web.app/)

> **Nota:** o backend roda no Cloud Run, que desliga a instância quando fica sem uso. A primeira inferência depois de um período ocioso precisa iniciar o contêiner e carregar o modelo (*cold start*) e pode falhar por tempo esgotado. Se isso acontecer, envie a imagem de novo: a segunda tentativa costuma funcionar.

```
Navegador (React) --login--> Firebase Auth
      | POST /api/predict + token de ID
      v
Firebase Hosting --rewrite /api/**--> Cloud Run (FastAPI + TFLite)
```

| Pasta | Conteúdo |
| --- | --- |
| [`notebooks/`](notebooks/) | Treino, avaliação e exportação do modelo (Google Colab) |
| `backend/` | API FastAPI para o Cloud Run |
| `backend/models/` | Modelo (`pcb_yolo.tflite`, fora do git) e `labels.json` |
| `frontend/` | Site em React, Vite e TypeScript |

## Modelo

| | |
| --- | --- |
| Arquitetura | YOLOv8 Small (`yolo_v8_s_backbone_coco`), detector de estágio único e sem âncoras |
| Parâmetros | 13.210.546 |
| Framework de treino | TensorFlow 2.21, Keras 3.13 e KerasCV 0.9 |
| Transfer learning | Backbone pré-treinado no COCO |
| Entrada | 640x640 px, com proporção preservada e preenchimento à direita e embaixo |
| Otimizador | Adam (LR = 0,001), batch size 4, até 50 épocas |
| Perdas | `ciou` (caixas) e `binary_crossentropy` (classes) |
| Callbacks | `EarlyStopping` (patience = 10, restaura os melhores pesos) e `ModelCheckpoint` (`save_best_only=True`) |
| Exportação | TensorFlow Lite com quantização dinâmica (13,54 MB) e Flex ops |

### Dataset e classes

O treino usa a versão aumentada do **PKU-Market-PCB** (Universidade de Pequim), com anotações no formato YOLO e divisão em treino, validação e teste. As imagens são de alta resolução, com iluminação controlada e ângulo reto.

| Classe | Defeito | Descrição |
| --- | --- | --- |
| `missing_hole` | Furo ausente | Furo de fixação ou de passagem que não foi perfurado |
| `mouse_bite` | Mordida de rato | Erosão na borda da trilha, que reduz a largura útil do condutor |
| `open_circuit` | Circuito aberto | Ruptura total ou parcial da continuidade da trilha |
| `short` | Curto-circuito | Ligação de cobre indesejada entre trilhas |
| `spur` | Espora | Pequena saliência projetada a partir da trilha |
| `spurious_copper` | Cobre espúrio | Fragmentos de cobre que permaneceram após a corrosão |

### Resultados

Métricas por classe do modelo Keras no conjunto de teste, com IoU ≥ 0,5 e confiança ≥ 0,25:

| Classe | Precisão | Recall | F1 |
| --- | --- | --- | --- |
| `missing_hole` | 92,37% | 97,76% | 94,99% |
| `short` | 92,00% | 85,19% | 88,46% |
| `open_circuit` | 83,03% | 66,83% | 74,05% |
| `spurious_copper` | 76,10% | 69,33% | 72,56% |
| `mouse_bite` | 87,66% | 61,09% | 72,00% |
| `spur` | 89,36% | 58,06% | 70,39% |

### Limitações

- O recall é menor em defeitos pequenos nas bordas das trilhas (`spur` e `mouse_bite`), que perdem detalhe ao reduzir a imagem para 640x640.
- O modelo foi treinado com imagens de ângulo reto e iluminação controlada. Fotos de celular, variações fortes de luz e oclusões podem reduzir o desempenho.
- O resultado apoia a inspeção e não substitui a verificação de um profissional qualificado.

### Próximos passos

- Dividir imagens em alta resolução em partes (*tiling*) antes da inferência, para melhorar a detecção de defeitos pequenos.
- Reduzir `CONFIDENCE_THRESHOLD` para 0,15–0,20 onde deixar passar um defeito custa mais que um falso alarme.
- Ampliar o aumento de dados (*MixUp*, distorções cromáticas) para simular variações de iluminação.
- Avaliar o YOLOv8 Medium ou Large, comparando ganho de acurácia e custo computacional.

### Inferência em produção

- O `.tflite` contém só a rede; a decodificação das caixas e o NMS estão em `backend/app/detector.py`, equivalentes aos do KerasCV.
- O modelo depende de Flex ops (`FlexConv2D`), por isso o backend fixa `tensorflow-cpu==2.18.1`: das versões testadas, foi a única que executou o arquivo. Python 3.13 ou superior não tem essa versão, e nesse caso `/api/predict` responde 503. Para inferência fora do Docker, use Python 3.12.
- O limiar de confiança é configurado pela variável `CONFIDENCE_THRESHOLD` (padrão: 0,25, o mesmo da avaliação).

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
  --concurrency 4 --timeout 60 --cpu-boost \
  --set-env-vars FIREBASE_PROJECT_ID=SEU-PROJETO

npm --prefix frontend run build
firebase deploy --only hosting
```

O `--allow-unauthenticated` libera o acesso no nível do Cloud Run; quem protege `/api/predict` é a validação do token do Firebase na aplicação.

Observações:

- O `backend/.gcloudignore` existe para que `backend/models/pcb_yolo.tflite` seja enviado no deploy, mesmo estando fora do git.
- O Firebase Hosting encerra requisições após 60 segundos. Se a primeira requisição (cold start com carga do modelo) passar disso, use `--min-instances 1`, que tem custo contínuo.
