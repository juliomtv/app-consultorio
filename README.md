# 🏥 Sistema de Consultório Digital

Sistema completo de gestão para consultório/clínica médica. Desenvolvido com **Python Flask**, **SQLite/PostgreSQL**, **PWA** e preparado para deploy em nuvem ou empacotamento como APK Android via Capacitor.

---

## 🚀 Início Rápido

### 1. Pré-requisitos
- Python 3.10+
- pip

### 2. Instalação

```bash
# Clonar / entrar no diretório
cd app-consultorio

# Criar e ativar ambiente virtual
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar com seus dados
notepad .env   # Windows
nano .env      # Linux/Mac
```

### 4. Executar

```bash
python app.py
```

Acesse: **http://localhost:5000**

**Admin padrão:**
- E-mail: `admin@consultorio.com`
- Senha: `Admin@2024!`

---

## 📁 Estrutura do Projeto

```
app-consultorio/
├── app.py                  # Ponto de entrada Flask
├── config.py               # Configurações (Dev/Prod/Test)
├── requirements.txt        # Dependências Python
├── .env.example            # Exemplo de variáveis de ambiente
│
├── database/
│   ├── __init__.py         # Extensões Flask (db, login, mail)
│   └── models.py           # Modelos SQLAlchemy
│
├── routes/
│   ├── auth.py             # Login, registro, recuperação de senha
│   ├── patient.py          # Área do paciente
│   ├── admin.py            # Painel administrativo
│   └── api.py              # API REST v1
│
├── static/
│   ├── css/
│   │   ├── main.css        # Design system global
│   │   ├── admin.css       # Estilos administrativos
│   │   └── patient.css     # Estilos do paciente
│   ├── js/
│   │   ├── app.js          # Utilitários globais
│   │   ├── admin.js        # Lógica do admin
│   │   ├── patient.js      # Lógica do paciente
│   │   └── contractions.js # Contador de contrações
│   ├── icons/              # Ícones PWA
│   ├── manifest.json       # PWA Manifest
│   └── sw.js               # Service Worker
│
├── templates/
│   ├── auth/               # Login, cadastro, senha
│   ├── patient/            # Área do paciente
│   ├── admin/              # Painel administrativo
│   └── errors/             # Páginas de erro
│
└── uploads/
    ├── documents/          # Documentos dos pacientes
    └── library/            # PDFs da biblioteca
```

---

## 🎯 Funcionalidades

### Área do Paciente
| Funcionalidade | Status |
|---|---|
| Cadastro e login | ✅ |
| Recuperação de senha | ✅ |
| Dashboard com próximas consultas | ✅ |
| Agendar consulta | ✅ |
| Reagendar consulta | ✅ |
| Cancelar consulta | ✅ |
| Histórico de consultas | ✅ |
| Upload de documentos | ✅ |
| Visualizador de PDF inline | ✅ |
| Biblioteca de materiais | ✅ |
| Notificações | ✅ |
| Perfil do paciente | ✅ |
| Contador de contrações | ✅ |
| Plano de parto | ✅ |
| Integração WhatsApp | ✅ |

### Área Administrativa
| Funcionalidade | Status |
|---|---|
| Dashboard analytics | ✅ |
| Gestão de pacientes (CRUD) | ✅ |
| Busca inteligente | ✅ |
| Gestão de profissionais | ✅ |
| Controle de consultas | ✅ |
| Alteração de status | ✅ |
| Agenda visual | ✅ |
| Controle financeiro | ✅ |
| Upload de documentos para pacientes | ✅ |
| Biblioteca de materiais (admin) | ✅ |
| Envio de notificações | ✅ |
| Logs do sistema | ✅ |

### Técnicas
| Recurso | Status |
|---|---|
| PWA instalável | ✅ |
| Service Worker (cache offline) | ✅ |
| API REST v1 | ✅ |
| Horários disponíveis em tempo real | ✅ |
| Suporte SQLite (dev) | ✅ |
| Preparado para PostgreSQL (prod) | ✅ |
| Estrutura para Capacitor/Android | ✅ |
| Design mobile-first | ✅ |

