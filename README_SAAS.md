# Arquitetura SaaS Multi-Tenant — Consultório Digital

## Visão Geral

O sistema foi refatorado de um sistema single-tenant para uma **plataforma SaaS multi-tenant white-label**, mantendo todo o código existente como base.

---

## Estrutura de Pastas

```
app-consultorio/
├── core/
│   ├── tenant_manager.py     # Resolução de tenant por domínio/subdomínio/header
│   ├── db_manager.py         # Gerenciador de engines por tenant (PostgreSQL/SQLite)
│   └── context_processor.py  # Injeta `branding` em todos os templates Jinja2
│
├── middleware/
│   └── tenant.py             # before_request: seta g.tenant, g.tenant_id, g.tenant_settings
│
├── services/
│   ├── settings_service.py   # CRUD de TenantSettings (white-label)
│   └── tenant_service.py     # Ciclo de vida de tenants (criar, desativar, stats)
│
├── routes/
│   ├── master.py             # Painel master — gestão de tenants (superadmin only)
│   ├── admin.py              # Painel do tenant (admin do cliente)
│   ├── api.py                # REST API v1 + JWT
│   └── auth.py               # Autenticação multi-role
│
├── templates/
│   ├── master/               # Templates do painel master (roxo)
│   │   ├── base_master.html
│   │   ├── dashboard.html
│   │   ├── tenants.html
│   │   ├── tenant_form.html
│   │   ├── tenant_detail.html
│   │   └── tenant_settings_form.html
│   ├── admin/                # Templates do painel do cliente (cor dinâmica)
│   └── auth/                 # Login/senha (cor e logo dinâmicos)
│
├── database/
│   └── models.py             # + Tenant, TenantSettings; User.tenant_id
│
├── config.py                 # Sem valores fixos de cliente; variáveis de ambiente
└── app.py                    # Factory com middleware, context processor, master blueprint
```

---

## Modelos Novos

### `Tenant`
| Campo | Tipo | Descrição |
|---|---|---|
| `slug` | String | Subdomínio único (ex: `clinicaana`) |
| `custom_domain` | String | Domínio próprio (ex: `clinicaana.com.br`) |
| `db_url` | String | URL PostgreSQL do banco próprio (null = banco compartilhado) |
| `plan` | String | `basic` / `pro` / `enterprise` |
| `active_modules` | String | Módulos ativos separados por vírgula (ex: `clinica,caravanas`) |
| `is_active` | Boolean | Ativar/desativar sem deletar dados |
| `trial_ends_at` | DateTime | Data de expiração do trial |

### `TenantSettings` (white-label)
| Campo | Descrição |
|---|---|
| `company_name` | Nome exibido no sistema |
| `tagline` | Subtítulo na tela de login |
| `logo_url` | URL do logo (CDN, S3, etc.) |
| `favicon_url` | URL do favicon |
| `primary_color` | Cor primária (hex) |
| `secondary_color` | Cor secundária (hex) |
| `bg_dark` | Cor de fundo da tela de login |
| `whatsapp` | Número do WhatsApp da clínica |
| `support_email` | E-mail de suporte |
| `footer_text` | Texto do rodapé |
| `custom_css` | CSS extra injetado globalmente |

---

## Resolução de Tenant

O middleware resolve qual tenant atende a requisição nesta ordem:

```
1. Domínio customizado  → clinicaana.com.br  → Tenant(custom_domain=...)
2. Subdomínio           → clinicaana.saas.com → Tenant(slug='clinicaana')
3. Header X-Tenant-Slug → API/Postman         → Tenant(slug=header)
4. Fallback dev         → primeiro tenant ativo (localhost)
```

Acesso ao `/master/*` ou `localhost` → sem tenant (contexto master).

---

## Roles de Usuário

| Role | Acesso | Descrição |
|---|---|---|
| `superadmin` | `/master/*` | Gerencia todos os tenants |
| `admin` | `/admin/*` | Admin de um tenant específico |
| `professional` | `/admin/*` | Profissional de saúde |
| `patient` | Bloqueado | Dados gerenciados pelo admin |

---

## Autenticação

### Session (Flask-Login)
Usado pelo painel web. Login via `/auth/login`.

### JWT (API)
Para integrações e apps mobile:

