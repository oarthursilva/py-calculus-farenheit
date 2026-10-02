# py-calculus-farenheit

API HTTP em **Python (Flask)** para cálculos de correção volumétrica / termodinâmica associados a fluidos de petróleo (temperatura ITS-90, grau API, pressão, fatores CTL/CPL/CTPL, entre outros). A aplicação está preparada para **SAP BTP / Cloud Foundry** com autenticação **XSUAA** (OAuth2).

## Índice

- [Visão geral](#visão-geral)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Pré-requisitos](#pré-requisitos)
- [Executar localmente](#executar-localmente)
- [API](#api)
- [Deploy local no Cloud Foundry](#deploy-local-no-cloud-foundry)
- [Pipeline CI/CD](#pipeline-cicd)
- [Resolução de problemas](#resolução-de-problemas)

---

## Visão geral

| Componente | Descrição |
|------------|-----------|
| **Runtime** | Python 3.12 (ver `cf/cap/api/runtime.txt`) |
| **Framework** | Flask 2.x |
| **Segurança** | Sempre cabeçalho `Authorization`. Com `py-uaa`: JWT via `sap-xssec` e scope `uaa.resource`. Sem `py-uaa`: ver `isAuthorized` em `app.py` (local: `True` comentado) |
| **MTA** | Descritor em `cf/standalone/mta.yaml`; módulo Python aponta para `cf/cap/api/` |
| **UAA** | Binding a um serviço **já existente** chamado `py-uaa` (instância XSUAA no mesmo space) |

---

## Estrutura do repositório

```
py-calculus-farenheit/
├── .sap_cid/
│   └── config.yaml           # Configuração SAP CI/CD (Source Repository / Steward — obrigatório no Init)
├── .pipeline/                 # Configuração SAP Project Piper (build MTA + deploy CF)
├── autoscaler/               # Configuração de autoscaler (CF)
├── cf/
│   ├── cap/api/              # Código da API Flask (origem da aplicação)
│   │   ├── app.py            # Factory da app, segurança, blueprints
│   │   ├── server.py         # Ponto de entrada WSGI (FLASK_APP)
│   │   ├── controllers.py    # Rotas HTTP
│   │   ├── services.py       # Lógica de cálculo
│   │   ├── models.py         # DTOs / serialização JSON
│   │   ├── requirements.txt
│   │   ├── Procfile          # Comando em CF (flask na porta 8080)
│   │   ├── manifest.yaml     # Alternativa cf push nativo (sem MTA)
│   │   └── .flaskenv         # FLASK_APP=server.py (desenvolvimento)
│   └── standalone/
│       ├── mta.yaml          # Descritor MTA (build / pipeline)
│       └── xs-security.json  # Referência XSUAA (ex.: criação de serviço)
└── README.md
```

---

## Pré-requisitos

### Desenvolvimento local

- **Python 3.12** (recomendado, alinhado a `runtime.txt`)
- **pip**

### Deploy manual no Cloud Foundry

- [Cloud Foundry CLI](https://github.com/cloudfoundry/cli) (`cf`)
- [MultiApps CF CLI Plugin](https://github.com/cloudfoundry/multiapps-cli-plugin) (`cf deploy` para MTA)
- [Cloud MTA Build Tool](https://github.com/SAP/cloud-mta-build-tool) (`mbt`) — para gerar o `.mtar` a partir do `mta.yaml`
- Subaccount e space no CF (ex.: **SAP BTP** região **BR10**: `https://api.cf.br10.hana.ondemand.com`)
- No space de destino, uma instância XSUAA existente com o nome **`py-uaa`**, conforme `mta.yaml` (`existing-service`)

---

## Executar localmente

### Localmente

Para executar a API localmente, deve primeiramente mover para a pasta da API e então iniciar o serviço Flask.

Na primeira vez, a partir da **raiz do repositório**, instala as dependências:

```bash
pip install -r cf/cap/api/requirements.txt
```

Depois:

```bash
cd cf/cap/api
flask run
```

O ficheiro `cf/cap/api/.flaskenv` define `FLASK_APP=server.py` para o comando `flask run` encontrar a aplicação (requer as dependências instaladas, incluindo `python-dotenv`).

- **Host local:** `localhost`
- **Porta local:** `5000`

Exemplo em **local**, depois de descomentares `isAuthorized = True` em `app.py` (ver secção seguinte): basta enviar qualquer cabeçalho `Authorization` (o valor não é validado como JWT enquanto não houver `py-uaa`):

```bash
curl -s -H "Authorization: Bearer local-dev" \
  "http://127.0.0.1:5000/to/fahrenheit?temp_f_its90=60&api60=35&pressure_psig=0"
```

### Autenticação e `app.py`

O `before_request` em `cf/cap/api/app.py` **sempre** exige o cabeçalho `Authorization` (caso contrário resposta `403`).

- **Com** serviço `py-uaa` (Cloud Foundry ou `VCAP_SERVICES` com credenciais reais): o token é validado com **`sap-xssec`** e o scope **`uaa.resource`** tem de existir no JWT.
- **Sem** `py-uaa` (típico no `flask run` na tua máquina): o ramo `else` define se o pedido é aceite **sem** validar JWT. No repositório está **`isAuthorized = False`** ativo e **`isAuthorized = True` comentado**. Para desenvolvimento local, **descomenta** `isAuthorized = True` e **comenta ou remove** a linha `isAuthorized = False` — assim consideras **`True`** em ambiente local, com o token ainda **não** verificado pelo XSUAA (útil para testes rápidos). **Não comites** essa alteração para branches de produção.

Trecho equivalente ao que corre quando existe `py-uaa` (já está no ficheiro dentro do `if service is not None:`):

```python
if 'authorization' not in request.headers:
    abort(403)
uaa_service = service.credentials
access_token = request.headers.get('authorization')[7:]
security_context = xssec.create_security_context(access_token, uaa_service)
isAuthorized = security_context.check_scope('uaa.resource')
```

---

## API

### `GET /to/fahrenheit`

Conversão / correção com base nos parâmetros de entrada.

**Query parameters (todos obrigatórios)**

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `temp_f_its90` | número | Temperatura em °F (ITS-90) |
| `api60` | número | Grau API a 60 °F |
| `pressure_psig` | número | Pressão em psig |

**Cabeçalhos**

| Cabeçalho | Obrigatório | Descrição |
|-----------|-------------|-----------|
| `Authorization` | Sim | Sempre obrigatório. Com `py-uaa`: `Bearer` + JWT válido e scope `uaa.resource`. Sem `py-uaa` e com `isAuthorized = True` em `app.py`: qualquer valor (ex.: `Bearer local-dev`). |

**Resposta de sucesso (200)** — corpo JSON com campos entre outros: `ctpl`, `t_f68`, `dtF`, `p60`, `pA`, `B`, `bB`, `pStar`, `alpha60`, `ctl`, `fs`, `cpl` (ver `cf/cap/api/models.py`).

**Erros**

- `400` — falta algum query parameter obrigatório (mensagem JSON com `error`)
- `403` — sem `Authorization`; ou token inválido / sem scope com **`py-uaa`**; ou, sem `py-uaa`, `isAuthorized = False` no `app.py`

---

## Deploy local no Cloud Foundry

“Deploy local” aqui significa **a partir da tua máquina** (CLI), para uma subaccount/space onde tens permissões — não confundir com “correr Flask em localhost”.

### 1. Autenticação e destino

**Produção (subaccount applications-producao, pipeline e exemplo manual):**

| | |
|--|--|
| **Subaccount** (BTP) | `Atem Distribuidora de Petroleo Ltda_applications-producao` |
| **Space** (Cloud Foundry) | `prod` |

Na CLI, **`cf target -o`** usa o nome da **org** Cloud Foundry da subaccount — neste ambiente corresponde ao nome da subaccount acima.

```bash
cf api https://api.cf.br10.hana.ondemand.com
cf login -u <o teu email SAP ID>
cf target -o "Atem Distribuidora de Petroleo Ltda_applications-producao" -s prod
```

O **deploy MTA** da CI/CD (e este exemplo) assumem essa subaccount e o **space `prod`**.

Confirma que no space **`prod`** existe o serviço **`py-uaa`** (tipo `xsuaa`, mesmo nome que o `mta.yaml` espera em `existing-service`). Sem essa instância, o `cf deploy` falha.

### 2. Gerar o arquivo MTA (`.mtar`)

O `cf deploy` na pasta do projeto **não** usa diretamente o `mta.yaml`; o fluxo suportado a partir do descriptor de desenvolvimento é **compilar com o MBT** e fazer deploy do **arquivo** gerado.

```bash
cd cf/standalone
mbt build -p cf
```

Por omissão o MBT grava o `.mtar` em:

```text
cf/standalone/mta_archives/
```

(o nome inclui ID e versão do MTA, por exemplo `calculus-fahrenheit-api_1.0.0.mtar`).

Para gravar o `.mtar` na pasta atual:

```bash
mbt build -p cf -t .
```

### 3. Deploy do `.mtar`

```bash
cf deploy mta_archives/calculus-fahrenheit-api_*.mtar
```

Substitui pelo nome exato do ficheiro se não usares wildcard. Flags úteis:

```bash
cf deploy mta_archives/calculus-fahrenheit-api_1.0.0.mtar -f
```

`-f` força substituição de recursos já existentes quando aplicável.

### 4. Verificação pós-deploy

- Rota pública (exemplo no space **prod**): `https://calculus-fahrenheit-api-prod.cfapps.br10.hana.ondemand.com` — o host segue o padrão `calculus-fahrenheit-api-${space}` do `mta.yaml`.
- Chama a API com `Authorization: Bearer <token>` válido para o `py-uaa`.

### Deploy nativo (sem MTA)

Opcionalmente existe `cf/cap/api/manifest.yaml` para `cf push` direto do módulo Python; nesse caso tens de configurar manualmente serviços, rotas e variáveis — o fluxo oficial do repositório é **MTA** em `cf/standalone`.

---

## Pipeline CI/CD

**Deploy CF** corre no estágio **Release** (subaccount **applications-producao**, **`cfSpace: prod`**). **Acceptance** fica sem deploy (`cloudFoundryDeploy: false`).

- **`.pipeline/config.yml`** — **Release** com **`cloudFoundryDeploy: true`**, **`cfOrg`** da subaccount de produção e **`cfSpace: prod`**; **Acceptance** com **`cloudFoundryDeploy: false`**.
- **`.sap_cid/config.yaml`** — **build**, **malwareScan** e **`release.cfDeploy`** com o **mesmo** org/space **prod**. O campo **`org`** é a org CF (= nome da subaccount). Garante credencial **`cf-secretkey`** com permissão nesse org/space. **`py-uaa`** tem de existir no space **`prod`**. Mantém **`buildToolVersion`** alinhado com **`.pipeline/config.yml`**. Versões MBTJ antigas podem ser recusadas.

---

## Resolução de problemas

| Problema | O que fazer |
|----------|-------------|
| `No configuration file found ... .sap_cid/config.yaml` | Garante que existe **`.sap_cid/config.yaml`** na raiz do repositório (commit e push). |
| `build tool version ... deprecated` / `no longer usable` | Atualiza **`buildToolVersion`** em `.sap_cid/config.yaml` e em `.pipeline/config.yml` para uma versão suportada (ex.: `MBTJ21N22`); confirma no Job Editor / documentação SAP CI/CD. |
| `No deployment descriptor with name mtad.yaml` | `mbt build` em `cf/standalone` e `cf deploy` do ficheiro **`.mtar`**. |
| `flag needs an argument: 't' in -t` | Usa `mbt build -p cf -t .` ou omite `-t` e usa `mta_archives/`. |
| `403` em CF | `Authorization: Bearer …` válido para `py-uaa`. |
| `403` em local | Descomenta `isAuthorized = True` em `app.py` (ver [Autenticação e `app.py`](#autenticação-e-apppy)). |
| `pip install -r requirements.txt` na raiz falha | Usa `pip install -r cf/cap/api/requirements.txt`. |
| `Service instance py-uaa not found` | Cria ou expõe a instância **`py-uaa`** (XSUAA) no **space `prod`** da subaccount **applications-producao**, ou ajusta o nome no `mta.yaml` se usares outro serviço. Confirma **`cf target`** correcto antes do deploy. |

---

## Licença

Ver ficheiro `LICENSE` na raiz do repositório.
