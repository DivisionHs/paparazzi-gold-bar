from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# Importa o router de convidados que você já tinha
from backend.app.routes.convidados import router as convidados_router

# Importa o seu novo router da Kommo (o código que você colou acima)
from backend.app.routes.webhooks import router as kommo_router

# Importa o router de validação do token do aniversariante (handshake do Flutter Web)
from backend.app.routes.aniversariantes import router as aniversariantes_router

app = FastAPI(title="Paparazzi Gold Bar API")


# Endpoint leve para health check do Render e para o ping de keep-alive
# (UptimeRobot/GitHub Actions) que evita a hibernação do plano free.
@app.get("/health")
async def health():
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    erros = exc.errors()
    msg_erro = "Por favor, verifique os campos preenchidos."
    if erros:
        campo = erros[0].get("loc", [-1])[-1]
        if campo == "whatsapp":
            msg_erro = "O número de WhatsApp inserido está inválido ou incompleto."
        elif campo == "cpf":
            msg_erro = "O CPF inserido deve conter exatamente 11 dígitos numéricos."
        elif campo == "nome_completo":
            msg_erro = "O nome completo digitado é curto demais."
        elif campo == "data_nascimento":
            msg_erro = "A data de nascimento informada é inválida."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": msg_erro},
    )

# Ativa a rota de cadastro de convidados do front-end
app.include_router(convidados_router)

# Ativa a rota de recepção do Webhook da Kommo
app.include_router(kommo_router)

# Ativa a rota de validação do token do aniversariante (GET /aniversariantes/validar-token/{token})
app.include_router(aniversariantes_router)