```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "email": "admin@clinica.com",
  "password": "senha",
  "tenant_slug": "clinicaana"   ← opcional se estiver no subdomínio
}
```

Resposta:
```json
{
  "status": "success",
  "data": {
    "token": "eyJ...",
    "expires_in": 86400
  }
}
```

Usar o token nas chamadas:
```http
Authorization: Bearer eyJ...
X-Tenant-Slug: clinicaana
```

---

## White-label Dinâmico

Cada template recebe automaticamente a variável `branding` via context processor:

```html
<!-- Disponível em qualquer template -->
{{ branding.company_name }}
{{ branding.primary }}
{{ branding.logo_url }}
```

As cores são injetadas como CSS variables no `<head>` de cada página:
```html
<style>
  :root {
    --primary: {{ branding.primary }};
    --secondary: {{ branding.secondary }};
  }
  {{ branding.custom_css }}
</style>
```

---

## Banco de Dados por Tenant

O `DBManager` suporta dois modos:

| Modo | Configuração | Uso |
|---|---|---|
| Compartilhado | `Tenant.db_url = NULL` | Dev / planos básicos |
| Isolado | `Tenant.db_url = "postgresql://..."` | Planos pro/enterprise |

Para ativar banco próprio ao criar tenant:
```python
from services.tenant_service import create_tenant

tenant = create_tenant(
    name="Clínica da Dra. Ana",
    slug="clinicaana",
    plan="pro",
    admin_email="admin@clinicaana.com.br",
    admin_password="Senha@Segura!",
    db_url="postgresql://user:pass@host/clinicaana_db"
)
```

---

## Painel Master

Acesso: `http://localhost:5000/master/dashboard`

Credenciais padrão:
- **E-mail:** `super@saas.com`
- **Senha:** `Super@2024!`

Funcionalidades:
- Visão geral de todos os tenants
- Criar novo tenant (com admin e banco opcionais)
- Editar tenant (plano, domínio, módulos)
- Configurar identidade visual por tenant (preview em tempo real)
- Ativar/desativar tenant

---

## Painel Admin (tenant)

Acesso: `http://localhost:5000/admin/dashboard`

Credenciais padrão do tenant demo:
- **E-mail:** `admin@consultorio.com`
- **Senha:** `Admin@2024!`

---

## Variáveis de Ambiente (`.env`)

```env
# SaaS
SECRET_KEY=sua-chave-secreta-aqui
FLASK_ENV=production

# Master
SUPERADMIN_EMAIL=super@saas.com
SUPERADMIN_PASSWORD=Super@2024!
SAAS_DOMAIN=seudominio.com.br

# Tenant padrão (demo)
DEFAULT_TENANT_NAME=Demo Clínica
DEFAULT_TENANT_SLUG=demo
ADMIN_EMAIL=admin@demo.com
ADMIN_PASSWORD=Admin@2024!

# Banco mestre (PostgreSQL em produção)
DATABASE_URL=postgresql://user:pass@host/saas_master

# E-mail
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=seu@email.com
MAIL_PASSWORD=sua-senha-app
```

---

## Módulos Planejados

```
modules/
├── clinica/      ← sistema atual refatorado
└── caravanas/    ← próximo módulo
```

Para ativar um módulo em um tenant:
```python
tenant.active_modules = "clinica,caravanas"
db.session.commit()
```

Para verificar no código:
```python
if g.tenant.has_module('caravanas'):
    # lógica do módulo
```

---

## Onboarding de Novo Cliente

1. No painel master → **Novo Tenant**
2. Preencher: nome, slug, plano, e-mail/senha do admin, URL do banco (opcional)
3. Em **Identidade Visual**: definir cores, logo, nome, domínio
4. Configurar DNS: `CNAME slug.seudominio.com.br` ou domínio próprio
5. Pronto — o cliente acessa com suas credenciais e identidade visual própria

---

## Segurança Implementada

- ✅ Senhas com bcrypt (Werkzeug)
- ✅ JWT assinado (HS256, 24h)
- ✅ CSRF via Flask-WTF
- ✅ Isolamento de tenant por `tenant_id` nas queries
- ✅ `superadmin_required` e `admin_required` decorators
- ✅ Rate limiting via `login_required` + logs de auditoria
- ✅ Cookies seguros em produção (`SESSION_COOKIE_SECURE`, `HTTPONLY`, `SAMESITE`)