---

## 🗄️ Banco de Dados

**Desenvolvimento:** SQLite (automático, sem configuração)

**Produção (PostgreSQL):**
```bash
# No .env:
DATABASE_URL=postgresql://user:password@host:5432/consultorio
pip install psycopg2-binary  # já no requirements.txt
```

**Migração com Flask-Migrate:**
```bash
flask db init       # apenas na primeira vez
flask db migrate -m "descricao"
flask db upgrade
```

---

## 📱 PWA — Instalar como App

O sistema é um **Progressive Web App** completo:

1. Acesse o sistema pelo navegador mobile
2. Aparecerá um banner "Adicionar à tela inicial"
3. O app funciona offline com cache de assets

Para gerar os **ícones PWA**, use ferramentas como [PWA Builder](https://www.pwabuilder.com/) e coloque em `static/icons/`.

---

## 📱 Android (Capacitor)

Para empacotar como APK:

```bash
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap init "Consultório" "com.consultorio.app"
npx cap add android

# Configure capacitor.config.json:
# server.url = "http://SEU_IP:5000"

npx cap open android
# Build no Android Studio
```

---

## 🚀 Deploy em Produção (VPS/Cloud)

### Gunicorn + Nginx

```bash
# Instalar Gunicorn (já no requirements.txt)
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name seudominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /path/to/app-consultorio/static/;
        expires 30d;
    }

    location /uploads/ {
        alias /path/to/app-consultorio/uploads/;
        internal;
    }
}
```

### Variáveis de ambiente para produção:
```env
FLASK_ENV=production
SECRET_KEY=chave-muito-secreta-e-longa
DATABASE_URL=postgresql://user:pass@host/db
```

---

## 🔒 Segurança

- Senhas hasheadas com Werkzeug (bcrypt)
- Proteção CSRF em formulários
- Sessões seguras com cookie HTTPOnly
- Validação de tipos de arquivo no upload
- Rate limiting via decorators
- Sanitização de nomes de arquivo (secure_filename)
- Acesso baseado em papéis (patient/admin/professional)
- Logs de auditoria completos

---

## 📄 API REST

Base: `/api/v1/`

| Endpoint | Método | Descrição |
|---|---|---|
| `/horarios-disponiveis` | GET | Horários disponíveis por profissional/data |
| `/notificacoes` | GET | Listar notificações |
| `/notificacoes/nao-lidas` | GET | Contador de não lidas |
| `/notificacoes/{id}/lida` | POST | Marcar como lida |
| `/contracoes/sessao` | POST | Iniciar sessão |
| `/contracoes/sessao/{id}/registrar` | POST | Registrar contração |
| `/contracoes/sessao/{id}/encerrar` | POST | Encerrar sessão |
| `/profissionais` | GET | Listar profissionais |
| `/consultas/proximas` | GET | Próximas consultas |
| `/admin/buscar-pacientes` | GET | Busca de pacientes (admin) |
| `/whatsapp/{phone}` | GET | URL do WhatsApp |

---

## 🤝 Tecnologias Utilizadas

- **Backend:** Python 3.10+, Flask 3.0, SQLAlchemy, Flask-Login, Flask-Mail
- **Banco:** SQLite (dev), PostgreSQL (prod)
- **Frontend:** HTML5, CSS3 custom, JavaScript vanilla
- **PWA:** Service Worker, Web App Manifest
- **Fonts:** Inter (Google Fonts)
- **Deploy:** Gunicorn, Nginx

---

## 📞 Suporte

Para configurar e-mail de recuperação de senha, Capacitor (Android) ou migração para PostgreSQL, consulte a documentação de cada ferramenta ou entre em contato com o desenvolvedor.
